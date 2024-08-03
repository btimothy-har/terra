from datetime import datetime

from pydantic import BaseModel


class ThreadMessage(BaseModel):
    role:str
    content:str
    timestamp:datetime

    def dict(self) -> dict:
        return {
            "role": self.role,
            "content": self.content,
            }
