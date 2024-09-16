import asyncio
import hashlib

from sqlalchemy.dialects.postgresql import insert as pg_insert

from api.clients import database_session
from api.clients import text_chunk
from api.clients import text_embed
from api.src.api.models.models import ContextMessage

from .schemas import ContextSchema

__all__ = ["embed_context_message"]


async def embed_context_message(message: ContextMessage):
    content_chunks = text_chunk.split_text(message.content)
    if not content_chunks:
        return None

    async def embed_chunk(n: int, chunk: str):
        def chunk_id(n: int) -> str:
            components = f"{message.thread_id}:{message.message_id}:{message.id}:{n}"
            return hashlib.md5(components.encode()).hexdigest()

        embedding = await text_embed.aembed_query(chunk)

        return {
            "id": chunk_id(n),
            "thread": message.thread_id,
            "message": message.message_id,
            "chunk": n,
            "agent": message.agent,
            "content": _build_content(n, content_chunks),
            "embedding": embedding,
        }

    insert_content = await asyncio.gather(
        *[embed_chunk(n, chunk) for n, chunk in enumerate(content_chunks)]
    )

    async with database_session() as db:
        stmt = pg_insert(ContextSchema).values(insert_content)
        stmt = stmt.on_conflict_do_nothing()
        await db.execute(stmt)
        await db.commit()


def _build_content(n: int, chunks: list[str]) -> str:
    if len(chunks) == 1:
        return chunks[0]
    elif n == 0:
        return chunks[n] + chunks[n + 1]
    elif n == len(chunks) - 1:
        return chunks[n - 1] + chunks[n]
    else:
        return chunks[n - 1] + chunks[n] + chunks[n + 1]
