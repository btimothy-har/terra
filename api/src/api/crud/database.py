from typing import Optional
from uuid import UUID

from psycopg_pool import AsyncConnectionPool

from shared.models.message import ThreadMessage
from shared.models.session import Session
from shared.models.thread import ConversationThread
from shared.models.user import User

from .sql import DELETE_THREAD
from .sql import FETCH_MESSAGE
from .sql import FETCH_SESSION
from .sql import FETCH_THREAD_ID
from .sql import FETCH_THREAD_MESSAGES
from .sql import FETCH_USER
from .sql import FETCH_USER_THREADS
from .sql import INSERT_MESSAGE
from .sql import INSERT_SESSION
from .sql import INSERT_USER
from .sql import PUT_THREAD_SAVE


async def fetch_user(database: AsyncConnectionPool, user_id: str) -> Optional[User]:
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
            picture=raw_data[4],
        )
        return user
    return None


async def insert_user(database: AsyncConnectionPool, user: User):
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
                    user.picture,
                ),
            )


async def fetch_session(
    database: AsyncConnectionPool, session_id: str
) -> Optional[Session]:
    async with database.connection() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(FETCH_SESSION, (session_id,))
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
                picture=raw_data[6],
            ),
            credentials=raw_data[7],
        )
        return session
    return None


async def insert_session(database: AsyncConnectionPool, session: User):
    async with database.connection() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(
                INSERT_SESSION,
                (session.id, session.user.id, session.timestamp, session.credentials),
            )


async def fetch_user_threads(
    database: AsyncConnectionPool, user_id: str
) -> Optional[list[ConversationThread]]:
    async with database.connection() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(FETCH_USER_THREADS, (user_id,))
            raw_data = await cursor.fetchall()

    if raw_data:
        thread_ids = [row[0] for row in raw_data]
        return thread_ids
    return None


async def fetch_thread(
    database: AsyncConnectionPool, user_id: str, thread_id: str
) -> Optional[ConversationThread]:
    async with database.connection() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(FETCH_THREAD_ID, (thread_id, user_id))
            raw_data = await cursor.fetchone()

    if raw_data:
        thread = ConversationThread(
            sid=raw_data[0],
            thread_id=raw_data[1],
            summary=raw_data[2],
            last_used=raw_data[3],
            messages=[],
        )
        return thread
    return None


async def insert_thread(database: AsyncConnectionPool, thread: ConversationThread):
    async with database.connection() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(
                PUT_THREAD_SAVE,
                (thread.sid, thread.thread_id, thread.summary, thread.last_used),
            )


async def delete_thread(database: AsyncConnectionPool, thread_id: str):
    async with database.connection() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(DELETE_THREAD, (thread_id,))


async def fetch_thread_messages(
    database: AsyncConnectionPool, thread_id: str
) -> Optional[list[str]]:
    async with database.connection() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(FETCH_THREAD_MESSAGES, (thread_id,))
            raw_data = await cursor.fetchall()

    if raw_data:
        message_ids = [row[0] for row in raw_data]
        return message_ids
    return None


async def fetch_message(
    database: AsyncConnectionPool, message_id: str
) -> Optional[ThreadMessage]:
    async with database.connection() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(FETCH_MESSAGE, (message_id,))
            raw_data = await cursor.fetchone()

    if raw_data:
        message = ThreadMessage(
            id=message_id, role=raw_data[0], content=raw_data[1], timestamp=raw_data[2]
        )
        return message
    return None


async def insert_message(
    database: AsyncConnectionPool,
    session_id: str,
    thread_id: str,
    message: ThreadMessage,
) -> UUID:
    async with database.connection() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(
                INSERT_MESSAGE,
                (
                    session_id,
                    thread_id,
                    message.id,
                    message.role,
                    message.content,
                    message.timestamp,
                ),
            )
