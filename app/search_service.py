import asyncio
import logging

from app.models import Manga, SourceId
from app.sources.base import MangaSource
from app.sources.registry import SOURCE_MAP, SOURCES


logger = logging.getLogger(__name__)


async def search_one(
    source_id: SourceId,
    query: str,
) -> list[Manga]:
    source = SOURCE_MAP[source_id]
    return await source.search(query)


async def search_all(query: str) -> list[Manga]:
    responses = await asyncio.gather(
        *(source.search(query) for source in SOURCES),
        return_exceptions=True,
    )

    results: list[Manga] = []

    for source, response in zip(SOURCES, responses):
        if isinstance(response, Exception):
            logger.warning(
                "%s search failed: %s",
                source.label,
                response,
            )
            continue

        results.extend(response)

    return results


def get_source(source_id: SourceId) -> MangaSource:
    return SOURCE_MAP[source_id]
