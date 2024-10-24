import asyncio
import json
import os
from datetime import UTC
from datetime import datetime
from datetime import timedelta

import ell
from fargs.utils import rate_limited_task
from fargs.utils import tqdm_iterable
from pydantic import BaseModel
from pydantic import Field
from sqlalchemy.dialects.postgresql import insert as pg_insert

from jobs.database import database_session
from jobs.tasks.base import BaseAsyncPipeline
from jobs.tasks.exceptions import PipelineFetchError

from ..models import NewsAPIResponse
from ..models import NewsItem
from ..models import NewsItemSchema
from .config import SOURCES
from .prompts import FILTER_LANGUAGE_PROMPT


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
        self._processed = None

    @ell.complex(
        model="gpt-4o-mini",
        response_format=LanguageClassifier,
    )
    def language_classifier(self, title: str, text: str):
        return [
            ell.system(
                FILTER_LANGUAGE_PROMPT.format(
                    schema_text=LanguageClassifier.model_json_schema()
                )
            ),
            ell.user(f"Title: {title}\nText: {text}"),
        ]

    async def run(self, extract_id: str = None):
        self.log.info("Running news scraper pipeline...")

        run_timestamp = datetime.now(UTC)
        last_fetch = await self.get_state("last_fetch")
        last_fetch = (
            datetime.fromisoformat(last_fetch)
            if last_fetch
            else (datetime.now(UTC) - timedelta(days=1))
        )

        total_articles = 0
        has_articles = True

        while has_articles:
            if extract_id:
                fetched_articles = await self.get_state(extract_id)
                available_articles = len(fetched_articles)
                if available_articles == 0:
                    self.log.warning(f"No articles found for extract ID: {extract_id}")
                    return
            else:
                try:
                    fetched_articles, available_articles = await self.fetch(
                        from_date=last_fetch,
                        to_date=run_timestamp,
                        offset=total_articles,
                    )
                except PipelineFetchError as e:
                    self.log.error(f"Error fetching news articles: {e}")
                    return

            articles = list(
                {article["id"]: article for article in fetched_articles}.values()
            )
            total_articles += len(articles)

            if len(articles) == 0:
                self.log.info("No articles found.")
                continue

            try:
                await self.process(articles)
                await self.load()
            except Exception as e:
                self.log.error(f"Error processing news articles: {e}")

            has_articles = available_articles > total_articles

        if not extract_id:
            await self.save_state("last_fetch", run_timestamp.isoformat())

        self.log.info(
            f"Completed news scraper pipeline. Total: {total_articles} articles."
        )

    async def fetch(self, from_date: datetime, to_date: datetime, offset: int = 0):
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
                "offset": offset,
            }
        }

        try:
            resp_data, resp_headers = await self.download(self.url, **args)
        except Exception as e:
            raise PipelineFetchError(f"Error fetching news articles: {e}") from e

        if float(resp_headers.get("X-API-Quota-Left", 0)) <= 10:
            self.log.warning(
                f"News API quota is low: {resp_headers.get('X-API-Quota-Left', 0)}"
            )
        else:
            self.log.info(
                f"News API quota remaining: "
                f"{resp_headers.get('X-API-Quota-Left', 0)}"
            )

        response = NewsAPIResponse.model_validate(json.loads(resp_data))

        return response.news, response.available

    async def process(self, data: list[dict]):
        @rate_limited_task(max_rate=30)
        async def process_one(article):
            try:
                article = NewsItem.model_validate(article)

                try:
                    raw_output = await asyncio.to_thread(
                        self.language_classifier, article.title, article.content
                    )
                except Exception as e:
                    self.log.error(f"Error classifying language: {e}")
                    return article

                parsed_output = raw_output.parsed

                if getattr(parsed_output, "is_english", True):
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
