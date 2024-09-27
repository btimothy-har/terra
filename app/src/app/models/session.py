import base64
import json
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from typing import Optional

import extra_streamlit_components as stx
import requests
import streamlit as st
from clients.fernet import get_encryption_client
from config import API_ENDPOINT
from config import SESSION_COOKIE
from google.oauth2.credentials import Credentials

import shared.models as models


def cookie_manager(session_id: str) -> stx.CookieManager:
    return stx.CookieManager(key=session_id)


class Session(models.Session):
    @classmethod
    def create(cls, session_id: str):
        new_session = cls(
            id=session_id, timestamp=datetime.now(timezone.utc), user=None
        )
        new_session.set_cookie(SESSION_COOKIE, session_id)
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
            encrypted_credentials = base64.b64decode(session_data["credentials"])
            decrypted_credentials = fernet.decrypt(encrypted_credentials)

            session_data["credentials"] = Credentials.from_authorized_user_info(
                json.loads(decrypted_credentials)
            )
            return cls(**session_data)
        return None

    def save(self):
        copy_session = self.model_copy()

        fernet = get_encryption_client()
        encrypted_credentials = fernet.encrypt(
            copy_session.credentials.to_json().encode()
        )

        copy_session.credentials = base64.b64encode(encrypted_credentials).decode(
            "utf-8"
        )

        put_save = requests.put(
            url=f"{API_ENDPOINT}/session/save",
            data=copy_session.model_dump_json(),
        )
        put_save.raise_for_status()

    def set_cookie(
        self,
        name: str,
        val: str,
        expires_at: datetime | None = None,
    ):
        if not expires_at:
            expires_at = datetime.now(timezone.utc) + timedelta(days=90)

        if "cookie_manager" not in st.session_state:
            st.session_state.cookie_manager = cookie_manager(self.id)

        try:
            st.session_state.cookie_manager.set(
                cookie=name,
                val=val,
                expires_at=expires_at,
            )
        except Exception:
            pass
