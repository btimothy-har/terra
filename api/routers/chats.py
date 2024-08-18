import asyncio
from typing import Optional

import numpy as np
from crud import cache
from crud import database as db
from crud import embeddings as emb
from fastapi import APIRouter
from fastapi import BackgroundTasks
from fastapi import Request
from fastapi.exceptions import HTTPException
from pydantic import BaseModel
from redis.commands.search.query import Query

from shared.models.message import ThreadMessage
from shared.models.thread import ConversationThread


class APIMessage(ThreadMessage):
    thread_id: str
    session_id: str
    user_id: str


class MessageContext(BaseModel):
    thread_id: str
    message_id: str
    messages: list[dict]


class ContextQuery(BaseModel):
    query: str
    top_k: int = 3


class ContextChunk(BaseModel):
    timestamp: str
    title: str
    content: str
    vector_score: float


threads_router = APIRouter(tags=["threads"], prefix="/threads")


@threads_router.get(
    "/{thread_id}",
    response_model=Optional[ConversationThread],
    summary="Gets a Chat Thread by ID.",
)
async def get_thread_id(
    request: Request,
    background_tasks: BackgroundTasks,
    thread_id: str,
    user_id: str,
):
    cached_thread = await cache.get_thread(
        request.app.cache, user_id=user_id, thread_id=thread_id
    )
    if cached_thread:
        return cached_thread

    db_thread = await db.fetch_thread(
        request.app.database, thread_id=thread_id, user_id=user_id
    )
    if db_thread:
        background_tasks.add_task(
            cache.put_thread, request.app.cache, user_id, db_thread
        )
        return db_thread
    return None


@threads_router.put("/save", summary="Saves a Chat Thread for a user to memory.")
async def put_thread_save(request: Request, user_id: str, thread: ConversationThread):
    await cache.put_thread(request.app.cache, user_id, thread)
    await db.insert_thread(request.app.database, thread)


@threads_router.put(
    "/{thread_id}/delete", summary="Delets a Chat Thread for a user to memory."
)
async def put_thread_delete(
    request: Request, background_tasks: BackgroundTasks, user_id: str, thread_id: str
):
    thread = await get_thread_id(request, background_tasks, thread_id, user_id)

    if not thread:
        raise HTTPException(status_code=400, detail="Thread does not exist.")

    background_tasks.add_task(db.delete_thread, request.app.database, thread.thread_id)
    await cache.delete_thread(request.app.cache, user_id, thread.thread_id)


@threads_router.get(
    "/{thread_id}/messages", summary="Gets all messages within a single Thread."
)
async def get_thread_messages(
    request: Request, background_tasks: BackgroundTasks, thread_id: str
) -> list[ThreadMessage]:
    message_ids = await cache.get_thread_messages(request.app.cache, thread_id)
    if not message_ids:
        message_ids = await db.fetch_thread_messages(request.app.database, thread_id)
        background_tasks.add_task(
            cache.put_thread_messages, request.app.cache, thread_id, message_ids
        )

    if message_ids:
        get_messages = await asyncio.gather(
            *[
                get_message_id(request, background_tasks, message_id)
                for message_id in message_ids
            ]
        )
        messages = [msg for msg in get_messages if msg]
        messages.sort(key=lambda x: x.timestamp)
        return messages
    return []


@threads_router.post(
    "/context/save",
    summary="Stores conversation context in memory, and vectorizes them for later use.",
    description="""
    Allows AI agents to store external context in memory by Thread ID, and vectorized for later use.
    Vectorization is handled in the background in FastAPI.
    Data does not persist.
    """,
    status_code=202,
)
async def put_context_save(
    request: Request, background_tasks: BackgroundTasks, context: MessageContext
):
    for i, m in enumerate(context.messages):
        message = emb.MessageToEmbed(
            num=i, thread_id=context.thread_id, message_id=context.message_id, **m
        )

        if message.title in ["Supervisor", "Archivist"]:
            continue
        if not message.content:
            continue

        background_tasks.add_task(
            emb.embed_message,
            request.app.cache,
            request.app.text_splitter,
            request.app.text_embedder,
            message,
        )
    return


@threads_router.get(
    "/context/search",
    summary="Gets conversation context from memory, by vector search.",
    description="""
    Allows AI agents to retrieve stored context in memory.
    """,
)
async def get_context_search(
    request: Request, query: str, top_k: int = 9
) -> list[ContextChunk]:
    index_info = await request.app.cache.ft("idx:context").info()
    request.app.logger.info(f"index count: {index_info['num_docs']}")
    request.app.logger.info(f"index status: {index_info['hash_indexing_failures']}")

    embed_query = await request.app.text_embedder.aembed_query(query)

    cache_query = (
        Query(f"(*)=>[KNN {top_k} @embeddings $query_vector AS vector_score]")
        .sort_by("vector_score", asc=True)
        .return_fields("vector_score", "timestamp", "title", "content")
        .dialect(2)
    )

    result = await request.app.cache.ft("idx:context").search(
        cache_query, {"query_vector": np.array(embed_query, dtype=np.float32).tobytes()}
    )

    return [
        ContextChunk(
            timestamp=r["timestamp"],
            title=r["title"],
            content=r["content"],
            vector_score=r["vector_score"],
        )
        for r in result.docs
    ]


messages_router = APIRouter(tags=["messages"], prefix="/messages")


@messages_router.get(
    "/{message_id}",
    response_model=Optional[ThreadMessage],
    summary="Finds a Chat Message by ID.",
)
async def get_message_id(
    request: Request, background_tasks: BackgroundTasks, message_id: str
) -> Optional[ThreadMessage]:
    cached_message = await cache.get_message(request.app.cache, message_id=message_id)
    if cached_message:
        return cached_message

    db_message = await db.fetch_message(request.app.database, message_id=message_id)
    if db_message:
        background_tasks.add_task(cache.put_message, request.app.cache, db_message)
        return db_message
    return None


@messages_router.put(
    "/save", summary="Saves a Chat Message to the Thread ID.", status_code=202
)
async def put_message_save(
    request: Request, background_tasks: BackgroundTasks, message: APIMessage
):
    # check if thread exists, otherwise raise error
    thread = await get_thread_id(
        request, background_tasks, message.thread_id, message.user_id
    )
    if not thread:
        raise HTTPException(
            status_code=400, detail="A thread must exist before saving a message."
        )

    background_tasks.add_task(cache.put_message, request.app.cache, message)
    background_tasks.add_task(
        cache.put_thread_messages, request.app.cache, message.thread_id, [message.id]
    )
    background_tasks.add_task(
        db.insert_message,
        request.app.database,
        message.session_id,
        message.thread_id,
        message,
    )
