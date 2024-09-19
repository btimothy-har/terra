import asyncio
from contextlib import asynccontextmanager

from weaviate.classes.config import Configure
from weaviate.classes.config import DataType
from weaviate.classes.config import Property
from weaviate.classes.config import Tokenization
from weaviate.classes.query import MetadataQuery
from weaviate.util import generate_uuid5

from api.config import EMBED_MODEL
from api.models import ContextMessage
from api.utils import text_chunk
from api.utils import text_embed
from api.utils import weaviate_client

__all__ = ["embed_context", "setup_context_collection", "search_context"]


@asynccontextmanager
async def weaviate_session():
    async with weaviate_client as client:
        yield client


class ContextCollectionError(Exception):
    pass


async def setup_context_collection():
    async with weaviate_session() as weaviate:
        try:
            context_collection = weaviate.collections.get("Context")
            if not context_collection:
                raise ContextCollectionError("Context collection not found.")
        except Exception:
            context_collection = await weaviate.collections.create(
                "Context",
                vectorizer_config=Configure.Vectorizer.text2vec_openai(
                    model=EMBED_MODEL
                ),
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
        return context_collection


async def embed_context(message: ContextMessage) -> str | None:
    model_dict = message.model_dump()

    message_id = generate_uuid5(model_dict)

    content_chunks = text_chunk.split_text(message.content)
    if not content_chunks:
        return None

    async def embed_chunk(n: int, chunk: str):
        embedding = await text_embed.aembed_query(chunk)

        chunk_data = {
            "parent": message_id,
            "agent": message.agent,
            "content": _build_content(n, content_chunks),
        }

        async with weaviate_session() as weaviate:
            context_collection = weaviate.collections.get("Context")
            await context_collection.data.insert(
                properties=chunk_data,
                vector=embedding,
            )

    await asyncio.gather(
        *[embed_chunk(n, chunk) for n, chunk in enumerate(content_chunks)]
    )
    return message_id


async def search_context(query: str, top_k: int = 10):
    async with weaviate_session() as weaviate:
        context_collection = weaviate.collections.get("Context")

        response = await context_collection.query.near_text(
            query=query,
            limit=top_k,
            return_metadata=MetadataQuery(creation_time=True),
        )
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
