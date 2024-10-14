import uuid

from pydantic import BaseModel
from pydantic import Field
from sqlalchemy.sql import select
from sqlalchemy.sql import update

from jobs.database import database_session
from jobs.pipelines.base import BaseAsyncPipeline
from jobs.pipelines.exceptions import PipelineFetchError
from jobs.pipelines.news_graph.engine import fargs
from jobs.pipelines.news_scraper.models import NewsItem
from jobs.pipelines.news_scraper.models import NewsItemSchema


class LanguageClassifier(BaseModel):
    is_english: bool = Field(title="Is the text in English?")
    confidence: float = Field(title="Confidence of the classification")


class NewsGraphPipeline(BaseAsyncPipeline):
    def __init__(self):
        super().__init__(
            namespace="news_graph",
            request_limit=2,
            request_interval=1,
        )
        self._processed = None

    async def run(self):
        total_articles = 0
        while True:
            try:
                articles = await self.fetch()
            except PipelineFetchError as e:
                self.log.error(f"Error fetching articles from database: {e}")
                return

            if len(articles) == 0:
                break

            total_articles += len(articles)

            await self.process(articles)
            await self.load()

        self.log.info(f"Ingested {total_articles} news items.")

    async def fetch(self):
        async with database_session() as session:
            query = (
                select(NewsItemSchema)
                .where(NewsItemSchema.batch_id.is_(None))
                .order_by(NewsItemSchema.publish_date.asc())
                .limit(100)
            )
            result = await session.execute(query)
            retrieved_articles = result.scalars().all()
        return retrieved_articles

    async def process(self, data: list[NewsItemSchema]):
        self._processed = [
            NewsItem.model_validate(item, from_attributes=True) for item in data
        ]

    async def load(self):
        batch_id = str(uuid.uuid4())

        as_documents = [item.as_document() for item in self._processed]
        await fargs.ingest(as_documents)

        async with database_session() as session:
            ids = [item.item_id for item in self._processed]
            stmt = (
                update(NewsItemSchema)
                .where(NewsItemSchema.item_id.in_(ids))
                .values(batch_id=batch_id)
            )
            await session.execute(stmt)
            await session.commit()

        self.log.info(f"Ingested {len(self._processed)} news items.")
