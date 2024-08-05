import json
from typing import Optional

from redis.asyncio import Redis

from shared.models.message import ThreadMessage
from shared.models.session import Session
from shared.models.thread import ConversationThread
from shared.models.user import User


##############################
##### USER CACHE         #####
##############################
async def get_user(cache:Redis, user_id:str) -> Optional[User]:
    user_data = await cache.get(f"user:{user_id}")
    if user_data:
        user_data = json.loads(user_data)
        return User(id=user_id,**user_data)
    return None

async def put_user(cache:Redis, user:User):
    await cache.set(
        name=f"user:{user.id}",
        value=user.model_dump_json(exclude={"id":True}),
        ex=3600
        )

##############################
##### SESSION CACHE      #####
##############################
async def get_session(cache:Redis, session_id:str) -> Optional[Session]:

    session_id = str(session_id)
    session_data = await cache.get(f"session:{session_id}")
    if session_data:
        session_data = json.loads(session_data)
        user_id = session_data.pop("user")["id"]
        user = await get_user(cache, user_id)
        if user:
            return Session(id=session_id, user=user, **session_data)
    return None

async def put_session(cache:Redis, session:User):
    session_model = session.model_dump_json(
        include={
            "timestamp":True,
            "credentials":True,
            "user": {"id":True}
            }
        )
    await cache.set(
        name=f"session:{str(session.id)}",
        value=session_model,
        ex=3600
        )

async def get_user_threads(cache:Redis, user_id:str) -> Optional[list[str]]:
    thread_ids = await cache.smembers(f"user:{user_id}:threads")
    if not thread_ids:
        return None

    return [tid for tid in thread_ids]

async def put_user_threads(cache:Redis, user_id:str, thread_ids:list[str]):
    await cache.sadd(f"user:{user_id}:threads", *[str(tid) for tid in thread_ids])


##############################
##### CONVERSATION CACHE #####
##############################
async def get_thread(
    cache:Redis,
    user_id:str,
    thread_id:str) -> Optional[ConversationThread]:

    thread_id = str(thread_id)

    if not await cache.sismember(f"user:{user_id}:threads", thread_id):
        return None
    thread_data = await cache.get(f"thread:{thread_id}")
    if not thread_data:
        return None

    thread = ConversationThread(
        thread_id=thread_id,
        messages=[],
        **json.loads(thread_data)
        )
    return thread

async def put_thread(cache:Redis, user_id:str, thread:ConversationThread):
    await cache.set(
        name=f"thread:{thread.thread_id}",
        value=thread.model_dump_json(exclude={"thread_id":True, "messages":True})
        )
    if await cache.exists(f"user:{user_id}:threads"):
        await put_user_threads(cache, user_id, [str(thread.thread_id)])

async def get_thread_messages(cache:Redis, thread_id:str) -> Optional[list[str]]:
    message_ids = await cache.smembers(f"thread:{thread_id}:messages")
    if not message_ids:
        return None
    return [mid for mid in message_ids]

async def put_thread_messages(cache:Redis, thread_id:str, message_ids:list[str]):
    await cache.sadd(f"thread:{thread_id}:messages", *message_ids)

async def get_message(cache:Redis, message_id:str) -> Optional[ThreadMessage]:
    message_data = await cache.get(f"message:{message_id}")
    if message_data:
        message_data = json.loads(message_data)
        return ThreadMessage(id=message_id, **message_data)
    return None

async def put_message(cache:Redis, message:ThreadMessage):
    await cache.set(
        name=f"message:{message.id}",
        value=message.model_dump_json(exclude={"id":True}),
        )
