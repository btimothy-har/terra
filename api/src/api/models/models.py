from pydantic import BaseModel
from pydantic import ConfigDict

import shared.models as models


class User(models.User):
    model_config = ConfigDict(from_attributes=True)


class Session(models.Session):
    model_config = ConfigDict(from_attributes=True)

    user: User


class ConversationThread(models.ConversationThread):
    model_config = ConfigDict(from_attributes=True)


class ThreadMessage(models.ThreadMessage):
    model_config = ConfigDict(from_attributes=True)


class ContextMessage(models.ContextMessage):
    model_config = ConfigDict(from_attributes=True)


class ContextChunk(BaseModel):
    timestamp: str
    agent: str
    content: str
