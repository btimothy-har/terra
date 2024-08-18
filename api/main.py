import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from langchain_experimental.text_splitter import SemanticChunker
from langchain_openai import OpenAIEmbeddings
from psycopg_pool import AsyncConnectionPool
from redis import exceptions as redis_exceptions
from redis.asyncio import Redis
from redis.commands.search.field import NumericField
from redis.commands.search.field import TextField
from redis.commands.search.field import VectorField
from redis.commands.search.indexDefinition import IndexDefinition
from redis.commands.search.indexDefinition import IndexType
from routers.chats import messages_router
from routers.chats import threads_router
from routers.users import router as users_router

EMBEDDINGS = OpenAIEmbeddings(
    model="text-embedding-3-small", dimensions=768, api_key=os.getenv("OPENAI_API_KEY")
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

schema = (
    TextField("$.thread_id", no_stem=True, as_name="thread_id"),
    TextField("$.message_id", no_stem=True, as_name="message_id"),
    NumericField("$.message_num", as_name="message_num"),
    NumericField("$.chunk_num", as_name="chunk_num"),
    TextField("$.timestamp", as_name="timestamp"),
    TextField("$.title", as_name="title"),
    TextField("$.content", as_name="content"),
    VectorField(
        "$.embeddings",
        "FLAT",
        {
            "TYPE": "FLOAT32",
            "DIM": 768,
            "DISTANCE_METRIC": "COSINE",
        },
        as_name="embeddings",
    ),
)
definition = IndexDefinition(prefix=["context:"], index_type=IndexType.JSON)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.logger = LOGGER
    app.text_splitter = CHUNKER
    app.text_embedder = EMBEDDINGS

    app.database = POSTGRES
    app.cache = REDIS

    try:
        await app.cache.ft("idx:context").create_index(
            fields=schema, definition=definition
        )
    except redis_exceptions.ResponseError:
        index_info = await app.cache.ft("idx:context").info()
        app.logger.warning(f"Index idx:content already exists. \
{index_info['num_docs']} documents indexed with {index_info['hash_indexing_failures']} failures.")
    else:
        app.logger.info("Index idx:content created.")

    await app.database.open()
    app.logger.info("Database and cache connections established.")

    # await app.cache.ft("idx:context").dropindex(delete_documents=True)

    yield

    await app.database.close()
    await app.cache.close()


app = FastAPI(lifespan=lifespan)

app.include_router(users_router)
app.include_router(threads_router)
app.include_router(messages_router)
