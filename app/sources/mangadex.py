from typing import Any

import httpx

from app.models import Chapter, Manga
from app.sources.base import MangaSource


API_BASE = "https://api.mangadex.org"
WEB_BASE = "https://mangadex.org"
COVERS_BASE = "https://uploads.mangadex.org/covers"

HEADERS = {
    "Accept": "application/json",
    "User-Agent": "MangaSearchTelegramBot/1.0",
}


def localized(
    values: dict[str, str] | None,
) -> str | None:
    if not values:
        return None

    return (
        values.get("en")
        or next(iter(values.values()), None)
    )


def cover_url(
    resource: dict[str, Any],
) -> str | None:
    for relationship in resource.get("relationships", []):
        if relationship.get("type") != "cover_art":
            continue

        filename = relationship.get(
            "attributes",
            {},
        ).get("fileName")

        if filename:
            return (
                f"{COVERS_BASE}/"
                f"{resource['id']}/"
                f"{filename}.256.jpg"
            )

    return None


def parse_manga(
    resource: dict[str, Any],
) -> Manga:
    attributes = resource.get("attributes", {})

    title = (
        localized(attributes.get("title"))
        or "Untitled manga"
    )

    alternative = next(
        (
            localized(value)
            for value in attributes.get(
                "altTitles",
                [],
            )
            if localized(value)
            and localized(value) != title
        ),
        None,
    )

    return Manga(
        source="mangadex",
        id=resource["id"],
        title=title,
        alternative_title=alternative,
        description=localized(
            attributes.get("description")
        ),
        status=attributes.get("status"),
        year=attributes.get("year"),
        cover_url=cover_url(resource),
        source_url=(
            f"{WEB_BASE}/title/{resource['id']}"
        ),
    )


class MangaDexSource(MangaSource):
    id = "mangadex"
    label = "🔵 MangaDex"

    async def request(
        self,
        path: str,
        params: list[tuple[str, str]],
    ) -> Any:
        async with httpx.AsyncClient(
            headers=HEADERS,
            timeout=15,
            follow_redirects=True,
        ) as client:
            response = await client.get(
                f"{API_BASE}{path}",
                params=params,
            )

            response.raise_for_status()

            return response.json()

    async def search(
        self,
        query: str,
    ) -> list[Manga]:
        params = [
            ("title", query),
            ("limit", "8"),
            ("order[relevance]", "desc"),
            ("includes[]", "cover_art"),
            ("contentRating[]", "safe"),
            ("contentRating[]", "suggestive"),
        ]

        response = await self.request(
            "/manga",
            params,
        )

        return [
            parse_manga(resource)
            for resource in response.get("data", [])
        ]

    async def get_manga(
        self,
        manga_id: str,
    ) -> Manga:
        response = await self.request(
            f"/manga/{manga_id}",
            [("includes[]", "cover_art")],
        )

        return parse_manga(response["data"])

    async def get_chapters(
        self,
        manga_id: str,
    ) -> list[Chapter]:
        params = [
            ("limit", "100"),
            ("order[chapter]", "desc"),
            ("order[publishAt]", "desc"),
            ("manga", manga_id),
            ("translatedLanguage[]", "en"),
        ]

        response = await self.request(
            "/chapter",
            params,
        )

        return [
            Chapter(
                id=resource["id"],
                chapter=(
                    resource.get(
                        "attributes",
                        {},
                    ).get("chapter")
                    or "Oneshot"
                ),
                title=resource.get(
                    "attributes",
                    {},
                ).get("title"),
                source_url=(
                    resource.get(
                        "attributes",
                        {},
                    ).get("externalUrl")
                    or (
                        f"{WEB_BASE}/chapter/"
                        f"{resource['id']}"
                    )
                ),
            )
            for resource in response.get("data", [])
        ]
