import json

import requests
from config import API_ENDPOINT
from config import authorization_header
from langchain_core.messages import ChatMessage

import shared.models as models


class ThreadMessage(models.ThreadMessage):
    def save(self, thread_id: str):
        put_save = requests.put(
            url=f"{API_ENDPOINT}/threads/{thread_id}/messages/new",
            headers=authorization_header(),
            data=self.model_dump_json(),
        )
        put_save.raise_for_status()

    def to_chat_message(self) -> ChatMessage:
        return ChatMessage(role=self.role, content=self.content)

    def to_chat_dict(self) -> dict:
        return {
            "role": self.role,
            "content": self.content,
        }


class ContextMessage(models.ContextMessage):
    @classmethod
    def save(cls, messages: list[dict]):
        msgs = [
            ContextMessage(
                content=m["content"],
                agent=m["agent"],
            )
            for m in messages
        ]
        put_context = requests.post(
            url=f"{API_ENDPOINT}/threads/context/save",
            data=json.dumps([m.model_dump() for m in msgs]),
        )
        put_context.raise_for_status()
