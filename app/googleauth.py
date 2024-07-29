import json
import os

import google_auth_oauthlib.flow
import streamlit as st
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from session import SessionUser

load_dotenv()

SCOPES = [
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "openid"
]

@st.cache_resource
def get_credentials(auth_code:str):
    flow = st.session_state.auth_flow
    flow.fetch_token(code=auth_code)
    return flow.credentials.to_json()

@st.dialog("Log In to Terra",width="small")
def auth_flow():
    st.session_state.auth_flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        ".oauth_client.json",
        scopes=SCOPES,
        redirect_uri=os.getenv("REDIRECT_URI"),
    )
    auth_code = st.query_params.get("code")

    if auth_code:
        with st.spinner("Authorizing..."):
            try:
                cred_json = get_credentials(auth_code)
            except Exception as e:
                st.error(f"Authorization failed: {e}")
            else:
                creds = Credentials.from_authorized_user_info(json.loads(cred_json))
                creds.refresh(Request())

                user_info_service = build(
                    serviceName="oauth2",
                    version="v2",
                    credentials=creds,
                )
                user_info = user_info_service.userinfo().get().execute()
                st.session_state.auth_code = auth_code
                st.session_state.user_info = SessionUser(**user_info)

                if st.session_state.user_info.email not in os.getenv("AUTH_USERS").split(","):
                    st.error("You have not been authorized to access Terra.")
                    st.stop()
                st.rerun()

    st.markdown("Terra is a private, experimental app. Please authorize yourself to gain access.")
    authorization_url, _ = st.session_state.auth_flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
    )
    st.markdown(f'<a href="{authorization_url}" target="_self">Login with Google</a>',unsafe_allow_html=True)
