import json
from datetime import datetime
from datetime import timezone
from typing import Optional

import requests
from clients.ai import OpenRouterModels
from clients.ai import get_client
from config import API_ENDPOINT

import shared.models as models

from .message import ThreadMessage

SUMMARY_PROMPT = {
    "role": "system",
    "content": """
        You are an AI Summarization Agent.
        Given the conversation between the user and the assistant, \
suggest a Title that best summarizes the conversation.
        - The title should be no longer than 5 words.
        - The title should be a phrase.
        - The title should only contain alphanumeric characters with NO punctuation \
or symbols.
    """,
}


class ConversationThread(models.ConversationThread):
    messages: list[ThreadMessage]
    summary: Optional[str]

    @classmethod
    def create(cls, user_id: str) -> "ConversationThread":
        return cls(
            user_id=user_id,
            summary=None,
            last_used=datetime.now(timezone.utc),
            messages=[],
        )

    @classmethod
    def get_all_for_user(cls, user_id: str) -> list[str] | None:
        get_thread_ids = requests.get(url=f"{API_ENDPOINT}/users/{user_id}/threads")
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
    def get_from_id(cls, thread_id: str) -> Optional["ConversationThread"]:
        get_thread_data = requests.get(url=f"{API_ENDPOINT}/threads/{thread_id}")
        try:
            get_thread_data.raise_for_status()
            thread_data = get_thread_data.json()
        except requests.exceptions.HTTPError:
            return None
        except json.JSONDecodeError:
            return None
        else:
            return (
                None
                if not thread_data
                else cls(
                    id=thread_data["id"],
                    user_id=thread_data["user_id"],
                    summary=thread_data["summary"],
                    last_used=datetime.fromisoformat(thread_data["last_used"]),
                    messages=[],
                )
            )

    def get_messages(self) -> list[ThreadMessage]:
        get_thread_messages = requests.get(
            url=f"{API_ENDPOINT}/threads/{self.id}/messages",
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
            self.messages = msgs
            return msgs

    def delete(self):
        put_del_thread = requests.put(
            url=f"{API_ENDPOINT}/threads/{self.id}/delete",
        )
        try:
            put_del_thread.raise_for_status()
        except requests.exceptions.HTTPError:
            return None
        except json.JSONDecodeError:
            return None

    def append(self, message: ThreadMessage):
        self.messages.append(message)
        if message.role == "user":
            self.last_used = message.timestamp

        if message.role == "assistant" and len(self.user_messages) == 1:
            self.create_summary()

        self.save()
        message.save(self.thread_id)

    def create_summary(self) -> str:
        llm = get_client(model=OpenRouterModels.OPENAI_GPT4O_MINI.value, temp=0.3)

        sm_messages = self.message_dict()
        sm_messages.extend([SUMMARY_PROMPT])

        get_summary = llm.invoke(sm_messages)
        self.summary = get_summary.content
        return get_summary.content

    def save(self) -> None:
        put_save = requests.put(
            url=f"{API_ENDPOINT}/threads/save",
            data=self.model_dump_json(),
        )
        put_save.raise_for_status()

    def message_dict(self) -> list[dict]:
        if len(self.messages) <= 1:
            return []
        return [m.to_chat_dict() for m in self.messages[1:]]
