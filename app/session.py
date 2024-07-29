from typing import Optional
from uuid import uuid4

from langchain_core.messages import ChatMessage
from pydantic import BaseModel


class SessionHistory:
    def __init__(self):
        self.session_id = str(uuid4())
        self.history = []

    def __iter__(self):
        return iter(self.history)

    def append(self, message:ChatMessage) -> list[ChatMessage]:
        self.history.append(message)
        return self.history

    def message_dict(self) -> dict:
        return [m.dict() for m in self.history]

class SessionUser(BaseModel):
    id: str
    email: str
    verified_email: bool
    name: str
    given_name: str
    family_name: Optional[str] = None
    hd: Optional[str] = None
