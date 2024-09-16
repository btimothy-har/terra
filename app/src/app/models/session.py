import json
import os
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from typing import Optional

import extra_streamlit_components as stx
import requests
from config import API_ENDPOINT

import shared.models as models

from .user import User


class Session(models.Session):
    _cookies = None

    @property
    def cookies(self) -> stx.CookieManager:
        if not self._cookies:
            self._cookies = stx.CookieManager(key=self.id)
        return self._cookies

    @property
    def authorized(self) -> bool:
        if self.user and getattr(self.user, "email", None) in os.getenv(
            "AUTH_USERS", ""
        ).split(","):
            return True
        return False

    @classmethod
    def create(cls, session_id: str):
        new_session = cls(
            id=session_id, timestamp=datetime.now(timezone.utc), user=None
        )
        new_session.set_cookie()
        return new_session

    @classmethod
    def resume(cls, session_id: str) -> Optional["Session"]:
        find_session = requests.get(url=f"{API_ENDPOINT}/users/session/{session_id}")
        find_session.raise_for_status()

        try:
            session_data = find_session.json()
        except json.JSONDecodeError:
            return None

        if session_data:
            session_data["user"] = User(**session_data["user"])
            return cls(**session_data)
        return None

    def save(self):
        put_save = requests.put(
            url=f"{API_ENDPOINT}/users/session/save",
            data=self.model_dump_json(),
        )
        put_save.raise_for_status()

    def set_cookie(self):
        self.cookies.set(
            cookie=os.getenv("COOKIE_NAME"),
            val=self.id,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
