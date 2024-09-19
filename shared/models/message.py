from datetime import UTC
from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel
from pydantic import Field


class ThreadMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    role: str
    content: str
    timestamp: datetime = Field(default=datetime.now(UTC))
    model: str | None = None


class ContextMessage(BaseModel):
    content: str
    agent: str
