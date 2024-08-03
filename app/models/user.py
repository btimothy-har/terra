import requests
from config import API_ENDPOINT

from shared.models.user import User


class AppUser(User):

    @classmethod
    def create(cls, **kwargs) -> "AppUser":
        return cls(
            id=kwargs['id'],
            email=kwargs['email'],
            name=kwargs['name'],
            given_name=kwargs.get('given_name', None),
            family_name=kwargs.get('family_name', None),
            picture=kwargs.get('picture', None)
            )

    def save(self):
        put_save = requests.put(
            url=f"{API_ENDPOINT}/users/save",
            data=self.model_dump_json()
            )
        put_save.raise_for_status()
