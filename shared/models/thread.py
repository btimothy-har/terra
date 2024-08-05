from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from .message import ThreadMessage


class ConversationThread(BaseModel):
    sid:str
    thread_id:str
    messages:list[ThreadMessage]
    summary:str
    last_used:Optional[datetime] = None

    def __iter__(self):
        return iter(self.messages)

    @property
    def user_messages(self) -> list[ThreadMessage]:
        return [m for m in self.messages if m.role == "user"]

    @property
    def bot_messages(self) -> list[ThreadMessage]:
        return [m for m in self.messages if m.role == "assistant"]
