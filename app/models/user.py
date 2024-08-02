from datetime import datetime
from datetime import timezone
from typing import Optional

from clients.postgres import get_pg_client
from pydantic import BaseModel


class SessionUser(BaseModel):
    id: str
    email: str
    name: str
    given_name: str
    family_name: Optional[str] = None
    picture: Optional[str] = None
    _timestamp = datetime.now(timezone.utc)

    def save(self):
        sql = """
            INSERT INTO
                users.googleid (uid, email, name, given_name, family_name, picture)
            VALUES
                (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (uid) DO UPDATE SET
                email = EXCLUDED.email,
                name = EXCLUDED.name,
                given_name = EXCLUDED.given_name,
                family_name = EXCLUDED.family_name,
                picture = EXCLUDED.picture;
            """

        data = (
            self.id,
            self.email,
            self.name,
            self.given_name,
            self.family_name,
            self.picture
            )

        client = get_pg_client()
        with client.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, data)
