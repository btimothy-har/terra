from datetime import UTC
from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel


class ThreadMessage(BaseModel):
    id: str = str(uuid4())
    role: str
    content: str
    timestamp: datetime = datetime.now(UTC)
    model: str = None


class ContextMessage(BaseModel):
    id: str = str(uuid4())
    thread_id: str
    message_id: str
    content: str
    agent: str
