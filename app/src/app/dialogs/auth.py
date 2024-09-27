import os

import google_auth_oauthlib.flow
import streamlit as st
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from models import User

SCOPES = [
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "openid",
]


@st.cache_data(ttl=3600, show_spinner=False)
def get_user_info(session_id: str, _credentials: Credentials) -> User:
    if not _credentials.valid:
        _credentials.refresh(Request())

    user_info_service = build(
        serviceName="oauth2",
        version="v2",
        credentials=_credentials,
    )
    user_info = user_info_service.userinfo().get().execute()
    user = User.create(**user_info)
    return user


@st.cache_data(ttl=60, show_spinner=False)
def get_credentials(auth_code: str) -> Credentials:
    flow = st.session_state.google_auth
    flow.fetch_token(code=auth_code)
    return flow.credentials


@st.dialog("Log In", width="small")
def auth_flow():
    if "google_auth" not in st.session_state:
        st.session_state.google_auth = (
            google_auth_oauthlib.flow.Flow.from_client_secrets_file(
                ".oauth_client.json",
                scopes=SCOPES,
                redirect_uri=os.getenv("REDIRECT_URI"),
            )
        )

    auth_code = st.query_params.get("code")
    if auth_code:
        with st.spinner("Authenticating..."):
            try:
                st.session_state.session.credentials = get_credentials(auth_code)
            except Exception as e:
                st.error(f"Authorization failed: {e}")
                auth_code = None
            else:
                st.session_state.session.save()

    if not auth_code:
        st.markdown(
            "_terra_ is a private, experimental app. "
            "Please authenticate yourself to verify identity."
        )
        st.caption(
            "Authenticating via Google will allow _terra_ to view AND "
            "collect your email address and profile information. "
            "This applies even if you are not authorized to use _terra_. "
            "Please be aware of this before proceeding."
        )

        authorization_url, _ = st.session_state.google_auth.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
        )
        st.markdown(
            f'<a href="{authorization_url}" target="_self">Login with Google</a>',
            unsafe_allow_html=True,
        )
        st.stop()

    st.rerun()
