from abc import ABC, abstractmethod

from app.models import Chapter, Manga, SourceId


class MangaSource(ABC):
    id: SourceId
    label: str

    @abstractmethod
    async def search(self, query: str) -> list[Manga]:
        raise NotImplementedError

    @abstractmethod
    async def get_manga(self, manga_id: str) -> Manga:
        raise NotImplementedError

    @abstractmethod
    async def get_chapters(
        self,
        manga_id: str,
    ) -> list[Chapter]:
        raise NotImplementedError
