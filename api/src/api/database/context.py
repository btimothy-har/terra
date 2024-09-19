import asyncio
from contextlib import asynccontextmanager
from datetime import UTC
from datetime import datetime

from sqlalchemy.dialects.postgresql import insert as pg_insert
from weaviate.classes.config import Configure
from weaviate.classes.config import DataType
from weaviate.classes.config import Property
from weaviate.classes.config import Tokenization
from weaviate.classes.query import MetadataQuery
from weaviate.util import generate_uuid5

from api.config import EMBED_MODEL
from api.database.schemas import ContextSchema
from api.models import ContextMessage
from api.utils import AsyncSessionLocal
from api.utils import text_chunk
from api.utils import text_embed
from api.utils import weaviate_session

__all__ = ["embed_context", "setup_context_collection", "search_context"]


@asynccontextmanager
async def database_session():
    async with AsyncSessionLocal() as session:
        yield session


class ContextCollectionError(Exception):
    pass


def setup_context_collection():
    weaviate_client = weaviate_session()

    try:
        context_collection = weaviate_client.collections.get("Context")
        if not context_collection:
            raise ContextCollectionError("Context collection not found.")
    except Exception:
        context_collection = weaviate_client.collections.create(
            "Context",
            vectorizer_config=Configure.Vectorizer.text2vec_openai(model=EMBED_MODEL),
            vector_index_config=Configure.VectorIndex.hnsw(ef=-1),
            properties=[
                Property(
                    name="parent", data_type=DataType.TEXT, skip_vectorization=True
                ),
                Property(
                    name="agent", data_type=DataType.TEXT, skip_vectorization=True
                ),
                Property(
                    name="content",
                    data_type=DataType.TEXT,
                    vectorize_property_name=False,
                    tokenization=Tokenization.WORD,
                ),
            ],
        )
    weaviate_client.close()
    return context_collection


async def embed_context(message: ContextMessage) -> str | None:
    weaviate_client = weaviate_session()

    model_dict = message.model_dump()
    message_id = generate_uuid5(model_dict)

    content_chunks = text_chunk.split_text(message.content)
    if not content_chunks:
        return None

    def embed_chunk(n: int, chunk: str):
        embedding = text_embed.embed_query(chunk)

        chunk_data = {
            "parent": message_id,
            "agent": message.agent,
            "content": _build_content(n, content_chunks),
        }

        context_collection = weaviate_client.collections.get("Context")
        context_collection.data.insert(
            properties=chunk_data,
            vector=embedding,
        )

    await asyncio.gather(
        *[
            asyncio.to_thread(embed_chunk, n, chunk)
            for n, chunk in enumerate(content_chunks)
        ]
    )
    async with database_session() as db:
        stmt = pg_insert(ContextSchema).values(
            id=message_id,
            timestamp=datetime.now(UTC),
            agent=message.agent,
            content=message.content,
        )
        stmt = stmt.on_conflict_do_nothing()

        await db.execute(stmt)
        await db.commit()

    weaviate_client.close()


def search_context(query: str, top_k: int = 10):
    weaviate_client = weaviate_session()

    context_collection = weaviate_client.collections.get("Context")

    response = context_collection.query.near_text(
        query=query,
        limit=top_k,
        return_metadata=MetadataQuery(creation_time=True),
    )
    weaviate_client.close()
    return response.objects


def _build_content(n: int, chunks: list[str]) -> str:
    if len(chunks) == 1:
        return chunks[0]
    elif n == 0:
        return chunks[n] + chunks[n + 1]
    elif n == len(chunks) - 1:
        return chunks[n - 1] + chunks[n]
    else:
        return chunks[n - 1] + chunks[n] + chunks[n + 1]
