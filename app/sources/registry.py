from app.models import SourceId
from app.sources.base import MangaSource
from app.sources.comick import ComickSource
from app.sources.kaliscan import KaliScanSource
from app.sources.mangadex import MangaDexSource


SOURCES: list[MangaSource] = [
    KaliScanSource(),
    ComickSource(),
    MangaDexSource(),
]


SOURCE_MAP: dict[SourceId, MangaSource] = {
    source.id: source
    for source in SOURCES
}


def source_label(source_id: SourceId) -> str:
    return SOURCE_MAP[source_id].label
