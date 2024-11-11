import json
from datetime import datetime

import requests
from config import API_ENDPOINT

import shared.models as models


class PodcastEpisode(models.PodcastEpisode):
    @classmethod
    def search(
        cls,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        tags: list[str] | None = None,
        geos: list[str] | None = None,
    ):
        filter_data = {}
        if from_date:
            filter_data["from_date"] = from_date
        if to_date:
            filter_data["to_date"] = to_date
        if tags:
            filter_data["tags"] = tags
        if geos:
            filter_data["geos"] = geos

        post_request = requests.post(
            url=f"{API_ENDPOINT}/podcasts/filter",
            data=json.dumps(filter_data, default=str),
        )
        post_request.raise_for_status()

        return [
            PodcastEpisode.model_validate(podcast) for podcast in post_request.json()
        ]
