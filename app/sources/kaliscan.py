import re
from urllib.parse import quote, urljoin

import httpx
from bs4 import BeautifulSoup

from app.models import Chapter, Manga
from app.sources.base import MangaSource


BASE_URL = "https://kaliscan.io"

HEADERS = {
    "Accept": "text/html,application/xhtml+xml",
    "User-Agent": "MangaSearchTelegramBot/1.0",
}


def text(value: str | None) -> str | None:
    if not value:
        return None

    return " ".join(
        BeautifulSoup(
            value,
            "html.parser",
        ).stripped_strings
    ).strip()


class KaliScanSource(MangaSource):
    id = "kaliscan"
    label = "🟢 KaliScan"

    async def get_html(self, path: str) -> str:
        async with httpx.AsyncClient(
            headers=HEADERS,
            timeout=15,
            follow_redirects=True,
        ) as client:
            response = await client.get(
                urljoin(BASE_URL, path)
            )

            response.raise_for_status()

            return response.text

    async def search(
        self,
        query: str,
    ) -> list[Manga]:
        html = await self.get_html(
            f"/search?q={quote(query)}"
        )

        soup = BeautifulSoup(
            html,
            "html.parser",
        )

        results: list[Manga] = []
        seen: set[str] = set()

        for anchor in soup.select(
            'a[href^="/manga/"][title]'
        ):
            href = anchor.get("href")
            title = anchor.get("title")
            image = anchor.select_one("img")

            if (
                not href
                or not title
                or href in seen
                or not image
            ):
                continue

            seen.add(href)

            results.append(
                Manga(
                    source="kaliscan",
                    id=href.removeprefix(
                        "/manga/"
                    ),
                    title=title,
                    cover_url=(
                        image.get("data-src")
                        or image.get("src")
                    ),
                    source_url=urljoin(
                        BASE_URL,
                        href,
                    ),
                )
            )

            if len(results) == 8:
                break

        return results

    async def get_manga(
        self,
        manga_id: str,
    ) -> Manga:
        html = await self.get_html(
            f"/manga/{manga_id}"
        )

        soup = BeautifulSoup(
            html,
            "html.parser",
        )

        title_node = (
            soup.select_one(".name.box h1")
            or soup.select_one("h1")
        )

        title = text(
            title_node.get_text()
            if title_node
            else None
        ) or manga_id

        image = soup.select_one(
            ".img-cover img"
        )

        status = self.value_after_label(
            soup,
            "Status",
        )

        authors = self.values_after_label(
            soup,
            "Authors",
        )

        genres = self.genre_values(soup)

        chapter_count = self.number_after_label(
            soup,
            "Chapters",
        )

        description_meta = soup.select_one(
            'meta[name="description"]'
        )

        return Manga(
            source="kaliscan",
            id=manga_id,
            title=title,
            cover_url=(
                image.get("data-src")
                or image.get("src")
                if image
                else None
            ),
            status=status,
            authors=authors,
            genres=genres,
            chapter_count=chapter_count,
            description=(
                description_meta.get("content")
                if description_meta
                else None
            ),
            source_url=urljoin(
                BASE_URL,
                f"/manga/{manga_id}",
            ),
        )

    async def get_chapters(
        self,
        manga_id: str,
    ) -> list[Chapter]:
        html = await self.get_html(
            f"/manga/{manga_id}"
        )

        soup = BeautifulSoup(
            html,
            "html.parser",
        )

        chapters: list[Chapter] = []
        seen: set[str] = set()

        for anchor in soup.select(
            'a[href*="/chapter-"]'
        ):
            href = anchor.get("href")

            title_node = anchor.select_one(
                ".chapter-title"
            )

            title = (
                text(str(title_node))
                if title_node
                else text(anchor.get_text())
            )

            if (
                not href
                or href in seen
                or not title
            ):
                continue

            seen.add(href)

            number = re.sub(
                r"^.*?chapter\s*",
                "",
                title,
                flags=re.I,
            ).split(" - ")[0]

            chapters.append(
                Chapter(
                    id=href,
                    chapter=number or "Oneshot",
                    title=title,
                    source_url=urljoin(
                        BASE_URL,
                        href,
                    ),
                )
            )

        return chapters

    @staticmethod
    def value_after_label(
        soup: BeautifulSoup,
        label: str,
    ) -> str | None:
        for paragraph in soup.select(".meta p"):
            paragraph_text = paragraph.get_text(
                " ",
                strip=True,
            ).lower()

            if label.lower() in paragraph_text:
                spans = paragraph.select("span")

                if spans:
                    return text(
                        spans[-1].get_text()
                    )

        return None

    @staticmethod
    def values_after_label(
        soup: BeautifulSoup,
        label: str,
    ) -> list[str]:
        for paragraph in soup.select(".meta p"):
            paragraph_text = paragraph.get_text(
                " ",
                strip=True,
            ).lower()

            if label.lower() in paragraph_text:
                return [
                    value
                    for value in (
                        text(span.get_text())
                        for span in paragraph.select(
                            "span"
                        )
                    )
                    if value
                ]

        return []

    @staticmethod
    def genre_values(
        soup: BeautifulSoup,
    ) -> list[str]:
        for paragraph in soup.select(".meta p"):
            paragraph_text = paragraph.get_text(
                " ",
                strip=True,
            ).lower()

            if "genres" in paragraph_text:
                return [
                    value.rstrip(" ,")
                    for value in (
                        text(anchor.get_text())
                        for anchor in paragraph.select(
                            "a"
                        )
                    )
                    if value
                ]

        return []

    @staticmethod
    def number_after_label(
        soup: BeautifulSoup,
        label: str,
    ) -> int | None:
        value = KaliScanSource.value_after_label(
            soup,
            label,
        )

        if not value:
            return None

        match = re.search(r"\d+", value)

        return int(match.group()) if match else None
