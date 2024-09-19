import os

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

DEFAULT_MODEL = "google/gemini-flash-1.5"
DEFAULT_TEMP = 0.2
MAX_TOKEN_VALUES = [512, 1024, 2048, 4096]
DEFAULT_MAX_TOKENS = 2048

API_ENDPOINT = "http://api:8000"

SESSION_COOKIE = f"{os.environ.get('COOKIE_NAME')}-Session"
THREAD_COOKIE = f"{os.environ.get('COOKIE_NAME')}-Thread"


@st.cache_data(ttl=3600, show_spinner=False)
def authorization_header():
    data = {
        "username": st.session_state.session.id,
        "password": str(st.session_state.user.id),
    }

    get_token = requests.post(
        url=f"{API_ENDPOINT}/session/authorize",
        data=data,
    )
    get_token.raise_for_status()

    token_data = get_token.json()
    return {"Authorization": f"{token_data['token_type']} {token_data['access_token']}"}
