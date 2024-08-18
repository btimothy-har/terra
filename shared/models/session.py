from datetime import datetime

from pydantic import BaseModel

from .user import User


class Session(BaseModel):
    id: str
    timestamp: datetime
    user: User
    credentials: bytes

    class Config:
        arbitrary_types_allowed = True
