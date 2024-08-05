from datetime import datetime
from datetime import timezone
from typing import Optional
from uuid import uuid4
import json

import requests
from clients.ai import get_client
from config import API_ENDPOINT
from langchain_core.messages import ChatMessage

from shared.models.thread import ConversationThread

from .message import AppMessage as ThreadMessage

SUMMARY_PROMPT = {
    "role":"system",
    "content": """
        You are an AI Summarization Agent.
        Given the conversation between the user and the assistant, suggest a Title that best summarizes the conversation.
        - The title should be no longer than 5 words.
        - The title should be a sentence.
    """
    }

class AppThread(ConversationThread):
    messages:list[ThreadMessage]
    summary:Optional[str]

    @classmethod
    def create(cls, session_id) -> "AppThread":
        return cls(
            sid=session_id,
            thread_id=str(uuid4()),
            messages=[],
            summary=None,
            last_used=datetime.now(timezone.utc)
            )

    @classmethod
    def get_all_for_user(cls, user_id:str) -> list[str]:
        get_thread_ids = requests.get(
            url=f"{API_ENDPOINT}/users/threads",
            params={
                "user_id": user_id
                },
            )
        try:
            get_thread_ids.raise_for_status()
            thread_ids = get_thread_ids.json()
        except requests.exceptions.HTTPError:
            return None
        except json.JSONDecodeError:
            return None

        if thread_ids:
            return thread_ids
        return None

    @classmethod
    def get_from_id(cls, thread_id:str, user_id:str) -> Optional["AppThread"]:
        get_thread_data = requests.get(
            url=f"{API_ENDPOINT}/chat/thread/id",
            params={
                "thread_id": thread_id,
                "user_id": user_id
                }
            )
        try:
            get_thread_data.raise_for_status()
            thread_data = get_thread_data.json()
        except requests.exceptions.HTTPError:
            return None
        except json.JSONDecodeError:
            return None
        else:
            return cls(
                sid=thread_data["sid"],
                thread_id=thread_data["thread_id"],
                messages=[],
                summary=thread_data["summary"],
                last_used=datetime.fromisoformat(thread_data["last_used"])
                )

    def get_messages(self) -> list[ThreadMessage]:
        get_thread_messages = requests.get(
            url=f"{API_ENDPOINT}/chat/thread/messages",
            params={
                "thread_id": self.thread_id
                }
            )
        try:
            get_thread_messages.raise_for_status()
            thread_messages = get_thread_messages.json()
        except requests.exceptions.HTTPError:
            return None
        except json.JSONDecodeError:
            return None
        else:
            msgs = [ThreadMessage(**m) for m in thread_messages]
            msgs.sort(key=lambda x: x.timestamp)
            return msgs

    def append(self, message:ChatMessage) -> ThreadMessage:
        thread_msg = ThreadMessage.from_chat_message(message)
        self.messages.append(thread_msg)
        if message.role == "user":
            self.last_used = datetime.now(timezone.utc)

        if message.role == "assistant" and len(self.user_messages) == 1:
            self.create_summary()
        return thread_msg

    def create_summary(self) -> str:
        llm = get_client(
            model="gpt-4o-mini",
            temp=0.3,
            max_tokens=512)

        sm_messages = self.message_dict()
        sm_messages.extend([SUMMARY_PROMPT])

        get_summary = llm.invoke(sm_messages)
        self.summary = get_summary.content
        return get_summary.content

    def save(self, user_id:str) -> None:
        put_save = requests.put(
            url=f"{API_ENDPOINT}/chat/thread/save",
            params={
                "user_id": user_id
                },
            data=self.model_dump_json(),
            )
        put_save.raise_for_status()

    def message_dict(self) -> list[dict]:
        if len(self.messages) <= 1:
            return []
        return [m.to_chat_dict() for m in self.messages[1:]]
