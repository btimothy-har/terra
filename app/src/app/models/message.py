from datetime import datetime
from datetime import timezone

import requests
from config import API_ENDPOINT
from langchain_core.messages import ChatMessage

import shared.models as models


class ThreadMessage(models.ThreadMessage):
    @classmethod
    def from_chat_message(cls, model: str, message: ChatMessage) -> "ThreadMessage":
        return cls(
            role=message.role,
            content=message.content,
            timestamp=datetime.now(timezone.utc),
            model=model,
        )

    def save(self, thread_id: str) -> None:
        put_save = requests.put(
            url=f"{API_ENDPOINT}/threads/{thread_id}/messages/new",
            data=self.model_dump_json(),
        )
        put_save.raise_for_status()

    def save_context(self, thread_id: str, context: list[dict]):
        for message in context:
            context_message = models.ContextMessage(
                thread_id=thread_id,
                message_id=self.id,
                content=message["content"],
                agent=message["agent"],
            )
            try:
                put_context = requests.post(
                    url=f"{API_ENDPOINT}/threads/context/save",
                    data=context_message.model_dump_json(),
                )
                put_context.raise_for_status()
            except Exception as e:
                print(f"Error saving context: {e}")
                continue

    def to_chat_message(self) -> ChatMessage:
        return ChatMessage(role=self.role, content=self.content)

    def to_chat_dict(self) -> dict:
        return {
            "role": self.role,
            "content": self.content,
        }
