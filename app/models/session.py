import hashlib
import json
from datetime import datetime
from datetime import timezone
from typing import Optional
from uuid import uuid4

from clients.fernet import get_encryption_client
from clients.postgres import get_pg_client
from google.oauth2.credentials import Credentials
from langchain_core.messages import ChatMessage
from pydantic import BaseModel


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
    _timestamp = datetime.now(timezone.utc)

    def _insert_to_database(self) -> str:
        sql = """
            INSERT INTO
                users.googleid (id, email, verified, name, given_name, family_name, hd, picture)
            VALUES
                (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                email = EXCLUDED.email,
                verified = EXCLUDED.verified,
                name = EXCLUDED.name,
                given_name = EXCLUDED.given_name,
                family_name = EXCLUDED.family_name,
                hd = EXCLUDED.hd,
                picture = EXCLUDED.picture;
            """

        data = (
            self.id,
            self.email,
            self.verified_email,
            self.name,
            self.given_name,
            self.family_name,
            self.hd,
            self.picture
            )

        client = get_pg_client()
        with client.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, data)

class SessionCredentials(Credentials):

    @classmethod
    def _find_session(cls, auth_code:str):
        sql = f"""
            SELECT
                s.credentials
            FROM
                users.sessions s
            WHERE
                s.auth_code = '{hashlib.sha256(auth_code.encode()).hexdigest()}'
            ORDER BY
                s.timestamp DESC
            LIMIT 1;
            """
        client = get_pg_client()
        with client.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql)
                raw_json = cursor.fetchone()

        if raw_json:
            fernet = get_encryption_client()
            json_store = fernet.decrypt(raw_json[0])
            return cls.from_authorized_user_info(json.loads(json_store))
        return None

    def _save_session(self, user:SessionUser, auth_code:str):
        fernet = get_encryption_client()

        sql = """
            INSERT INTO
                users.sessions (uid, timestamp, scopes, auth_code, credentials)
            VALUES
                (%s, %s, %s, %s, %s)
            ON CONFLICT (auth_code) DO UPDATE SET
                credentials = EXCLUDED.credentials;
            """

        data = (
            user.id,
            user._timestamp,
            self.scopes,
            hashlib.sha256(auth_code.encode()).hexdigest(),
            fernet.encrypt(self.to_json().encode())
            )

        client = get_pg_client()
        with client.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, data)
