from datetime import UTC
from datetime import datetime
from datetime import timedelta

import aiohttp
from fargs.utils import tqdm_iterable
from llama_index.core.vector_stores import FilterOperator
from llama_index.core.vector_stores import MetadataFilter
from llama_index.core.vector_stores import MetadataFilters
from sqlalchemy.sql import select

from jobs.config import API_ENDPOINT
from jobs.config import ENV
from jobs.database import database_session
from jobs.tasks.base import BaseAsyncPipeline
from jobs.tasks.exceptions import PipelineError
from jobs.tasks.exceptions import PipelineFetchError

from ..models import NewsItem
from ..models import NewsItemSchema
from .graph import graph_engine
from .graph import graph_stores
from .studio.main import PodcastStudioFlow

podcast_flow = PodcastStudioFlow(timeout=None, verbose=True if ENV == "dev" else False)


class PodcastCreateError(PipelineError):
    pass


class NewsPodcastPipeline(BaseAsyncPipeline):
    def __init__(self):
        super().__init__(
            namespace="news.podcast",
            request_limit=2,
            request_interval=1,
        )
        self._processed = None
        self.graph_engine = graph_engine

    async def run(self):
        self.log.info("Running news podcast pipeline...")

        run_timestamp = datetime.now(UTC)
        last_fetch = await self.get_state("last_fetch")
        last_fetch = (
            datetime.fromisoformat(last_fetch)
            if last_fetch
            else (datetime.now(UTC) - timedelta(hours=12))
        )

        try:
            articles = await self.fetch(last_fetch)
        except PipelineFetchError as e:
            self.log.error(f"Error fetching articles from database: {e}")
            return

        if len(articles) > 0:
            await self.process(articles)
            await self.load()
        else:
            self.log.info("No articles found.")

        await self.save_state("last_fetch", run_timestamp.isoformat())

    async def fetch(self, last_fetch: datetime):
        async with database_session() as session:
            if ENV == "dev":
                query = (
                    select(NewsItemSchema)
                    .where(NewsItemSchema.batch_id.is_(None))
                    .order_by(NewsItemSchema.publish_date.asc())
                    .limit(300)
                )
            else:
                query = (
                    select(NewsItemSchema)
                    .where(NewsItemSchema.batch_id.is_(None))
                    .where(NewsItemSchema.publish_date > last_fetch)
                    .order_by(NewsItemSchema.publish_date.asc())
                )
            result = await session.execute(query)
            retrieved_articles = result.scalars().all()
        return retrieved_articles

    async def process(self, data: list[NewsItemSchema]):
        if False:
            news_items = [
                NewsItem.model_validate(item, from_attributes=True).as_document()
                for item in data
            ]

            await graph_engine.ingest(
                documents=news_items,
                show_progress=True if ENV == "dev" else False,
            )

        self._processed = await graph_engine.summarize(max_cluster_size=100)

    async def load(self):
        async for community in tqdm_iterable(
            self._processed, desc="Preparing podcasts"
        ):
            source_nodes = graph_stores.nodes_store.get_nodes(
                filters=MetadataFilters(
                    filters=[
                        MetadataFilter(
                            key="chunk_id",
                            operator=FilterOperator.IN,
                            value=community.metadata["sources"],
                        ),
                    ]
                )
            )

            node_ids = [n.node_id for n in source_nodes]
            article_ids = list(set([n.metadata["doc_id"] for n in source_nodes]))
            source_countries = list(
                set([n.metadata["source_country"].upper() for n in source_nodes])
            )

            if len(article_ids) > 1 or len(source_countries) > 1:
                podcast = await podcast_flow.run(
                    community=community,
                    node_ids=node_ids,
                    article_ids=article_ids,
                    source_countries=source_countries,
                )

                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.request(
                            "PUT", f"{API_ENDPOINT}/podcasts/new", json=podcast
                        ) as response:
                            response.raise_for_status()

                except Exception as e:
                    raise PodcastCreateError(f"Failed to create podcast: {e}") from e
                return
