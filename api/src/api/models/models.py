from datetime import datetime
from typing import Self

from pydantic import BaseModel

import shared.models as models
from api.auth import decrypt_user_data
from api.auth import encrypt_user_data


class User(models.User):
    pass


class Session(models.Session):
    pass


class ConversationThread(models.ConversationThread):
    last_used: datetime
    messages: None = None

    def encrypt(self, key: bytes, **kwargs) -> dict:
        model_dict = self.model_dump(exclude={"messages"}, **kwargs)
        model_dict["summary"] = encrypt_user_data(key, model_dict["summary"])
        return model_dict

    @classmethod
    def decrypt(cls, schema, key: bytes) -> Self:
        model_dict = {
            "id": schema.id,
            "summary": decrypt_user_data(key, schema.summary),
            "last_used": schema.last_used,
        }
        return cls.model_validate(model_dict)


class ThreadMessage(models.ThreadMessage):
    def encrypt(self, key: bytes, **kwargs) -> dict:
        model_dict = self.model_dump(**kwargs)
        model_dict["content"] = encrypt_user_data(key, model_dict["content"])
        return model_dict

    @classmethod
    def decrypt(cls, schema, key: bytes) -> Self:
        model_dict = {
            "id": schema.id,
            "thread_id": schema.thread_id,
            "role": schema.role,
            "content": decrypt_user_data(key, schema.content),
            "timestamp": schema.timestamp,
            "model": schema.model,
        }
        return cls.model_validate(model_dict)


class ContextMessage(models.ContextMessage):
    pass


class ContextChunk(BaseModel):
    timestamp: datetime
    agent: str
    content: str
