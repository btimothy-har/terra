from typing import Optional
from uuid import uuid4

from langchain_core.messages import ChatMessage
from pydantic import BaseModel
from .postgres import get_pg_client

class SessionHistory:
    def __init__(self):
        self.session_id = str(uuid4())
        self.history = []

    def __iter__(self):
        return iter(self.history)

    def append(self, message:ChatMessage) -> list[ChatMessage]:
        self.history.append(message)
        return self.history

    def message_dict(self) -> dict:
        return [m.dict() for m in self.history]

class SessionUser(BaseModel):
    id: str
    email: str
    verified_email: bool
    name: str
    given_name: str
    family_name: Optional[str] = None
    hd: Optional[str] = None
    picture: Optional[str] = None

    def _insert_to_database(self) -> str:
        sql = f"""
            INSERT INTO \
                users.googleid (id, email, verified, name, given_name, family_name, hd, picture)
            VALUES \
                ( \
                '{self.id}', '{self.email}', '{self.verified_email}', \
                '{self.name}', '{self.given_name}', '{self.family_name}', \
                '{self.hd}', '{self.picture}' \
                )
            ON CONFLICT (id) DO UPDATE SET
                email = EXCLUDED.email,
                verified = EXCLUDED.verified,
                name = EXCLUDED.name,
                given_name = EXCLUDED.given_name,
                family_name = EXCLUDED.family_name,
                hd = EXCLUDED.hd,
                picture = EXCLUDED.picture;
            """

        client = get_pg_client()
        with client.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql)
