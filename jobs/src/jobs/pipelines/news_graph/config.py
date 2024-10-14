import os

from llama_index.core.node_parser import SemanticSplitterNodeParser
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.embeddings.openai import OpenAIEmbeddingMode

PROJECT_NAME = "news_graph"

EMBED_DIM = 1536
EMBED_MODEL = "text-embedding-3-small"


embeddings = OpenAIEmbedding(
    mode=OpenAIEmbeddingMode.TEXT_SEARCH_MODE,
    model="text-embedding-3-small",
    dimensions=EMBED_DIM,
    api_key=os.getenv("OPENAI_API_KEY"),
)

splitter = SemanticSplitterNodeParser(
    buffer_size=2,
    embed_model=embeddings,
    breakpoint_percentile_threshold=95,
)

VECTOR_STORE_PARAMS = {
    "host": "postgres",
    "port": "5432",
    "database": "terra",
    "user": os.getenv("POSTGRES_USER"),
    "password": os.getenv("POSTGRES_PASSWORD"),
    "hybrid_search": True,
    "embed_dim": EMBED_DIM,
    "use_jsonb": True,
    "hnsw_kwargs": {"hnsw_ef_construction": 400, "hnsw_m": 16, "hnsw_ef_search": 100},
}
