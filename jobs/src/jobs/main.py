from datetime import UTC
from datetime import datetime
from datetime import timedelta

from scrapers.database import init_db
from scrapers.database import session
from scrapers.models import NewsItem
from scrapers.models import schema
from scrapers.news import get_latest_news
from sqlalchemy.dialects.postgresql import insert

init_db()


latest_news = get_latest_news(datetime.now(UTC) - timedelta(hours=1))

article_to_import = latest_news["news"][0]

import_item = NewsItem(
    item_id=str(article_to_import["id"]),
    title=article_to_import["title"],
    content=article_to_import["text"],
    summary=article_to_import["summary"],
    url=article_to_import["url"],
    image=article_to_import.get("image"),
    video=article_to_import.get("video"),
    publish_date=article_to_import["publish_date"],
    author=article_to_import["author"],
    authors=article_to_import.get("authors"),
    language=article_to_import.get("language"),
    category=article_to_import.get("catgory", article_to_import.get("category")),
    source_country=article_to_import.get("source_country"),
    sentiment=article_to_import.get("sentiment"),
)

stmt = insert(schema.NewsItemSchema).values(**import_item.model_dump())
stmt = stmt.on_conflict_do_nothing()
session.execute(stmt)
session.commit()
