from crud import embeddings as emb
from crud import sql as crud_sql
from fastapi import FastAPI
from psycopg_pool import AsyncConnectionPool
from redis.asyncio import Redis


async def load_context_to_mem(
    app: FastAPI, database: AsyncConnectionPool, cache: Redis
):
    async with database.connection() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(crud_sql.FETCH_ALL_CONTEXT)
            raw_data = await cursor.fetchall()

    if not raw_data:
        app.logger.info("No context data found in database.")
        return

    ct = 0
    for row in raw_data:
        context = emb.EmbeddedChunk(
            thread_id=row[1],
            message_id=row[2],
            message_num=row[3],
            chunk_num=row[4],
            timestamp=row[5],
            title=row[6],
            content=row[7],
            embeddings=row[8],
        )
        await cache.json().set(row[0], "$", context.model_dump_json())
        ct += 1
    app.logger.info(f"Loaded {ct} context items into memory.")
