import logging
import os

from langchain_experimental.text_splitter import SemanticChunker
from langchain_openai import OpenAIEmbeddings
from psycopg_pool import AsyncConnectionPool
from redis.asyncio import Redis

import api.config as config

logger = logging.getLogger("uvicorn.error")

text_embed = OpenAIEmbeddings(
    model="text-embedding-3-small",
    dimensions=config.CONTEXT_DIM,
    api_key=os.getenv("OPENAI_API_KEY"),
)

text_chunk = SemanticChunker(
    embeddings=text_embed,
    breakpoint_threshold_type="standard_deviation",
    breakpoint_threshold_amount=0.5,
)


async def postgres() -> AsyncConnectionPool:
    database = AsyncConnectionPool(config.POSTGRES_URL, open=False)
    await database.open()
    return database


async def redis() -> Redis:
    redis = Redis(
        host="redis",
        port=6379,
        decode_responses=True,
        auto_close_connection_pool=False,
    )
    return redis
