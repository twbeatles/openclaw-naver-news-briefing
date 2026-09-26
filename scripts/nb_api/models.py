from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class NewsItem:
    """Naver Search API 기사 1건의 정규화된 표현."""

    title: str
    description: str
    link: str
    original_link: str
    publisher: str
    pub_date: str
    pub_date_iso: str | None

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


__all__ = ["NewsItem"]
