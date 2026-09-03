import logging
from typing import Any
from urllib.parse import quote

import httpx

from app.models import Chapter, Manga
from app.sources.base import MangaSource


API_BASE = "https://api.comick.dev/v1.0"
WEB_BASE = "https://comick.dev"

HEADERS = {
    "Accept": "application/json",
    "User-Agent": "MangaSearchTelegramBot/1.0",
}

logger = logging.getLogger(__name__)


class ComickSource(MangaSource):
    id = "comick"
    label = "🟣 Comick"

    def __init__(self) -> None:
        self._cache: dict[
            str,
            dict[str, Any],
        ] = {}

    async def get_json(self, path: str) -> Any:
        async with httpx.AsyncClient(
            headers=HEADERS,
            timeout=15,
            follow_redirects=True,
        ) as client:
            response = await client.get(
                f"{API_BASE}{path}"
            )

            response.raise_for_status()

            return response.json()

    def parse_manga(
        self,
        record: dict[str, Any],
    ) -> Manga:
        hid = str(record["hid"])

        self._cache[hid] = record

        cover_key = (
            record.get("md_covers") or [{}]
        )[0].get("b2key")

        status = {
            1: "Ongoing",
            2: "Completed",
        }.get(record.get("status"))

        last_chapter = record.get(
            "last_chapter"
        )

        try:
            chapter_count = (
                int(float(last_chapter))
                if last_chapter
                else None
            )
        except (TypeError, ValueError):
            chapter_count = None

        return Manga(
            source="comick",
            id=hid,
            title=(
                record.get("title")
                or "Untitled manga"
            ),
            description=record.get("desc"),
            status=status,
            year=record.get("year"),
            chapter_count=chapter_count,
            cover_url=(
                f"https://meo.comick.pictures/"
                f"{quote(cover_key)}"
                if cover_key
                else None
            ),
            source_url=(
                f"{WEB_BASE}/comic/"
                f"{record.get('slug', hid)}"
            ),
        )

    async def search(
        self,
        query: str,
    ) -> list[Manga]:
        response = await self.get_json(
            f"/search/?q={quote(query)}&limit=8"
        )

        return [
            self.parse_manga(record)
            for record in response
        ]

    async def get_manga(
        self,
        manga_id: str,
    ) -> Manga:
        if manga_id in self._cache:
            return self.parse_manga(
                self._cache[manga_id]
            )

        record = await self.get_json(
            f"/comic/{quote(manga_id)}"
        )

        return self.parse_manga(record)

    async def get_chapters(
        self,
        manga_id: str,
    ) -> list[Chapter]:
        manga = await self.get_manga(
            manga_id
        )

        response = await self.get_json(
            f"/comic/{quote(manga_id)}"
            "/chapters?lang=en&limit=100"
        )

        chapters = response.get(
            "chapters",
            [],
        )

        return [
            Chapter(
                id=str(
                    chapter.get("hid")
                    or (
                        f"{manga_id}-"
                        f"{chapter.get('chap')}"
                    )
                ),
                chapter=str(
                    chapter.get("chap")
                    or "Oneshot"
                ),
                title=chapter.get("title"),
                source_url=(
                    f"{manga.source_url}/chapter/"
                    f"{quote(str(chapter.get('chap') or ''))}"
                ),
            )
            for chapter in chapters
        ]
