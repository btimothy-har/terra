import json
import os

import google_auth_oauthlib.flow
import streamlit as st
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from models.credentials import SessionCredentials
from models.credentials import SessionUser

SCOPES = [
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "openid"
]

@st.cache_data(show_spinner=False)
def get_credentials(auth_code:str) -> SessionCredentials:
    credentials = SessionCredentials._find_credentials(auth_code)
    if not credentials:
        flow = st.session_state.auth_flow
        flow.fetch_token(code=auth_code)
        json_credentials = flow.credentials.to_json()
        credentials = SessionCredentials.from_authorized_user_info(json.loads(json_credentials))

    if not credentials.valid:
        credentials.refresh(Request())
    return credentials

@st.dialog("Log In to Terra",width="small")
def auth_flow():
    st.session_state.auth_flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        ".oauth_client.json",
        scopes=SCOPES,
        redirect_uri=os.getenv("REDIRECT_URI"),
    )
    auth_code = st.session_state.auth_code or st.query_params.get("code")

    if auth_code:
        with st.spinner("Authorizing..."):
            try:
                creds = get_credentials(auth_code)
            except Exception as e:
                st.error(f"Authorization failed: {e}")
                print(e)
            else:
                st.session_state.auth_code = auth_code

                user_info_service = build(
                    serviceName="oauth2",
                    version="v2",
                    credentials=creds,
                )
                user_info = user_info_service.userinfo().get().execute()
                st.session_state.session.user = SessionUser(**user_info)

                st.session_state.session.user._insert_to_database()
                st.session_state.session._insert_to_database()

                creds._save_credentials(st.session_state.session.user, auth_code)

                if st.session_state.session.user.email not in os.getenv("AUTH_USERS").split(","):
                    st.error("You have not been authorized to access Terra.")
                    st.stop()

                st.session_state.session.authorized = True
                st.rerun()

    st.markdown("Terra is a private, experimental app. Please authorize yourself to gain access.")
    st.caption("Granting access via Google will allow Terra to view AND collect your email address and \
        profile information. This applies even if you are not authorized to use Terra. \
        Please be aware of this before proceeding.")

    authorization_url, _ = st.session_state.auth_flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    st.markdown(f'<a href="{authorization_url}" target="_self">Login with Google</a>',unsafe_allow_html=True)
