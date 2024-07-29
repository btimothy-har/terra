import os

import google_auth_oauthlib.flow
import streamlit as st
from googleapiclient.discovery import build
from session import SessionUser

SCOPES = [
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "openid"
    ]

def auth_flow():
    auth_code = st.query_params.get("code")
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        ".oauth_client.json",
        scopes=SCOPES,
        redirect_uri=os.getenv("REDIRECT_URI", "http://localhost:8501/"),
    )

    if auth_code:
        try:
            flow.fetch_token(code=auth_code)
        except Exception as e:
            st.error(f"Authorization failed: {e}")
            st.stop()

        user_info_service = build(
            serviceName="oauth2",
            version="v2",
            credentials=flow.credentials,
        )
        user_info = user_info_service.userinfo().get().execute()
        st.session_state.auth_code = auth_code
        st.session_state.user_info = SessionUser(**user_info)
        st.rerun()
    else:
        authorization_url, _ = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
        )
        st.page_link(authorization_url, label="Sign in with Google", icon="🌎")
