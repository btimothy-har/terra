import os

from llama_index.graph_stores.neo4j import Neo4jPropertyGraphStore
from llama_index.storage.docstore.postgres import PostgresDocumentStore
from llama_index.vector_stores.postgres import PGVectorStore

from jobs.pipelines.news_graph.config import VECTOR_STORE_PARAMS

article_store = PostgresDocumentStore.from_uri(
    uri=f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@postgres:5432/terra",
    table_name="articles",
    schema_name="news",
    use_jsonb=True,
)

graph_store = Neo4jPropertyGraphStore(
    username="neo4j",
    password=os.getenv("NEO4J_PASSWORD"),
    url="bolt://neo4j:7687",
)

sources_store = PGVectorStore.from_params(
    **VECTOR_STORE_PARAMS,
    table_name="sources",
    schema_name="news",
)
