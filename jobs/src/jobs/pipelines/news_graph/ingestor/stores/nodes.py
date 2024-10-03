from llama_index.vector_stores.postgres import PGVectorStore

from jobs.pipelines.news_graph.config import VECTOR_STORE_PARAMS

nodes_store = PGVectorStore.from_params(
    **VECTOR_STORE_PARAMS,
    table_name="nodes",
    schema_name="news",
)
