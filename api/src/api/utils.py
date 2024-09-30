import asyncio
import logging
import os
from langchain_experimental.text_splitter import SemanticChunker
from langchain_openai import OpenAIEmbeddings
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker

import api.config as config

logger = logging.getLogger("uvicorn.error")

text_embed = OpenAIEmbeddings(
    model=config.EMBED_MODEL,
    dimensions=config.EMBED_DIM,
    api_key=os.getenv("OPENAI_API_KEY"),
)

text_chunk = SemanticChunker(
    embeddings=text_embed,
    breakpoint_threshold_type="standard_deviation",
    breakpoint_threshold_amount=0.5,
)

engine = create_async_engine(f"postgresql+asyncpg://{config.POSTGRES_URL}")
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def database_session():
    async with AsyncSessionLocal() as session:
        yield session


async def run_in_executor(executor, func, *args):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, func, *args)
