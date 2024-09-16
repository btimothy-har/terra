from typing import Optional

from fastapi import APIRouter
from fastapi import BackgroundTasks
from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.sql import select
from sqlalchemy.sql import update

from api.clients import database_session
from api.clients import text_embed
from api.database.schemas import ContextSchema
from api.database.schemas import MessageSchema
from api.database.schemas import ThreadSchema
from api.database.utils import embed_context_message
from api.models import ContextChunk
from api.models import ContextMessage
from api.models import ConversationThread
from api.models import ThreadMessage

threads_router = APIRouter(tags=["threads"], prefix="/threads")


@threads_router.get(
    "/{thread_id}",
    response_model=Optional[ConversationThread],
    summary="Gets a Chat Thread by ID.",
)
async def get_thread_by_id(thread_id: str):
    async with database_session() as db:
        query = await db.execute(
            select(ThreadSchema).filter(
                ThreadSchema.id == thread_id,
                ThreadSchema.is_deleted.is_(False),
            )
        )
        result = query.scalar_one_or_none()
    if result:
        return ConversationThread.model_validate(result)
    return None


@threads_router.put(
    "/save",
    response_model=ConversationThread,
    summary="Saves a Chat Thread for a user to memory.",
)
async def put_thread_save(thread: ConversationThread):
    async with database_session() as db:
        stmt = pg_insert(ThreadSchema).values(
            **thread.model_dump(exclude={"messages"}),
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["id"],
            set_={
                "summary": stmt.excluded.summary,
                "last_used": stmt.excluded.last_used,
            },
        )
        await db.execute(stmt)
        await db.commit()


@threads_router.put(
    "/{thread_id}/delete", summary="Delets a Chat Thread for a user to memory."
)
async def put_thread_delete(thread_id: str):
    async with database_session() as db:
        stmt = (
            update(ThreadSchema)
            .where(ThreadSchema.id == thread_id)
            .values(is_deleted=True)
        )
        await db.execute(stmt)
        await db.commit()


@threads_router.get(
    "/{thread_id}/messages",
    response_model=list[ThreadMessage],
    summary="Gets all messages within a single Thread.",
)
async def get_thread_messages(thread_id: str):
    async with database_session() as db:
        query = await db.execute(
            select(MessageSchema).filter(MessageSchema.thread_id == thread_id)
        )
        results = query.scalars().all()
    if results:
        return [ThreadMessage.model_validate(m) for m in results]
    return []


@threads_router.put(
    "/{thread_id}/messages/{message_id}",
    response_model=Optional[ThreadMessage],
    summary="Finds a Chat Message by ID.",
)
async def get_message_by_id(thread_id: str, message_id: str):
    async with database_session() as db:
        query = await db.execute(
            select(MessageSchema).filter(
                MessageSchema.id == message_id,
                MessageSchema.thread_id == thread_id,
            )
        )
        result = query.scalar_one_or_none()
    if result:
        return ThreadMessage.model_validate(result)
    return None


@threads_router.put(
    "/{thread_id}/messages/new", summary="Saves a Chat Message to the Thread ID."
)
async def put_thread_message(thread_id: str, message: ThreadMessage):
    thread = await get_thread_by_id(thread_id)
    if not thread:
        raise HTTPException(
            status_code=400, detail="A thread must exist before saving a message."
        )

    async with database_session() as db:
        stmt = pg_insert(MessageSchema).values(
            thread_id=thread_id,
            **message.model_dump(),
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["id"],
            set_={
                "role": stmt.excluded.role,
                "content": stmt.excluded.content,
            },
        )
        await db.execute(stmt)
        await db.commit()


@threads_router.post(
    "/context/save",
    summary="Stores conversation context in memory, and vectorizes them for later use.",
    description="""
    Allows AI agents to store external context in memory by Thread ID, and vectorized
    for later use. Vectorization is handled in the background in FastAPI.
    """,
    status_code=202,
)
async def put_context_save(background_tasks: BackgroundTasks, message: ContextMessage):
    if not message.content:
        return
    if message.agent in ["Supervisor", "Archivist"]:
        return

    background_tasks.add_task(embed_context_message, message)


@threads_router.get(
    "/context/search",
    response_model=list[ContextChunk],
    summary="Gets conversation context from memory, by vector search.",
    description="""
    Allows AI agents to retrieve stored context in memory.
    """,
)
async def get_context_search(query: str, top_k: int = 10):
    embedding_array = func.array(await text_embed.aembed_query(query))

    async with database_session() as db:
        stmt = (
            select(ContextSchema)
            .order_by(ContextSchema.embedding.cosine_distance(embedding_array))
            .limit(top_k)
        )
        results = db.execute(stmt).scalars().all()

    return [
        ContextChunk(
            timestamp=r.timestamp,
            agent=r.agent,
            content=r.content,
        )
        for r in results
    ]
