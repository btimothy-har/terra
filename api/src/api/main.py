import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from langchain_experimental.text_splitter import SemanticChunker
from langchain_openai import OpenAIEmbeddings
from psycopg_pool import AsyncConnectionPool
from redis import exceptions as redis_exceptions
from redis.asyncio import Redis
from redis.commands.search.indexDefinition import IndexDefinition
from redis.commands.search.indexDefinition import IndexType

import api.config as config
from api.routers import messages_router
from api.routers import threads_router
from api.routers import users_router

EMBEDDINGS = OpenAIEmbeddings(
    model="text-embedding-3-small",
    dimensions=config.CONTEXT_DIM,
    api_key=os.getenv("OPENAI_API_KEY"),
)

CHUNKER = SemanticChunker(
    embeddings=EMBEDDINGS,
    breakpoint_threshold_type="standard_deviation",
    breakpoint_threshold_amount=0.5,
)

POSTGRES_URL = f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@postgres:5432/terra"
POSTGRES = AsyncConnectionPool(POSTGRES_URL, open=False)

REDIS = Redis(
    host="redis", port=6379, decode_responses=True, auto_close_connection_pool=False
)

LOGGER = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.logger = LOGGER
    app.text_splitter = CHUNKER
    app.text_embedder = EMBEDDINGS

    app.database = POSTGRES
    app.cache = REDIS

    try:
        await app.cache.ft(config.CONTEXT_INDEX).create_index(
            fields=config.CONTEXT_SCHEMA,
            definition=IndexDefinition(
                prefix=[config.CONTEXT_PREFIX + ":"], index_type=IndexType.JSON
            ),
        )
    except redis_exceptions.ResponseError:
        index_info = await app.cache.ft(config.CONTEXT_INDEX).info()
        app.logger.warning(
            f"Index {config.CONTEXT_INDEX} already exists. "
            f"{index_info['num_docs']} documents indexed with "
            f"{index_info['hash_indexing_failures']} failures."
        )
    else:
        index_info = await app.cache.ft(config.CONTEXT_INDEX).info()
        app.logger.warning(
            f"Index {config.CONTEXT_INDEX} created. "
            f"{index_info['num_docs']} documents indexed with "
            f"{index_info['hash_indexing_failures']} failures."
        )

    await app.database.open()
    app.logger.info("Database and cache connections established.")

    yield

    await app.database.close()
    await app.cache.close()


app = FastAPI(lifespan=lifespan)

app.include_router(users_router)
app.include_router(threads_router)
app.include_router(messages_router)
