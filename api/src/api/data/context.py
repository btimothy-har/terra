import os
from datetime import UTC
from datetime import datetime

from llama_index.core import Document
from llama_index.core import VectorStoreIndex
from llama_index.core.ingestion import IngestionPipeline
from llama_index.core.node_parser import SemanticSplitterNodeParser
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.storage.docstore.postgres import PostgresDocumentStore
from llama_index.vector_stores.postgres import PGVectorStore

from api.config import EMBED_DIM
from api.config import EMBED_MODEL
from api.config import POSTGRES_URL
from api.models import ContextMessage

__all__ = ["ingest_context", "search_context"]

os.environ["PG_CONN_STR"] = f"postgresql://{POSTGRES_URL}"

text_embedder = OpenAIEmbedding(
    model=EMBED_MODEL,
    dimensions=EMBED_DIM,
    api_key=os.getenv("OPENAI_API_KEY"),
)

splitter = SemanticSplitterNodeParser(
    buffer_size=2,
    embed_model=text_embedder,
    breakpoint_percentile_threshold=90,
)

document_store = PostgresDocumentStore.from_uri(
    uri=f"postgresql://{POSTGRES_URL}",
    table_name="documents",
    schema_name="context",
    use_jsonb=True,
)

vector_store = PGVectorStore.from_params(
    host="postgres",
    port="5432",
    database="terra",
    user=os.getenv("POSTGRES_USER"),
    password=os.getenv("POSTGRES_PASSWORD"),
    table_name="vectors",
    schema_name="context",
    hybrid_search=True,
    embed_dim=EMBED_DIM,
    use_jsonb=True,
    hnsw_kwargs={"hnsw_ef_construction": 400, "hnsw_m": 16, "hnsw_ef_search": 100},
)

vector_index = VectorStoreIndex.from_vector_store(vector_store=vector_store)

ingestion_pipeline = IngestionPipeline(
    transformations=[
        splitter,
        text_embedder,
    ],
    vector_store=vector_store,
)


def ingest_context(messages: list[ContextMessage]):
    documents = [
        Document(
            text=message.content,
            metadata={
                "agent": message.agent,
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )
        for message in messages
    ]
    ingestion_pipeline.run(documents)
    vector_index.refresh_ref_docs(documents)


def search_context(query: str, top_k: int = 10) -> list[Document]:
    retriever = vector_index.as_retriever(
        vector_store_query_mode="hybrid",
        similarity_top_k=top_k,
        sparse_top_k=top_k,
        embed_model=text_embedder,
    )
    response = retriever.retrieve(query)
    return response
