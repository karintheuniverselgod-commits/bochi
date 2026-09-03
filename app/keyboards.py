from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from app import callbacks
from app.models import Chapter, Manga
from app.sources.registry import SOURCES, source_label


CHAPTERS_PER_PAGE = 20


def source_picker() -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []

    for index in range(0, len(SOURCES), 2):
        rows.append(
            [
                InlineKeyboardButton(
                    source.label,
                    callback_data=f"{callbacks.SOURCE}:{source.id}",
                )
                for source in SOURCES[index : index + 2]
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                "🌐 Search all 3 sources",
                callback_data=f"{callbacks.SOURCE}:all",
            )
        ]
    )

    rows.append(
        [
            InlineKeyboardButton(
                "❌ Cancel search",
                callback_data=callbacks.CANCEL,
            )
        ]
    )

    return InlineKeyboardMarkup(rows)


def result_list(results: list[Manga]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []

    for index in range(0, len(results), 2):
        row: list[InlineKeyboardButton] = []

        for result_index, manga in enumerate(
            results[index : index + 2],
            start=index,
        ):
            row.append(
                InlineKeyboardButton(
                    f"{source_label(manga.source)} · {manga.title[:25]}",
                    callback_data=f"{callbacks.SELECT}:{result_index}",
                )
            )

        rows.append(row)

    rows.append(
        [
            InlineKeyboardButton(
                "↩ Choose another source",
                callback_data=f"{callbacks.BACK}:source",
            )
        ]
    )

    return InlineKeyboardMarkup(rows)


def manga_actions_with_url(manga: Manga) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "📚 Chapters",
                    callback_data=f"{callbacks.CHAPTERS}:0",
                )
            ],
            [
                InlineKeyboardButton(
                    "🔗 Open source page",
                    url=manga.source_url,
                )
            ],
            [
                InlineKeyboardButton(
                    "← Back to results",
                    callback_data=f"{callbacks.BACK}:results",
                )
            ],
        ]
    )


def chapter_list(
    chapters: list[Chapter],
    page: int,
) -> InlineKeyboardMarkup:
    page_count = max(
        1,
        (len(chapters) + CHAPTERS_PER_PAGE - 1)
        // CHAPTERS_PER_PAGE,
    )

    safe_page = max(0, min(page, page_count - 1))

    start = safe_page * CHAPTERS_PER_PAGE
    visible = chapters[start : start + CHAPTERS_PER_PAGE]

    rows: list[list[InlineKeyboardButton]] = []

    for index in range(0, len(visible), 2):
        rows.append(
            [
                InlineKeyboardButton(
                    chapter_button_text(chapter),
                    url=chapter.source_url,
                )
                for chapter in visible[index : index + 2]
            ]
        )

    navigation: list[InlineKeyboardButton] = []

    if safe_page > 0:
        navigation.append(
            InlineKeyboardButton(
                "‹ Previous",
                callback_data=f"{callbacks.CHAPTERS}:{safe_page - 1}",
            )
        )

    navigation.append(
        InlineKeyboardButton(
            f"Page {safe_page + 1} / {page_count}",
            callback_data=callbacks.NOOP,
        )
    )

    if safe_page < page_count - 1:
        navigation.append(
            InlineKeyboardButton(
                "Next ›",
                callback_data=f"{callbacks.CHAPTERS}:{safe_page + 1}",
            )
        )

    rows.append(navigation)

    rows.append(
        [
            InlineKeyboardButton(
                "← Back to manga",
                callback_data=f"{callbacks.BACK}:manga",
            )
        ]
    )

    return InlineKeyboardMarkup(rows)


def chapter_button_text(chapter: Chapter) -> str:
    suffix = (
        f" · {chapter.title[:22]}"
        if chapter.title
        else ""
    )

    return f"Ch. {chapter.chapter}{suffix}"
