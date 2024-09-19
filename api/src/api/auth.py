import base64
import hashlib
import os
from typing import Annotated
from typing import Any

import jwt
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.sql import select

from api.database.schemas import SessionSchema
from api.database.schemas import UserDataKeySchema
from api.database.schemas import UserKeySchema
from api.utils import database_session

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="session/authorize")


class Token(BaseModel):
    access_token: str
    token_type: str


class AuthPayload(BaseModel):
    data_key: str
    user_key: str


class NotAuthorizedError(Exception):
    pass


async def authenticate_request(token: Annotated[str, Depends(oauth2_scheme)]):
    cred_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, os.getenv("JWT_SECRET_KEY"), algorithms=["HS256"])
        enc_session_key = payload.get("session")
        enc_public_key = payload.get("key")
        if not enc_session_key or not enc_public_key:
            raise cred_exception

    except jwt.InvalidTokenError as error:
        raise cred_exception from error

    session_key = base64.b64decode(enc_session_key).decode("utf-8")
    session_id, user_id = session_key.split(":")
    public_key = base64.b64decode(enc_public_key).decode("utf-8")

    key_handler = await UserKeyHandler.load_keys(user_id)
    if not await key_handler.is_valid_session(session_id):
        raise cred_exception

    payload["data_key"] = await key_handler.get_or_create_data_key(public_key)
    payload["user_key"] = await key_handler.hashed_user_id
    return AuthPayload(**payload)


def encrypt_user_data(data_key: bytes, data: Any) -> bytes:
    f = Fernet(data_key)
    return f.encrypt(data)


def decrypt_user_data(data_key: bytes, encrypted_data: bytes) -> Any:
    try:
        f = Fernet(data_key)
        return f.decrypt(encrypted_data)
    except Exception as e:
        raise NotAuthorizedError from e


class UserKeyHandler:
    @classmethod
    async def load_keys(cls, user_id: str) -> "UserKeyHandler":
        key_handler = cls(user_id)
        await key_handler.get_public_key()
        await key_handler.get_private_key()
        return key_handler

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.public_key = None
        self.private_key = None

    @property
    def hashed_user_id(self) -> str:
        return hashlib.sha256(self.user_id.encode("utf-8")).hexdigest()

    @property
    def data_key_id(self) -> str:
        key = f"{self.hashed_user_id}:{self.public_key}"
        return base64.urlsafe_b64encode(key).decode("utf-8")

    async def is_valid_session(self, session_id: str) -> bool:
        async with database_session() as db:
            query = await db.execute(
                select(SessionSchema).filter(SessionSchema.id == session_id)
            )
            results = query.scalar_one_or_none()

        if not results:
            return False

        return True

    def create_api_token(self, session_id: str) -> Token:
        session_key = f"{session_id}:{self.user_id}"
        jwt_payload = {
            "session": base64.b64encode(session_key.encode()).decode("utf-8"),
            "key": base64.b64encode(self.public_key).decode("utf-8"),
        }
        encoded_jwt = jwt.encode(
            jwt_payload, os.getenv("JWT_SECRET_KEY"), algorithm="HS256"
        )

        return Token(access_token=encoded_jwt, token_type="bearer")

    def _private_key_encryption(self) -> Fernet:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=os.getenv("PRIVATE_KEY_SALT"),
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.user_id.encode("utf-8")))
        return Fernet(key)

    async def get_public_key(self) -> bytes:
        async with database_session() as db:
            query = await db.execute(
                select(UserKeySchema).filter(
                    UserKeySchema.id == self.hashed_user_id,
                )
            )
            results = query.scalar_one_or_none()

            if not results:
                return None

            self.public_key = results.public_key
            return results.public_key

    async def get_private_key(self) -> bytes:
        async with database_session() as db:
            query = await db.execute(
                select(UserKeySchema).filter(
                    UserKeySchema.id == self.hashed_user_id,
                )
            )
            results = query.scalar_one_or_none()

            if not results:
                return None

            self.private_key = results.private_key
            return results.private_key

    async def generate_rsa_keys(self) -> bytes:
        key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        private_key = key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        public_key = key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

        f = self._private_key_encryption()
        encrypted_private_key = f.encrypt(private_key)

        async with database_session() as db:
            stmt = pg_insert(UserKeySchema).values(
                id=self.hashed_user_id,
                public_key=public_key,
                private_key=encrypted_private_key,
            )
            stmt = stmt.on_conflict_do_nothing(index_elements=["id"])
            await db.execute(stmt)
            await db.commit()

        self.private_key = private_key
        self.public_key = public_key

        return public_key

    def encrypt_data(self, data: bytes) -> bytes:
        if not self.public_key:
            raise ValueError("Public key not found.")

        public_key = serialization.load_pem_public_key(self.public_key)
        encrypted = public_key.encrypt(
            data,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
        return encrypted

    def decrypt_data(self, data: bytes) -> bytes:
        if not self.private_key:
            raise ValueError("Private key not found.")

        f = self._private_key_encryption()
        decrypted_private_key = f.decrypt(self.private_key)

        private_key = serialization.load_pem_private_key(
            decrypted_private_key, password=None
        )

        decrypted = private_key.decrypt(
            data,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
        return decrypted

    async def get_or_create_data_key(self, public_key: bytes) -> bytes:
        if public_key != self.public_key:
            raise ValueError("Public key does not match.")

        if not self.private_key:
            raise ValueError("Private key not found.")

        async with database_session() as db:
            query = await db.execute(
                select(UserDataKeySchema).filter(
                    UserDataKeySchema.id == self.data_key_id,
                )
            )
            results = query.scalar_one_or_none()

            if results:
                data_key = self.decrypt_data(results.data_key)

            if not results:
                data_key = Fernet.generate_key()
                enc_data_key = self.encrypt_data(data_key)
                stmt = pg_insert(UserDataKeySchema).values(
                    id=self.data_key_id,
                    data_key=enc_data_key,
                )
                stmt = stmt.on_conflict_do_nothing(index_elements=["id"])
                await db.execute(stmt)
                await db.commit()

        return data_key
