import asyncio
import json
import os
from datetime import UTC
from datetime import datetime
from datetime import timedelta

from pydantic import BaseModel
from pydantic import Field
from sqlalchemy.dialects.postgresql import insert as pg_insert

from jobs.database import database_session
from jobs.pipelines.base import BaseAsyncPipeline
from jobs.pipelines.exceptions import PipelineFetchError
from jobs.pipelines.news_scraper.config import SOURCES
from jobs.pipelines.news_scraper.config import llm
from jobs.pipelines.news_scraper.models import NewsAPIResponse
from jobs.pipelines.news_scraper.models import NewsItem
from jobs.pipelines.news_scraper.models import NewsItemSchema
from jobs.pipelines.news_scraper.prompts import FILTER_LANGUAGE_PROMPT
from jobs.pipelines.utils import rate_limited_task
from jobs.pipelines.utils import tqdm_iterable


class LanguageClassifier(BaseModel):
    is_english: bool = Field(title="Is the text in English?")
    confidence: float = Field(title="Confidence of the classification")


class NewsScraperPipeline(BaseAsyncPipeline):
    def __init__(self):
        super().__init__(
            namespace="news",
            request_limit=2,
            request_interval=1,
        )
        self.url = "https://api.worldnewsapi.com/search-news"
        self.llm = llm
        self._processed = None

    async def run(self):
        self.log.info("Running news scraper pipeline...")

        run_timestamp = datetime.now(UTC)
        last_fetch = await self.get_state("last_fetch")
        last_fetch = (
            datetime.fromisoformat(last_fetch)
            if last_fetch
            else (datetime.now(UTC) - timedelta(days=1))
        )

        try:
            articles = await self.fetch(from_date=last_fetch, to_date=run_timestamp)
        except PipelineFetchError as e:
            self.log.error(f"Error fetching news articles: {e}")
            return

        await self.save_state("last_fetch", run_timestamp.isoformat())
        articles = list({article["id"]: article for article in articles}.values())

        self.log.info(f"Retrieved {len(articles)} news articles.")
        if len(articles) > 0:
            await self.process(articles)
            await self.load()

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

        resp_data, resp_headers = await self.download(self.url, **args)

        response = NewsAPIResponse.model_validate(json.loads(resp_data))
        retrieved_articles.extend(response.news)

        while response.available > len(retrieved_articles):
            args["params"]["offset"] = len(retrieved_articles)

            if resp_headers.get("X-API-Quota-Left", 0) == 0:
                self.log.error("News API quota exceeded.")
                break

            resp_data, resp_headers = await self.download(self.url, **args)
            response = NewsAPIResponse.model_validate(json.loads(resp_data))
            retrieved_articles.extend(response.news)

        return retrieved_articles

    async def process(self, data: list[dict]):
        prompt = FILTER_LANGUAGE_PROMPT.format(
            schema_text=LanguageClassifier.model_json_schema()
        )

        llm_with_output = self.llm.with_structured_output(
            LanguageClassifier, method="json_mode", include_raw=True
        )

        @rate_limited_task()
        async def process_one(article):
            try:
                article = NewsItem.model_validate(article)
                messages = [
                    {
                        "role": "system",
                        "content": prompt,
                    },
                    {
                        "role": "user",
                        "content": f"Title: {article.title}\nText: {article.content}",
                    },
                ]
                raw_output = await llm_with_output.ainvoke(messages)

                output = raw_output["parsed"]
                if getattr(output, "is_english", True):
                    return article
                return None

            except Exception as e:
                error_data = {
                    "article": article.model_dump_json(),
                    "error": str(e),
                }
                await self.save_state(
                    f"error:{article.item_id}", json.dumps(error_data), ex=604_800
                )
                self.log.error(f"Error processing article {article.item_id}: {e}")

        tasks = [asyncio.create_task(process_one(article)) for article in data]
        output_articles = []

        async for task in tqdm_iterable(tasks, desc="Processing..."):
            processed = await task
            if processed:
                output_articles.append(processed)

        self._processed = output_articles

    async def load(self):
        data = self._processed
        if not data:
            return

        values_list = [{**item.model_dump()} for item in data]
        stmt = pg_insert(NewsItemSchema).values(values_list)
        stmt = stmt.on_conflict_do_nothing(index_elements=["item_id"])

        async with database_session() as session:
            await session.execute(stmt)
            await session.commit()
        self.log.info(f"Loaded {len(data)} articles.")