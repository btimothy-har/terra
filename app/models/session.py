from datetime import datetime
from datetime import timezone, timedelta
from typing import Optional
import json
import os

from clients.postgres import get_pg_client
from models.user import SessionUser
from pydantic import BaseModel
from pydantic import Field
from google.oauth2.credentials import Credentials
from clients.fernet import get_encryption_client
import extra_streamlit_components as stx

class UserSession(BaseModel):
    id:str = Field()
    timestamp:datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    user:Optional[SessionUser] = Field(default=None)
    credentials:Optional[Credentials] = Field(default=None)

    authorized:bool = Field(default=False)
    _cookies = None

    class Config:
        arbitrary_types_allowed = True

    @property
    def cookies(self) -> stx.CookieManager:
        if not self._cookies:
            self._cookies = stx.CookieManager(key=self.id)
        return self._cookies

    def set_session(self):
        self.cookies.set(
            cookie=os.environ.get("COOKIE_NAME"),
            val=self.id,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7)
            )

    @classmethod
    def resume_session(cls, session_id):
        sql = f"""
            SELECT
                ts.uid,
                ts.timestamp,
                tu.email,
                tu.name,
                tu.given_name,
                tu.family_name,
                tu.picture,
                ta.credentials
            FROM
                users.sessions as ts
                JOIN users.googleid as tu ON ts.uid = tu.uid
                JOIN users.authentication as ta ON ts.sid = ta.sid
            WHERE
                ts.sid='{session_id}'
            ORDER BY
                ts.timestamp DESC
            LIMIT 1;
            """

        client = get_pg_client()
        with client.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql)
                raw_data = cursor.fetchone()

        if raw_data:
            fernet = get_encryption_client()
            session = cls(
                id=session_id,
                timestamp=raw_data[1],
                user=SessionUser(
                    id=raw_data[0],
                    email=raw_data[2],
                    name=raw_data[3],
                    given_name=raw_data[4],
                    family_name=raw_data[5],
                    picture=raw_data[6]
                    ),
                credentials=Credentials.from_authorized_user_info(
                    json.loads(fernet.decrypt(raw_data[7]))
                    )
                )
            return session
        return None

    def save_session(self):
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

        self._save_credentials()

    def _save_credentials(self):
        fernet = get_encryption_client()

        sql = """
            INSERT INTO
                users.authentication (uid, sid, scopes, credentials)
            VALUES
                (%s, %s, %s, %s)
            ON CONFLICT (sid) DO UPDATE SET
                credentials = EXCLUDED.credentials;
            """

        data = (
            self.user.id,
            self.id,
            self.credentials.scopes,
            fernet.encrypt(self.credentials.to_json().encode())
            )

        client = get_pg_client()
        with client.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, data)
