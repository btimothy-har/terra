import asyncio
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from typing import Annotated
from typing import Optional

from fastapi import APIRouter
from fastapi import BackgroundTasks
from fastapi import Depends
from fastapi import HTTPException
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import select
from sqlalchemy.sql import update

from api.auth import AuthPayload
from api.auth import NotAuthorizedError
from api.auth import authenticate_request
from api.data.context import ingest_context
from api.data.context import search_context
from api.data.schemas import MessageSchema
from api.data.schemas import ThreadSchema
from api.models import ContextChunk
from api.models import ContextMessage
from api.models import ConversationThread
from api.models import ThreadMessage
from api.utils import database_session
from api.utils import run_in_executor

threads_router = APIRouter(tags=["threads"], prefix="/threads")

DatabaseSession = Annotated[AsyncSession, Depends(database_session)]
UserAuth = Annotated[AuthPayload, Depends(authenticate_request)]


@threads_router.get(
    "/user",
    summary="Gets all conversation threads for a user. Only returns the Thread IDs.",
)
async def get_threads_for_user(
    db: Annotated[AsyncSession, Depends(database_session)], auth: UserAuth
) -> Optional[list[str]]:
    query = await db.execute(
        select(ThreadSchema).filter(
            ThreadSchema.user_id == auth.user_key,
            ThreadSchema.is_deleted.is_(False),
        )
    )
    results = query.scalars().all()
    if results:
        return [t.id for t in results]
    return None


@threads_router.get(
    "/{thread_id}",
    response_model=Optional[ConversationThread],
    summary="Gets a Chat Thread by ID.",
)
async def get_thread_by_id(thread_id: str, db: DatabaseSession, auth: UserAuth):
    query = await db.execute(
        select(ThreadSchema).filter(
            ThreadSchema.id == thread_id,
            ThreadSchema.is_deleted.is_(False),
        )
    )
    result = query.scalar_one_or_none()
    if result:
        try:
            return await run_in_executor(
                ProcessPoolExecutor(), ConversationThread.decrypt, result, auth.data_key
            )
        except NotAuthorizedError as exc:
            raise HTTPException(status_code=401, detail="Not Authorized") from exc
    return None


@threads_router.put(
    "/save",
    summary="Saves a Chat Thread for a user to memory.",
)
async def put_thread_save(
    thread: ConversationThread, db: DatabaseSession, auth: UserAuth
):
    model_dict = await run_in_executor(
        ProcessPoolExecutor(), thread.encrypt, auth.data_key
    )
    stmt = pg_insert(ThreadSchema).values(
        user_id=auth.user_key,
        **model_dict,
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
async def put_thread_delete(thread_id: str, db: DatabaseSession, auth: UserAuth):
    stmt = (
        update(ThreadSchema)
        .where(ThreadSchema.id == thread_id, ThreadSchema.user_id == auth.user_key)
        .values(is_deleted=True)
    )
    await db.execute(stmt)
    await db.commit()


@threads_router.get(
    "/{thread_id}/messages",
    response_model=list[ThreadMessage],
    summary="Gets all messages within a single Thread.",
)
async def get_thread_messages(thread_id: str, db: DatabaseSession, auth: UserAuth):
    query = await db.execute(
        select(MessageSchema).filter(MessageSchema.thread_id == thread_id)
    )
    results = query.scalars().all()
    if results:
        try:
            with ProcessPoolExecutor() as executor:
                decrypted_results = await asyncio.gather(
                    *(
                        run_in_executor(
                            executor, ThreadMessage.decrypt, m, auth.data_key
                        )
                        for m in results
                    )
                )
                return decrypted_results
        except NotAuthorizedError as exc:
            raise HTTPException(status_code=401, detail="Not Authorized") from exc
    return []


@threads_router.get(
    "/{thread_id}/messages/{message_id}",
    response_model=Optional[ThreadMessage],
    summary="Finds a Chat Message by ID.",
)
async def get_message_by_id(
    thread_id: str, message_id: str, db: DatabaseSession, auth: UserAuth
):
    query = await db.execute(
        select(MessageSchema).filter(
            MessageSchema.id == message_id,
            MessageSchema.thread_id == thread_id,
        )
    )
    result = query.scalar_one_or_none()
    if result:
        try:
            return await run_in_executor(
                ProcessPoolExecutor(), ThreadMessage.decrypt, result, auth.data_key
            )
        except NotAuthorizedError as exc:
            raise HTTPException(status_code=401, detail="Not Authorized") from exc
    return None


@threads_router.put(
    "/{thread_id}/messages/new", summary="Saves a Chat Message to the Thread ID."
)
async def put_thread_message(
    thread_id: str, message: ThreadMessage, db: DatabaseSession, auth: UserAuth
):
    thread = await get_thread_by_id(thread_id, db, auth)
    if not thread:
        raise HTTPException(
            status_code=400, detail="A thread must exist before saving a message."
        )
    encrypted_message = await run_in_executor(
        ProcessPoolExecutor(), message.encrypt, auth.data_key
    )

    stmt = pg_insert(MessageSchema).values(
        thread_id=thread_id,
        **encrypted_message,
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
def post_context_save(
    background_tasks: BackgroundTasks, messages: list[ContextMessage]
) -> str | None:
    in_messages = [
        m for m in messages if m.content and m.agent not in ["Supervisor", "Archivist"]
    ]
    ingest_context(in_messages)
    # background_tasks.add_task(ingest_context, messages)
    return


@threads_router.get(
    "/context/search",
    response_model=list[ContextChunk],
    summary="Gets conversation context from memory, by vector search.",
    description="""
    Allows AI agents to retrieve stored context in memory.
    """,
)
def get_context_search(query: str, top_k: int = 10):
    results = search_context(query, top_k)

    return [
        ContextChunk(
            timestamp=datetime.fromisoformat(r.metadata["timestamp"]),
            agent=r.metadata["agent"],
            content=r.text,
        )
        for r in results
    ]
