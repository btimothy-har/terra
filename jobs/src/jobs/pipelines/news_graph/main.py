import asyncio
import json
import os
import uuid
from datetime import UTC
from datetime import datetime
from datetime import timedelta

from pydantic import BaseModel
from pydantic import Field
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.sql import select as pg_select

from jobs.database import cache_client
from jobs.database import database_session
from jobs.database.schemas import NewsItemSchema
from jobs.pipelines.base import BaseAsyncScraper
from jobs.pipelines.exceptions import PipelineFetchError
from jobs.pipelines.news_graph.config import SOURCES
from jobs.pipelines.news_graph.config import llm
from jobs.pipelines.news_graph.ingestor import ingest_to_graph
from jobs.pipelines.news_graph.models import NewsAPIResponse
from jobs.pipelines.news_graph.models import NewsItem
from jobs.pipelines.news_graph.prompts import FILTER_LANGUAGE_PROMPT
from jobs.pipelines.utils import check_and_set_next_run


class LanguageClassifier(BaseModel):
    is_english: bool = Field(title="Is the text in English?")
    confidence: float = Field(title="Confidence of the classification")


class NewsGraphPipeline(BaseAsyncScraper):
    def __init__(self):
        super().__init__(
            namespace="news",
            task_concurrency=100,
            request_limit=2,
            request_interval=1,
        )
        self.url = "https://api.worldnewsapi.com/search-news"
        self.llm = llm

    @check_and_set_next_run()
    async def run(self):
        self.log.info("Running news scraper...")

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
            self.log.error(f"Error fetching News: {e}")
            return run_timestamp + timedelta(seconds=60)

        articles = list({article["id"]: article for article in articles}.values())

        self.log.info(f"Retrieved {len(articles)} articles.")
        if len(articles) > 0:
            await self.load(await self.process(articles))

        await self.save_state("last_fetch", run_timestamp.isoformat())

        next_run = datetime.now(UTC) + timedelta(hours=24)
        self._iter_count += 1
        return next_run

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

    async def process(self, data: list[dict]):
        prompt = FILTER_LANGUAGE_PROMPT.format(
            schema_text=LanguageClassifier.model_json_schema()
        )

        llm_with_output = self.llm.with_structured_output(
            LanguageClassifier, method="json_mode", include_raw=True
        )

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
                try:
                    raw_output = await llm_with_output.ainvoke(messages)
                    output = raw_output["parsed"]
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

                if getattr(output, "is_english", True):
                    return article
                else:
                    return None

        tasks = [process_one(article) for article in data]
        return [item for item in await asyncio.gather(*tasks) if item is not None]

    async def load(self, data: list[NewsItem]):
        batch_id = str(uuid.uuid4())

        async with database_session() as session:
            values_list = [{**item.model_dump(), "batch_id": batch_id} for item in data]
            stmt = pg_insert(NewsItemSchema).values(values_list)
            stmt = stmt.on_conflict_do_nothing()
            await session.execute(stmt)
            await session.commit()

        async with cache_client() as cache:
            current_loaded = await cache.get(f"jobs:loaded:{self.namespace}")
            if not current_loaded:
                current_loaded = {batch_id}
            else:
                current_loaded = set(json.loads(current_loaded))
                current_loaded.add(batch_id)

            await cache.set(
                f"jobs:loaded:{self.namespace}", json.dumps(list(current_loaded))
            )

        self.log.info(f"Loaded {len(data)} articles.")

    async def ingest(self):
        ingest_lock = asyncio.Lock()

        async with cache_client() as cache:
            batch_ids = await cache.get(f"jobs:loaded:{self.namespace}")
            batch_ids = json.loads(batch_ids)

        if not batch_ids:
            return

        async def ingest_one(batch_id: str):
            async with ingest_lock:
                async with database_session() as session:
                    stmt = pg_select(NewsItemSchema).where(
                        NewsItemSchema.batch_id == batch_id
                    )
                    result = await session.execute(stmt)
                    items = result.scalars().all()

                news_items = [
                    NewsItem.model_validate(item, from_attributes=True)
                    for item in items
                ]

                try:
                    await ingest_to_graph(news_items)
                except Exception as e:
                    self.log.error(f"Error ingesting batch {batch_id}: {e}")
                    return

                async with cache_client() as cache:
                    current_loaded = await cache.get(f"jobs:loaded:{self.namespace}")
                    if not current_loaded:
                        current_loaded = set()
                    else:
                        current_loaded = set(json.loads(current_loaded))

                    current_loaded.discard(batch_id)
                    await cache.set(
                        f"jobs:loaded:{self.namespace}",
                        json.dumps(list(current_loaded)),
                    )

                self.log.info(
                    f"Ingested batch {batch_id} with {len(news_items)} items."
                )

        tasks = [ingest_one(batch_id) for batch_id in batch_ids]
        await asyncio.gather(*tasks)
