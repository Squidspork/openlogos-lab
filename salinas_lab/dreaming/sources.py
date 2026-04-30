from __future__ import annotations

from pydantic import BaseModel, HttpUrl


class DreamSource(BaseModel):
    name: str
    url: HttpUrl
    topic_hint: str = ""


DEFAULT_SOURCES = [
    DreamSource.model_validate(
        {"name": "Hacker News", "url": "https://news.ycombinator.com/rss", "topic_hint": "technology"}
    ),
    DreamSource.model_validate(
        {"name": "arXiv AI", "url": "https://export.arxiv.org/rss/cs.AI", "topic_hint": "AI research"}
    ),
    DreamSource.model_validate(
        {
            "name": "MIT Technology Review",
            "url": "https://www.technologyreview.com/feed/",
            "topic_hint": "technology",
        }
    ),
]
