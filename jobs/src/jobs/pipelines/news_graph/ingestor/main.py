import asyncio

from llama_index.core.graph_stores.types import KG_NODES_KEY
from llama_index.core.graph_stores.types import KG_RELATIONS_KEY
from llama_index.core.indices import PropertyGraphIndex
from llama_index.core.ingestion import DocstoreStrategy
from llama_index.core.ingestion import IngestionPipeline

from jobs.pipelines.news_graph.config import embeddings
from jobs.pipelines.news_graph.config import llm
from jobs.pipelines.news_graph.config import splitter
from jobs.pipelines.news_graph.models import NewsItem

from .extractors import ClaimsExtractor
from .extractors import EntityExtractor
from .extractors import RelationshipExtractor
from .stores import article_store
from .stores import claims_store
from .stores import graph_store
from .stores import sources_store
from .transformers import ClaimsTransformer
from .transformers import GraphTransformer
from .transformers import SourcesTransformer

graph_extractor = IngestionPipeline(
    name="news_graph_extraction",
    project_name="news_graph",
    transformations=[
        EntityExtractor(),
        RelationshipExtractor(),
        ClaimsExtractor(),
        GraphTransformer(),
    ],
    docstore=article_store,
    docstore_strategy=DocstoreStrategy.UPSERTS,
)


sources_extractor = IngestionPipeline(
    name="claims_extraction",
    project_name="news_graph",
    transformations=[SourcesTransformer(), splitter, embeddings],
    vector_store=sources_store,
)

claims_extractor = IngestionPipeline(
    name="claims_extraction",
    project_name="news_graph",
    transformations=[ClaimsTransformer(), splitter, embeddings],
    vector_store=claims_store,
)


async def ingest_to_graph(items: list[NewsItem]):
    async def insert_node(node):
        await asyncio.to_thread(graph_store.upsert_nodes, node.metadata[KG_NODES_KEY])
        await asyncio.to_thread(
            graph_store.upsert_relations, node.metadata[KG_RELATIONS_KEY]
        )

    documents = [item.as_document() for item in items]
    extracted = await graph_extractor.arun(documents)
    for node in extracted:
        await insert_node(node)

    await sources_extractor.arun(extracted)
    await claims_extractor.arun(extracted)


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
