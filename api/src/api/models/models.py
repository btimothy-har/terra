from pydantic import BaseModel
from pydantic import ConfigDict

import shared.models as models
from api.auth import encrypt_user_data


class User(models.User):
    model_config = ConfigDict(from_attributes=True)


class Session(models.Session):
    model_config = ConfigDict(from_attributes=True)

    user: User


class ConversationThread(models.ConversationThread):
    def encrypt(self, key: bytes, **kwargs) -> dict:
        model_dict = self.model_dump(**kwargs)
        model_dict["summary"] = encrypt_user_data(key, model_dict["summary"])
        return model_dict


class ThreadMessage(models.ThreadMessage):
    def encrypt(self, key: bytes, **kwargs) -> dict:
        model_dict = self.model_dump(**kwargs)
        model_dict["content"] = encrypt_user_data(key, model_dict["content"])
        return model_dict


class ContextMessage(models.ContextMessage):
    model_config = ConfigDict(from_attributes=True)


class ContextChunk(BaseModel):
    timestamp: str
    agent: str
    content: str
