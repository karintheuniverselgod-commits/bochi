from dataclasses import dataclass, field
from typing import Literal


SourceId = Literal["kaliscan", "comick", "mangadex"]


@dataclass(slots=True)
class Manga:
    source: SourceId
    id: str
    title: str
    source_url: str
    alternative_title: str | None = None
    description: str | None = None
    status: str | None = None
    authors: list[str] = field(default_factory=list)
    genres: list[str] = field(default_factory=list)
    year: int | None = None
    chapter_count: int | None = None
    cover_url: str | None = None


@dataclass(slots=True)
class Chapter:
    id: str
    chapter: str
    source_url: str
    title: str | None = None


@dataclass(slots=True)
class SearchSession:
    query: str
    results: list[Manga] = field(default_factory=list)
    selected_source: SourceId | None = None
    selected_id: str | None = None

    def select(self, manga: Manga) -> None:
        self.selected_source = manga.source
        self.selected_id = manga.id

    @property
    def has_selection(self) -> bool:
        return bool(self.selected_source and self.selected_id)
