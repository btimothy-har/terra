from typing import Optional

from pydantic import BaseModel


class User(BaseModel):
    id: str
    email: str
    name: str
    given_name: str
    family_name: Optional[str]
    picture: Optional[str]
