import asyncio
import os
from contextlib import asynccontextmanager
from typing import Optional
from uuid import UUID

from crud import cache
from crud import database as db
from fastapi import Depends
from fastapi import FastAPI
from fastapi import Request
from psycopg_pool import AsyncConnectionPool
from redis.asyncio import Redis

from shared.models.session import Session
from shared.models.user import User

POSTGRES_URL = f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@postgres:5432/terra"
POSTGRES = AsyncConnectionPool(POSTGRES_URL,open=False)

REDIS = Redis(
    host="redis",
    port=6379,
    decode_responses=True,
    auto_close_connection_pool=False
    )

@asynccontextmanager
async def lifespan(app:FastAPI):
    app.database = POSTGRES
    await app.database.open()
    await app.database.wait()

    app.cache = REDIS
    await app.cache.ping()

    yield

    app.database.close()
    app.cache.close()


app = FastAPI(lifespan=lifespan)

@app.get("/")
async def main():
    sql = """
        SELECT *
        FROM
            users.sessions as ts
        ORDER BY
            ts.timestamp DESC
        LIMIT 1;
        """

    with app.database.connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql)
            raw_data = cursor.fetchone()
    return raw_data

@app.put("/users/save")
async def save_user(user:User):
    await cache.put_user(app.cache, user)
    await db.insert_user(app.database, user)


@app.get("/session/find", response_model=Optional[Session])
async def resume_session(session_id:UUID):
    cached_session = await cache.get_session(app.cache, session_id)
    if cached_session:
        return cached_session

    db_session = await db.fetch_session(app.database, session_id)
    if db_session:
        asyncio.create_task(
            cache.add_session(app.cache, db_session)
            )
        return db_session
    return None


@app.put("/session/save")
async def save_session(session:Session):
    await cache.add_session(app.cache, session)
    await db.insert_session(app.database, session)
