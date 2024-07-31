import hashlib
import json

from clients.fernet import get_encryption_client
from clients.postgres import get_pg_client
from google.oauth2.credentials import Credentials
from models.user import SessionUser


class SessionCredentials(Credentials):

    @classmethod
    def _find_credentials(cls, auth_code:str):
        sql = f"""
            SELECT
                a.credentials
            FROM
                users.authentication a
            WHERE
                a.auth_code = '{hashlib.sha256(auth_code.encode()).hexdigest()}'
            ORDER BY
                a.timestamp DESC
            LIMIT 1;
            """
        client = get_pg_client()
        with client.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql)
                raw_json = cursor.fetchone()

        if raw_json:
            fernet = get_encryption_client()
            json_store = fernet.decrypt(raw_json[0])
            return cls.from_authorized_user_info(json.loads(json_store))
        return None

    def _save_credentials(self, user:SessionUser, auth_code:str):
        fernet = get_encryption_client()

        sql = """
            INSERT INTO
                users.authentication (uid, timestamp, scopes, auth_code, credentials)
            VALUES
                (%s, %s, %s, %s, %s)
            ON CONFLICT (auth_code) DO UPDATE SET
                credentials = EXCLUDED.credentials;
            """

        data = (
            user.id,
            user._timestamp,
            self.scopes,
            hashlib.sha256(auth_code.encode()).hexdigest(),
            fernet.encrypt(self.to_json().encode())
            )

        client = get_pg_client()
        with client.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, data)
