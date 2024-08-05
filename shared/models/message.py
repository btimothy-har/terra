from datetime import datetime

from pydantic import BaseModel


class ThreadMessage(BaseModel):
    id:str
    role:str
    content:str
    timestamp:datetime
