from datetime import datetime
from datetime import timezone

from langchain_core.messages import ChatMessage

from shared.models.message import ThreadMessage


class AppMessage(ThreadMessage):
    @classmethod
    def from_chat_message(cls, message:ChatMessage) -> "ThreadMessage":
        return cls(
            role=message.role,
            content=message.content,
            timestamp=datetime.now(timezone.utc)
            )

    def to_chat_message(self) -> ChatMessage:
        return ChatMessage(
            role=self.role,
            content=self.content
            )
