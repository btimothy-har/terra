from typing import Optional
from uuid import UUID

from psycopg_pool import AsyncConnectionPool

from shared.models.session import Session
from shared.models.user import User

from .sql import FETCH_SESSION
from .sql import FETCH_USER
from .sql import INSERT_SESSION
from .sql import INSERT_USER


async def insert_user(database: AsyncConnectionPool, user:User):
    async with database.connection() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(
                INSERT_USER,
                (
                    user.id,
                    user.email,
                    user.name,
                    user.given_name,
                    user.family_name,
                    user.picture
                    )
                )

async def fetch_user(database:AsyncConnectionPool, user_id:str) -> Optional[User]:
    async with database.connection() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(FETCH_USER, (user_id,))
            raw_data = await cursor.fetchone()

    if raw_data:
        user = User(
            id=user_id,
            email=raw_data[0],
            name=raw_data[1],
            given_name=raw_data[2],
            family_name=raw_data[3],
            picture=raw_data[4]
            )
        return user
    return None

async def insert_session(database:AsyncConnectionPool, session:User):
    async with database.connection() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(
                INSERT_SESSION,
                (session.id, session.user.id, session.timestamp, session.credentials)
                )

async def fetch_session(database:AsyncConnectionPool, session_id:UUID) -> Optional[Session]:
    print("fetching session from db")
    async with database.connection() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(
                FETCH_SESSION,
                (str(session_id),)
            )
            raw_data = await cursor.fetchone()

    if raw_data:
        session = Session(
            id=session_id,
            timestamp=raw_data[1],
            user=User(
                id=raw_data[0],
                email=raw_data[2],
                name=raw_data[3],
                given_name=raw_data[4],
                family_name=raw_data[5],
                picture=raw_data[6]
                ),
            credentials=raw_data[7]
            )
        return session
    return None
