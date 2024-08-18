import json
from datetime import datetime
from datetime import timezone
from uuid import uuid4

import requests
from config import API_ENDPOINT
from langchain_core.messages import ChatMessage

from shared.models.message import ThreadMessage


class AppMessage(ThreadMessage):
    @classmethod
    def from_chat_message(cls, message: ChatMessage) -> "ThreadMessage":
        return cls(
            id=str(uuid4()),
            role=message.role,
            content=message.content,
            timestamp=datetime.now(timezone.utc),
        )

    def save(self, thread_id: str, session_id: str, user_id: str) -> None:
        message_dict = self.model_dump()
        message_dict.update(
            {"thread_id": thread_id, "session_id": session_id, "user_id": user_id}
        )

        put_save = requests.put(
            url=f"{API_ENDPOINT}/messages/save",
            data=json.dumps(message_dict, default=str),
        )
        put_save.raise_for_status()

    def save_context(self, thread_id: str, context: list[dict]) -> None:
        put_context = requests.post(
            url=f"{API_ENDPOINT}/threads/context/save",
            data=json.dumps(
                {"thread_id": thread_id, "message_id": self.id, "messages": context}
            ),
        )
        put_context.raise_for_status()

    def to_chat_message(self) -> ChatMessage:
        return ChatMessage(role=self.role, content=self.content)

    def to_chat_dict(self) -> dict:
        return {
            "role": self.role,
            "content": self.content,
        }
