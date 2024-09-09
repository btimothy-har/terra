import os
from datetime import datetime

import requests


def get_latest_news(datetime: datetime):
    req = requests.get(
        url="https://api.worldnewsapi.com/search-news",
        params={
            "api-key": os.getenv("NEWS_API_KEY"),
            "language": "en",
            "earliest-publish-date": datetime.strftime("%Y-%m-%d %H:%M:%S"),
        },
    )
    req.raise_for_status()
    return req.json()
