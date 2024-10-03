from llama_index.core.graph_stores.types import KG_NODES_KEY
from llama_index.core.graph_stores.types import KG_RELATIONS_KEY
from llama_index.core.indices import PropertyGraphIndex
from llama_index.core.ingestion import DocstoreStrategy
from llama_index.core.ingestion import IngestionPipeline

from jobs.pipelines.news_graph.config import embeddings
from jobs.pipelines.news_graph.config import llm
from jobs.pipelines.news_graph.config import splitter
from jobs.pipelines.news_scraper.models import NewsItem

from .extractors import ClaimsExtractor
from .extractors import EntityExtractor
from .extractors import RelationshipExtractor
from .stores import article_store
from .stores import graph_store
from .stores import index_communities_store
from .stores import nodes_store
from .stores import raw_communities_store
from .transformers import CommunityReportGenerator
from .transformers import GraphTransformer

graph_extractor = IngestionPipeline(
    name="news_graph_extraction",
    project_name="news_graph",
    transformations=[
        splitter,
        EntityExtractor(),
        RelationshipExtractor(),
        ClaimsExtractor(),
        GraphTransformer(),
        embeddings,
    ],
    docstore=article_store,
    vector_store=nodes_store,
    docstore_strategy=DocstoreStrategy.UPSERTS,
)

community_transformer = IngestionPipeline(
    name="news_graph_community_extraction",
    project_name="news_graph",
    transformations=[CommunityReportGenerator(), embeddings],
    docstore=raw_communities_store,
    vector_store=index_communities_store,
    docstore_strategy=DocstoreStrategy.UPSERTS_AND_DELETE,
)


async def ingest_to_graph(items: list[NewsItem]):
    if len(items) == 0:
        return

    documents = [item.as_document() for item in items]
    extracted = await graph_extractor.arun(
        documents=documents,
        show_progress=True,
    )
    for node in extracted:
        if node.metadata[KG_NODES_KEY]:
            graph_store.upsert_nodes(node.metadata[KG_NODES_KEY])
        if node.metadata[KG_RELATIONS_KEY]:
            graph_store.upsert_relations(node.metadata[KG_RELATIONS_KEY])


# load from existing graph/vector store
index = PropertyGraphIndex.from_existing(
    llm=llm,
    kg_extractors=[
        EntityExtractor(),
        RelationshipExtractor(),
        ClaimsExtractor(),
        GraphTransformer(),
    ],
    transformations=[splitter],
    property_graph_store=graph_store,
    use_async=True,
    embed_model=embeddings,
    embed_kg_nodes=True,
)
