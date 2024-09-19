import json
import os
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from typing import Optional

import extra_streamlit_components as stx
import requests
from clients.fernet import get_encryption_client
from config import API_ENDPOINT
from google.oauth2.credentials import Credentials

import shared.models as models


class Session(models.Session):
    _cookies = None

    @property
    def cookies(self) -> stx.CookieManager:
        if not self._cookies:
            self._cookies = stx.CookieManager(key=self.id)
        return self._cookies

    @classmethod
    def create(cls, session_id: str):
        new_session = cls(
            id=session_id, timestamp=datetime.now(timezone.utc), user=None
        )
        new_session.set_cookie()
        return new_session

    @classmethod
    def resume(cls, session_id: str) -> Optional["Session"]:
        find_session = requests.get(url=f"{API_ENDPOINT}/session/{session_id}")
        find_session.raise_for_status()

        try:
            session_data = find_session.json()
        except json.JSONDecodeError:
            return None

        if session_data:
            fernet = get_encryption_client()
            session_data["credentials"] = Credentials.from_authorized_user_info(
                json.loads(fernet.decrypt(session_data["credentials"]))
            )
            return cls(**session_data)
        return None

    def save(self):
        copy_session = self.model_copy()

        fernet = get_encryption_client()
        copy_session.credentials = fernet.encrypt(
            copy_session.credentials.to_json().encode()
        )

        put_save = requests.put(
            url=f"{API_ENDPOINT}/session/save",
            data=copy_session.model_dump_json(),
        )
        put_save.raise_for_status()

    def set_cookie(self):
        self.cookies.set(
            cookie=os.getenv("COOKIE_NAME"),
            val=self.id,
            expires_at=datetime.now(timezone.utc) + timedelta(days=90),
        )
