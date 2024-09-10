import asyncio
import json
import os
from datetime import UTC
from datetime import datetime
from datetime import timedelta

from pydantic import BaseModel
from pydantic import Field
from sqlalchemy.dialects.postgresql import insert as pg_insert

from .base import AsyncScraper
from .models import NewsItem
from .models.schema import NewsItemSchema
from .utils.ai import LLM
from .utils.news_sources import SOURCES
from .utils.prompts import NEWS_LANGUAGE_PROMPT


class LanguageClassifier(BaseModel):
    is_english: bool = Field(title="Is the text in English?")
    confidence: float = Field(title="Confidence of the classification")


class NewsScraper(AsyncScraper):
    def __init__(self):
        super().__init__(namespace="news", request_limit=2, request_interval=1)
        self.url = "https://api.worldnewsapi.com/search-news"

    @property
    def last_fetched(self) -> datetime:
        if self._last_fetched:
            return self._last_fetched
        else:
            return datetime.now(UTC) - timedelta(days=1)

    def compute_new_sleep_time(self, quota_remaining: int):
        now = datetime.now(UTC)
        midnight = datetime.combine(
            now.date() + timedelta(days=1), datetime.min.time(), tzinfo=UTC
        )
        seconds_left = (midnight - now).total_seconds()

        if int(quota_remaining) > 1:
            time_between_requests = seconds_left / int(quota_remaining)
        else:
            time_between_requests = seconds_left
        return time_between_requests

    async def run(self):
        args = {}
        args["params"] = {
            "api-key": os.getenv("NEWS_API_KEY"),
            "language": "en",
            "earliest-publish-date": self.last_fetched.strftime("%Y-%m-%d %H:%M:%S"),
            "sort": "publish-time",
            "sort-direction": "ASC",
            "news-sources": ",".join(SOURCES),
            "number-of-articles": 10,
        }
        get_latest_news, req_headers = await self.fetch(
            url=self.url,
            **args,
        )

        get_latest_news = json.loads(get_latest_news)
        data = get_latest_news["news"]

        self.logger.info(
            f"Found {len(data)} articles. Available: {get_latest_news['available']}."
        )
        if len(data) == 0:
            return

        transformed = await self.transform(data)
        await self.load(transformed)

        quota_remaining = req_headers["X-API-Quota-Left"]

        self._next_run = datetime.now(UTC) + timedelta(
            seconds=max(self.compute_new_sleep_time(float(quota_remaining)), 180)
        )
        self.logger.info(
            f"Quota remaining: {quota_remaining}. Next run at: {self._next_run}"
        )

    async def transform(self, data: list[dict]):
        async def transform_article(article: dict):
            llm_with_output = LLM.with_structured_output(
                LanguageClassifier, method="json_mode"
            )

            messages = [
                {
                    "role": "system",
                    "content": NEWS_LANGUAGE_PROMPT.format(
                        schema_text=LanguageClassifier.model_json_schema()
                    ),
                },
                {
                    "role": "user",
                    "content": f"Title: {article['title']}\nText: {article['text']}",
                },
            ]
            output = await llm_with_output.ainvoke(messages)

            if output.is_english:
                return NewsItem(
                    item_id=str(article["id"]),
                    title=article["title"],
                    content=article["text"],
                    summary=article.get("summary"),
                    url=article["url"],
                    image=article.get("image"),
                    video=article.get("video"),
                    publish_date=article["publish_date"],
                    author=article.get("author"),
                    authors=article.get("authors"),
                    language=article.get("language"),
                    category=article.get("catgory", article.get("category")),
                    source_country=article.get("source_country"),
                    sentiment=article.get("sentiment"),
                )
            else:
                return None

        tasks = [transform_article(article) for article in data]
        return [item for item in await asyncio.gather(*tasks) if item is not None]

    async def load(self, data: list[NewsItem]):
        async def load_one(item: NewsItem):
            async with self.get_session() as session:
                stmt = pg_insert(NewsItemSchema).values(**item.model_dump())
                stmt = stmt.on_conflict_do_nothing()
                await session.execute(stmt)
                await session.commit()

        await asyncio.gather(*[load_one(item) for item in data])
        self.logger.info(f"Loaded {len(data)} articles")
