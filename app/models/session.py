from datetime import datetime
from datetime import timezone
from typing import Optional
from uuid import uuid4

from clients.postgres import get_pg_client
from models.user import SessionUser
from pydantic import BaseModel
from pydantic import Field


class UserSession(BaseModel):
    id:str = Field(default_factory=lambda: str(uuid4()))
    user:Optional[SessionUser] = Field(default=None)
    timestamp:datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    authorized:bool = Field(default=False)

    def _insert_to_database(self):
        sql = """
            INSERT INTO
                users.sessions (sid, uid, timestamp)
            VALUES
                (%s, %s, %s)
            ON CONFLICT (sid) DO NOTHING
            """

        data = (
            self.id,
            self.user.id,
            self.timestamp,
            )

        client = get_pg_client()
        with client.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, data)
