import os
from datetime import UTC
from datetime import datetime

from haystack import Document
from haystack import Pipeline
from haystack.components.embedders import OpenAIDocumentEmbedder
from haystack.components.embedders import OpenAITextEmbedder
from haystack.components.preprocessors import DocumentSplitter
from haystack.document_stores.types import DuplicatePolicy
from haystack.utils import Secret
from haystack_integrations.components.retrievers.pgvector import (
    PgvectorEmbeddingRetriever,
)
from haystack_integrations.components.retrievers.pgvector import (
    PgvectorKeywordRetriever,
)
from haystack_integrations.document_stores.pgvector import PgvectorDocumentStore

from api.config import EMBED_DIM
from api.config import EMBED_MODEL
from api.config import POSTGRES_URL
from api.models import ContextMessage

__all__ = ["ingest_context", "search_context"]

os.environ["PG_CONN_STR"] = f"postgresql://{POSTGRES_URL}"

document_embedder = OpenAIDocumentEmbedder(
    api_key=Secret.from_env_var("OPENAI_API_KEY"),
    model=EMBED_MODEL,
    dimensions=EMBED_DIM,
)

splitter = DocumentSplitter(split_by="sentence", split_length=10, split_overlap=2)

document_store = PgvectorDocumentStore(
    connection_string=Secret.from_env_var("PG_CONN_STR"),
    table_name="agent_context",
    language="english",
    embedding_dimension=EMBED_DIM,
    vector_function="cosine_similarity",
    recreate_table=False,
    search_strategy="hnsw",
    hnsw_index_name="hnsw_index_agentcontext",
    keyword_index_name="keyword_index_agentcontext",
    hnsw_recreate_index_if_exists=True,
)

query_pipeline = Pipeline()

query_pipeline.add_component(
    "embedder",
    OpenAITextEmbedder(
        api_key=Secret.from_env_var("OPENAI_API_KEY"),
        model=EMBED_MODEL,
        dimensions=EMBED_DIM,
    ),
)
query_pipeline.add_component(
    "retriever", PgvectorEmbeddingRetriever(document_store=document_store)
)
query_pipeline.connect("embedder.embedding", "retriever.query_embedding")

pg_keyword_search = PgvectorKeywordRetriever(document_store=document_store)


def ingest_context(message: ContextMessage):
    document = Document(
        content=message.content,
        meta={"agent": message.agent, "timestamp": datetime.now(UTC).isoformat()},
    )
    split_documents = splitter.run([document])
    embed_chunks = document_embedder.run(split_documents["documents"])
    document_store.write_documents(
        embed_chunks.get("documents"), policy=DuplicatePolicy.OVERWRITE
    )


def search_context(query: str, top_k: int = 10) -> list[Document]:
    embd_results = query_pipeline.run(
        {"embedder": {"text": query}, "retriever": {"top_k": top_k}}
    )
    key_results = pg_keyword_search.run(query=query)

    print("RESULTS")
    print(key_results)

    return embd_results["retriever"]["documents"]
