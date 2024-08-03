from uuid import UUID

from pydantic import BaseModel

from .message import ThreadMessage


class ConversationThread(BaseModel):
    sid:UUID
    thread_id:UUID
    messages:list[ThreadMessage]

    def __iter__(self):
        return iter(self.messages)

    def message_dict(self) -> dict:
        if len(self.messages) <= 1:
            return []
        return [m.dict() for m in self.messages[1:]]
