from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from .user import User


class Session(BaseModel):
    id:UUID
    timestamp:datetime
    user:User
    credentials:bytes

    class Config:
        arbitrary_types_allowed = True
