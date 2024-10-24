import uuid

from sqlalchemy.sql import select
from sqlalchemy.sql import update

from jobs.config import ENV
from jobs.database import database_session
from jobs.tasks.base import BaseAsyncPipeline
from jobs.tasks.exceptions import PipelineFetchError

from ..models import NewsItem
from ..models import NewsItemSchema
from .config import PROJECT_NAME
from .graph import graph_engine


class NewsPodcastPipeline(BaseAsyncPipeline):
    def __init__(self):
        super().__init__(
            namespace=PROJECT_NAME,
            request_limit=2,
            request_interval=1,
        )
        self._processed = None
        self._fetch_count = 1 if ENV == "dev" else 100

    async def run(self):
        try:
            articles = await self.fetch()
        except PipelineFetchError as e:
            self.log.error(f"Error fetching articles from database: {e}")
            return

        if len(articles) == 0:
            self.log.info("No articles found.")
            return

        await self.process(articles)
        await self.load()

    async def fetch(self):
        async with database_session() as session:
            query = (
                select(NewsItemSchema)
                .where(NewsItemSchema.batch_id.is_(None))
                .order_by(NewsItemSchema.publish_date.asc())
                .limit(self._fetch_count)
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
        await graph_engine.ingest(documents=as_documents)

        async with database_session() as session:
            ids = [item.item_id for item in self._processed]
            stmt = (
                update(NewsItemSchema)
                .where(NewsItemSchema.item_id.in_(ids))
                .values(batch_id=batch_id)
            )
            await session.execute(stmt)
            await session.commit()

        self.log.info(
            f"Ingested {len(self._processed)} news items with batch ID {batch_id}."
        )
