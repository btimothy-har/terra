from datetime import datetime
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel

from .message import ThreadMessage


class ConversationThread(BaseModel):
    id: str = str(uuid4())
    user_id: str
    summary: str
    last_used: Optional[datetime] = None
    messages: list[ThreadMessage]

    def __iter__(self):
        return iter(self.messages)

    @property
    def user_messages(self) -> list[ThreadMessage]:
        return [m for m in self.messages if m.role == "user"]

    @property
    def bot_messages(self) -> list[ThreadMessage]:
        return [m for m in self.messages if m.role == "assistant"]
