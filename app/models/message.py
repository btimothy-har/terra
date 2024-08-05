from datetime import datetime
from datetime import timezone
from uuid import uuid4

import requests
from config import API_ENDPOINT
from langchain_core.messages import ChatMessage

from shared.models.message import ThreadMessage


class AppMessage(ThreadMessage):
    @classmethod
    def from_chat_message(cls, message:ChatMessage) -> "ThreadMessage":
        return cls(
            id=str(uuid4()),
            role=message.role,
            content=message.content,
            timestamp=datetime.now(timezone.utc)
            )

    def save(self, thread_id:str, session_id:str, user_id:str) -> None:
        put_save = requests.put(
            url=f"{API_ENDPOINT}/chat/message/save",
            params={
                "thread_id": thread_id,
                "session_id": session_id,
                "user_id": user_id
                },
            data=self.model_dump_json(),
            )
        put_save.raise_for_status()

    def to_chat_message(self) -> ChatMessage:
        return ChatMessage(
            role=self.role,
            content=self.content
            )

    def to_chat_dict(self) -> dict:
        return {
            "role": self.role,
            "content": self.content,
            }
