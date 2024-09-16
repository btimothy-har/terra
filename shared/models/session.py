from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from .user import User


class Session(BaseModel):
    id: str
    timestamp: datetime
    user: Optional[User] = None
