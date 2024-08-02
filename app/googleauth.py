import json
import os

from datetime import timedelta

import google_auth_oauthlib.flow
import streamlit as st
import extra_streamlit_components as stx
from typing import Optional
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from models.user import SessionUser

SCOPES = [
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "openid"
]

@st.cache_data(ttl=3600,show_spinner=False)
def get_credentials(auth_code:str) -> Credentials:
    flow = st.session_state.auth_flow
    flow.fetch_token(code=auth_code)
    return flow.credentials

@st.cache_data(ttl=3600,show_spinner=False)
def get_user_info(session_id:str) -> SessionUser:
    user_info_service = build(
        serviceName="oauth2",
        version="v2",
        credentials=st.session_state.session.credentials,
    )
    user_info = user_info_service.userinfo().get().execute()
    user = SessionUser(**user_info)
    user.save()
    return user

@st.dialog("Log In",width="small")
def auth_flow():
    if "auth_flow" not in st.session_state:
        st.session_state.auth_flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
            ".oauth_client.json",
            scopes=SCOPES,
            redirect_uri=os.getenv("REDIRECT_URI"),
        )

    if not st.session_state.session.credentials:
        auth_code = st.query_params.get("code")
        if auth_code:
            with st.spinner("Authenticating..."):
                try:
                    st.session_state.session.credentials = get_credentials(auth_code)
                except Exception as e:
                    st.error(f"Authorization failed: {e}")
                    auth_code = None
                else:
                    if not st.session_state.session.credentials.valid:
                        st.session_state.session.credentials.refresh(Request())

        if not auth_code:
            st.markdown("_terra_ is a private, experimental app. Please authenticate yourself to verify identity.")
            st.caption("Authenticating via Google will allow _terra_ to view AND collect your email address and \
                profile information. This applies even if you are not authorized to use _terra_. \
                Please be aware of this before proceeding.")
            st.caption("Session cookies are stored on your browser for 7 days.")

            authorization_url, _ = st.session_state.auth_flow.authorization_url(
                access_type="offline",
                include_granted_scopes="true",
                prompt="consent",
            )
            st.markdown(f'<a href="{authorization_url}" target="_self">Login with Google</a>',unsafe_allow_html=True)
            st.stop()

    st.session_state.session.user = get_user_info(st.session_state.session.id)
    st.session_state.session.save_session()

    if st.session_state.session.user.email not in os.getenv("AUTH_USERS").split(","):
        st.error("You are not authorized to access _terra_.")
        st.stop()

    st.session_state.session.authorized = True
    st.rerun()
