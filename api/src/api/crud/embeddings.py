from datetime import datetime
from datetime import timezone

from pydantic import BaseModel
from redis.asyncio import Redis

import api.config as config
from api.clients import text_chunk
from api.clients import text_embed


class MessageToEmbed(BaseModel):
    num: int
    thread_id: str
    message_id: str
    title: str
    content: str


class EmbeddedChunk(BaseModel):
    thread_id: str
    message_id: str
    message_num: int
    chunk_num: int
    timestamp: datetime
    title: str
    content: str
    embeddings: list[float]

    @property
    def key(self) -> str:
        return (
            f"{config.CONTEXT_PREFIX}:{self.thread_id}:{self.message_id}:{self.message_num}:"
            f"{self.chunk_num}"
        )


def build_content(n: int, chunks: list[str]) -> str:
    if len(chunks) == 1:
        return chunks[0]
    elif n == 0:
        return chunks[n] + chunks[n + 1]
    elif n == len(chunks) - 1:
        return chunks[n - 1] + chunks[n]
    else:
        return chunks[n - 1] + chunks[n] + chunks[n + 1]


async def embed_message(
    cache: Redis,
    message: MessageToEmbed,
):
    content_chunks = text_chunk.split_text(message.content)
    if not content_chunks:
        return

    for n, chunk in enumerate(content_chunks):
        embedding = await text_embed.aembed_query(chunk)
        embedded = EmbeddedChunk(
            thread_id=message.thread_id,
            message_id=message.message_id,
            message_num=message.num,
            chunk_num=n,
            timestamp=datetime.now(timezone.utc),
            title=message.title,
            content=build_content(n, content_chunks),
            embeddings=embedding,
        )

        await cache.json().set(embedded.key, "$", embedded.model_dump(mode="json"))
