import asyncio
import json
import os
from datetime import UTC
from datetime import datetime
from datetime import timedelta

from pydantic import BaseModel
from pydantic import Field
from pydantic import model_validator
from sqlalchemy.dialects.postgresql import insert as pg_insert

from scrapers.base import BaseAsyncScraper
from scrapers.base import ScraperFetchError
from scrapers.models import NewsItemSchema
from scrapers.utils.ai import llm
from scrapers.utils.funcs import check_and_set_next_run
from scrapers.utils.funcs import database_session
from scrapers.utils.prompts import NEWS_LANGUAGE_PROMPT

SOURCES = [
    "cnn.com",
    "bbc.co.uk",
    "vox.com",
    "globalissues.org",
    "egyptian-gazette.com",
    "cbslocal.com",
    "euronews.com",
    "financialpost.com",
    "time.com",
    "sky.com",
    "washingtonpost.com",
    "cbc.ca",
    "aljazeera.com",
    "channelnewsasia.com",
    "dailymail.co.uk",
    "huffingtonpost.co.uk",
    "independent.co.uk",
    "politico.com",
    "washingtontimes.com",
    "nikkei.com",
    "economist.com.na",
    "hrmasia.com",
    "nationalpost.com",
    "google.com",
    "technode.com",
    "thediplomat.com",
    "asiasentinel.com",
    "bostonherald.com",
    "campaignasia.com",
    "cbsnews.com",
    "cnbc.com",
    "computerworld.com",
    "dailyherald.com",
    "eastasiaforum.org",
    "financeasia.com",
    "huffpost.com",
    "japantimes.co.jp",
    "nytimes.com",
    "politico.eu",
    "theworld.org",
    "rand.org",
    "scmp.com",
    "euronews247.com",
    "theguardian.com",
    "yahoo.com",
    "dailywire.com",
    "reuters.com",
]


class LanguageClassifier(BaseModel):
    is_english: bool = Field(title="Is the text in English?")
    confidence: float = Field(title="Confidence of the classification")


class NewsItem(BaseModel):
    item_id: str
    title: str
    content: str
    summary: str | None = None
    url: str
    image: str | None = None
    video: str | None = None
    publish_date: datetime
    author: str | None = None
    authors: list[str] | None = None
    category: str | None = None
    language: str | None = None
    source_country: str | None = None
    sentiment: float = None

    @model_validator(mode="before")
    @classmethod
    def convert_keys(cls, data: dict):
        data["item_id"] = str(data.pop("id"))
        data["content"] = data.pop("text")

        if "catgory" in data:
            data["category"] = data.pop("catgory")
        return data


class NewsAPIResponse(BaseModel):
    offset: int
    number: int
    available: int
    news: list[dict]


class NewsScraper(BaseAsyncScraper):
    def __init__(self):
        super().__init__(
            namespace="news",
            task_concurrency=100,
            request_limit=2,
            request_interval=1,
        )
        self.url = "https://api.worldnewsapi.com/search-news"

    async def fetch(self, from_date: datetime, to_date: datetime):
        retrieved_articles = []
        args = {
            "params": {
                "api-key": os.getenv("NEWS_API_KEY"),
                "language": "en",
                "earliest-publish-date": from_date.strftime("%Y-%m-%d %H:%M:%S"),
                "latest-publish-date": to_date.strftime("%Y-%m-%d %H:%M:%S"),
                "sort": "publish-time",
                "sort-direction": "DESC",
                "news-sources": ",".join(SOURCES),
                "number": 100,
            }
        }

        resp_data, resp_headers = await super().fetch(self.url, **args)

        response = NewsAPIResponse.model_validate(json.loads(resp_data))
        retrieved_articles.extend(response.news)

        while response.available > len(retrieved_articles):
            args["params"]["offset"] = len(retrieved_articles)

            if resp_headers.get("X-API-Quota-Left", 0) == 0:
                self.log.error("News API quota exceeded.")
                break

            resp_data, resp_headers = await super().fetch(self.url, **args)
            response = NewsAPIResponse.model_validate(json.loads(resp_data))
            retrieved_articles.extend(response.news)

            await asyncio.sleep(0)

        return retrieved_articles

    @check_and_set_next_run()
    async def run(self):
        self.log.info("Running news scraper...")

        run_timestamp = datetime.now(UTC)

        if self._iter_count == 0:
            last_fetch = datetime.now(UTC) - timedelta(days=1)
        else:
            last_fetch = await self.get_state("last_fetch")
            last_fetch = (
                datetime.fromisoformat(last_fetch)
                if last_fetch
                else (datetime.now(UTC) - timedelta(days=1))
            )

        try:
            articles = await self.fetch(from_date=last_fetch, to_date=run_timestamp)
        except ScraperFetchError as e:
            self.log.error(f"Error fetching News: {e}")
            return run_timestamp + timedelta(seconds=60)

        articles = list({article["id"]: article for article in articles}.values())

        self.log.info(f"Retrieved {len(articles)} articles.")
        if len(articles) > 0:
            processed = await self.process(articles)
            await self.load(processed)

        await self.save_state("last_fetch", run_timestamp.isoformat())

        next_run = datetime.now(UTC) + timedelta(hours=24)
        self._iter_count += 1
        return next_run

    async def process(self, data: list[dict]):
        async def process_one(article: dict):
            async with self._concurrency:
                try:
                    article = NewsItem.model_validate(article)
                except Exception as e:
                    error_data = {
                        "article": article,
                        "error": str(e),
                    }
                    await self.save_state(
                        f"error:{article['id']}", json.dumps(error_data)
                    )
                    self.log.error(f"Error processing article {article['id']}: {e}")
                    return None

                llm_with_output = llm.with_structured_output(LanguageClassifier)

                messages = [
                    {
                        "role": "system",
                        "content": NEWS_LANGUAGE_PROMPT.format(
                            schema_text=LanguageClassifier.model_json_schema()
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"Title: {article.title}\nText: {article.content}",
                    },
                ]
                try:
                    output = await llm_with_output.ainvoke(messages)
                except Exception as e:
                    error_data = {
                        "article": article.model_dump_json(),
                        "error": str(e),
                    }
                    await self.save_state(
                        f"error:{article.item_id}", json.dumps(error_data)
                    )
                    self.log.error(f"Error processing article {article.item_id}: {e}")
                    return None

                if output.is_english:
                    return article
                else:
                    return None

        tasks = [process_one(article) for article in data]
        return [item for item in await asyncio.gather(*tasks) if item is not None]

    async def load(self, data: list[NewsItem]):
        async def load_one(item: NewsItem):
            async with self._concurrency:
                async with database_session() as session:
                    stmt = pg_insert(NewsItemSchema).values(**item.model_dump())
                    stmt = stmt.on_conflict_do_nothing()
                    await session.execute(stmt)
                    await session.commit()

        await asyncio.gather(*[load_one(item) for item in data])
        self.log.info(f"Loaded {len(data)} articles.")
