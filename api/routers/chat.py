import asyncio
from typing import Optional

import numpy as np
from crud import cache
from crud import database as db
from fastapi import APIRouter
from fastapi import BackgroundTasks
from fastapi import Request
from fastapi.exceptions import HTTPException
from pydantic import BaseModel
from redis.commands.search.query import Query

from shared.models.message import ThreadMessage
from shared.models.thread import ConversationThread


class MessageContext(BaseModel):
    thread_id:str
    message_id:str
    messages:list[dict]

router = APIRouter(
    tags=["chat"],
    prefix="/chat"
)

@router.get("/thread/id",
    response_model=Optional[ConversationThread],
    summary="Gets a Chat Thread by ID.")
async def get_thread_id(
    thread_id:str,
    user_id:str,
    request:Request,
    background_tasks:BackgroundTasks):

    cached_thread = await cache.get_thread(
        request.app.cache,
        user_id=user_id,
        thread_id=thread_id)
    if cached_thread:
        return cached_thread

    db_thread = await db.fetch_thread(
        request.app.database,
        thread_id=thread_id,
        user_id=user_id)
    if db_thread:
        background_tasks.add_task(cache.put_thread, request.app.cache, user_id, db_thread)
        return db_thread
    return None

@router.put("/thread/save",
    summary="Saves a Chat Thread for a user to memory.")
async def put_thread_save(
    user_id:str,
    thread:ConversationThread,
    request:Request):

    await cache.put_thread(request.app.cache, user_id, thread)
    await db.insert_thread(request.app.database, thread)

@router.put("/thread/delete",
    summary="Delets a Chat Thread for a user to memory.")
async def put_thread_delete(
    user_id:str,
    thread_id:str,
    request:Request,
    background_tasks:BackgroundTasks):

    thread = await get_thread_id(thread_id, user_id, request, background_tasks)

    if not thread:
        raise HTTPException(status_code=400, detail="Thread does not exist.")

    background_tasks.add_task(db.delete_thread, request.app.database, thread.thread_id)
    await cache.delete_thread(request.app.cache, user_id, thread.thread_id)

@router.get("/thread/messages",
    summary="Gets all messages within a single Thread.")
async def get_thread_messages(
    thread_id:str,
    request:Request,
    background_tasks:BackgroundTasks) -> list[ThreadMessage]:

    message_ids = await cache.get_thread_messages(request.app.cache, thread_id)
    if not message_ids:
        message_ids = await db.fetch_thread_messages(request.app.database, thread_id)
        background_tasks.add_task(cache.put_thread_messages, request.app.cache, thread_id, message_ids)

    if message_ids:
        get_messages = await asyncio.gather(
            *[get_message_id(message_id, request, background_tasks) for message_id in message_ids]
            )
        messages = [msg for msg in get_messages if msg]
        messages.sort(key=lambda x: x.timestamp)
        return messages
    return []

@router.get("/message/id",
    response_model=Optional[ThreadMessage],
    summary="Finds a Chat Message by ID.")
async def get_message_id(
    message_id:str,
    request:Request,
    background_tasks:BackgroundTasks) -> Optional[ThreadMessage]:

    cached_message = await cache.get_message(
        request.app.cache,
        message_id=message_id)
    if cached_message:
        return cached_message

    db_message = await db.fetch_message(
        request.app.database,
        message_id=message_id)
    if db_message:
        background_tasks.add_task(cache.put_message, request.app.cache, db_message)
        return db_message
    return None

@router.put("/message/save",
    summary="Saves a Chat Message to the Thread ID.")
async def put_message_save(
    thread_id:str,
    session_id:str,
    user_id:str,
    message:ThreadMessage,
    request:Request,
    background_tasks:BackgroundTasks):

    # check if thread exists, otherwise raise error
    thread = await get_thread_id(thread_id, user_id, request, background_tasks)
    if not thread:
        raise HTTPException(status_code=400, detail="A thread must exist before saving a message.")

    background_tasks.add_task(db.insert_message, request.app.database, session_id, thread_id, message)

    await cache.put_message(request.app.cache, message)
    await cache.put_thread_messages(request.app.cache, thread_id, [message.id])

@router.post("/context/save",
    summary="Stores conversation context in memory, and vectorizes them for later use.",
    description=
    """
    Allows AI agents to store external context in memory by Thread ID, and vectorized for later use.
    Context is secured by Thread ID to prevent cross-contamination.
    Vectorization is handled in the background in FastAPI.
    Data does not persist.
    """,
    status_code=202)
async def put_context_save(context:MessageContext, request:Request, background_tasks:BackgroundTasks):
    for i, m in enumerate(context.messages):
        message = cache.MessageToEmbed(
            num=i,
            thread_id=context.thread_id,
            message_id=context.message_id,
            **m)

        if message.title == "Supervisor":
            continue
        if not message.content:
            continue
        background_tasks.add_task(
            cache.embed_message,
            request.app.cache,
            request.app.text_splitter,
            request.app.text_embedder,
            message)
    return

@router.get("/context/search",
    summary="Gets conversation context from memory, by vector search.",
    description=
    """
    Allows AI agents to retrieve stored context in memory by Thread ID.
    Context is secured by Thread ID to prevent cross-contamination.
    """)
async def get_context_search(
    request:Request,
    thread_id:str,
    query:str,
    top_k:int=3) -> list[cache.EmbeddedMessage]:

    embed_query = request.app.text_embedder.embed_query(query)

    query = (
        Query(f'(@thread_id:"{thread_id}")=>[KNN {top_k} @embeddings $query_vector AS vector_score]')
        .sort_by('vector_score',asc=False)
        .return_fields(
            'vector_score',
            'thread_id',
            'message_id',
            'message_num',
            'title',
            'content')
        .dialect(2)
        )

    result = await request.app.cache.ft('idx:context').search(
        query,
        {'query_vector': np.array(embed_query, dtype=np.float32).tobytes()}
        )
    return [
        cache.EmbeddedMessage(
            num=doc['message_num'],
            thread_id=doc['thread_id'],
            message_id=doc['message_id'],
            title=doc['title'],
            content=doc['content'],
            vector_score=doc['vector_score']
        ) for doc in result.docs
    ]
