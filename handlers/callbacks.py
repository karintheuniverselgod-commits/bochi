import logging

from telegram import Update
from telegram.error import TelegramError
from telegram.ext import ContextTypes

from app import callbacks
from app.database import MongoDatabase
from app.keyboards import (
    chapter_list,
    manga_actions_with_url,
    result_list,
    source_picker,
)
from app.models import Manga
from app.search_service import (
    get_source,
    search_all,
    search_one,
)
from app.session_store import SessionStore


logger = logging.getLogger(__name__)


async def callback_router(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    query = update.callback_query

    if not query or not query.message:
        return

    await query.answer()

    chat_id = query.message.chat_id

    parts = (
        query.data or ""
    ).split(":")

    action = parts[0]
    value = (
        parts[1]
        if len(parts) > 1
        else None
    )

    store: SessionStore = (
        context.application.bot_data["sessions"]
    )

    database: MongoDatabase = (
        context.application.bot_data["database"]
    )

    if update.effective_user:
        await database.record_user(
            update.effective_user,
            chat_id,
            "button",
        )

    if action == callbacks.NOOP:
        return

    if action == callbacks.CANCEL:
        store.delete(chat_id)

        await query.message.reply_text(
            "Search cancelled."
        )

        return

    if action == callbacks.SOURCE and value:
        await search_from_source(
            chat_id,
            value,
            store,
            query.message,
            database,
            update.effective_user.id
            if update.effective_user
            else None,
        )

        return

    if action == callbacks.SELECT and value:
        await select_result(
            chat_id,
            value,
            store,
            query.message,
        )

        return

    if action == callbacks.CHAPTERS:
        await show_chapters(
            chat_id,
            int_or_zero(value),
            store,
            query.message,
        )

        return

    if (
        action == callbacks.BACK
        and value == "source"
    ):
        await query.message.reply_text(
            "Select a source to search:",
            reply_markup=source_picker(),
        )

        return

    if (
        action == callbacks.BACK
        and value == "results"
    ):
        await show_results(
            chat_id,
            store,
            query.message,
        )

        return

    if (
        action == callbacks.BACK
        and value == "manga"
    ):
        await show_selected_manga(
            chat_id,
            store,
            query.message,
        )

        return


async def search_from_source(
    chat_id: int,
    source_value: str,
    store: SessionStore,
    message: object,
    database: MongoDatabase,
    user_id: int | None,
) -> None:
    session = store.get(chat_id)

    if not session or not session.query:
        await message.reply_text(
            "Your search expired. "
            "Please send /search again."
        )

        return

    search_label = (
        "all 3 sources"
        if source_value == "all"
        else source_value
    )

    await message.reply_text(
        f"🔎 Searching {search_label} "
        f"for: {session.query}"
    )

    try:
        if source_value == "all":
            session.results = await search_all(
                session.query
            )

        else:
            source_id = source_value

            if source_id not in (
                "kaliscan",
                "comick",
                "mangadex",
            ):
                raise ValueError(
                    "Unknown source"
                )

            session.results = await search_one(
                source_id,
                session.query,
            )

        if user_id is not None:
            await database.record_search(
                telegram_user_id=user_id,
                chat_id=chat_id,
                search_query=session.query,
                source=source_value,
                result_count=len(
                    session.results
                ),
            )

    except Exception as error:
        logger.warning(
            "Source search failed for %s: %s",
            source_value,
            error,
        )

        session.results = []

        await message.reply_text(
            "That source is temporarily "
            "unavailable. Try another source.",
            reply_markup=source_picker(),
        )

        return

    if not session.results:
        await message.reply_text(
            f"No results found for: "
            f"{session.query}\n\n"
            "Try another source or a shorter title.",
            reply_markup=source_picker(),
        )

        return

    await message.reply_text(
        f"📚 Results for: {session.query}\n\n"
        "Select a title to view details:",
        reply_markup=result_list(
            session.results
        ),
    )


async def select_result(
    chat_id: int,
    index_value: str,
    store: SessionStore,
    message: object,
) -> None:
    session = store.get(chat_id)

    try:
        manga = (
            session.results[
                int(index_value)
            ]
            if session
            else None
        )

    except (
        IndexError,
        ValueError,
    ):
        manga = None

    if not session or not manga:
        await message.reply_text(
            "That result expired. "
            "Please send /search again."
        )

        return

    session.select(manga)

    await show_selected_manga(
        chat_id,
        store,
        message,
    )


async def show_selected_manga(
    chat_id: int,
    store: SessionStore,
    message: object,
) -> None:
    session = store.get(chat_id)

    if not session or not session.has_selection:
        await message.reply_text(
            "Please start with "
            "/search <title>."
        )

        return

    source = get_source(
        session.selected_source
    )

    try:
        manga = await source.get_manga(
            session.selected_id or ""
        )

    except Exception as error:
        logger.warning(
            "Manga detail lookup failed: %s",
            error,
        )

        await message.reply_text(
            f"{source.label} could not load "
            "that title. Try another result "
            "or source.",
            reply_markup=result_list(
                session.results
            ),
        )

        return

    caption = manga_message(manga)
    keyboard = manga_actions_with_url(manga)

    if manga.cover_url:
        try:
            await message.reply_photo(
                photo=manga.cover_url,
                caption=caption[:1024],
                reply_markup=keyboard,
            )

            return

        except TelegramError as error:
            logger.warning(
                "Cover could not be sent: %s",
                error,
            )

    await message.reply_text(
        caption,
        reply_markup=keyboard,
    )


async def show_chapters(
    chat_id: int,
    page: int,
    store: SessionStore,
    message: object,
) -> None:
    session = store.get(chat_id)

    if not session or not session.has_selection:
        await message.reply_text(
            "Please start with "
            "/search <title>."
        )

        return

    source = get_source(
        session.selected_source
    )

    try:
        manga, chapters = (
            await gather_manga_and_chapters(
                source,
                session.selected_id or "",
            )
        )

    except Exception as error:
        logger.warning(
            "Chapter lookup failed: %s",
            error,
        )

        await message.reply_text(
            f"{source.label} could not load "
            "chapters for this title. "
            "Try another source.",
            reply_markup=result_list(
                session.results
            ),
        )

        return

    if not chapters:
        await message.reply_text(
            f"No chapter links are available "
            f"for {manga.title} on "
            f"{source.label}.",
            reply_markup=manga_actions_with_url(
                manga
            ),
        )

        return

    await message.reply_text(
        f"📚 {manga.title}\n\n"
        f"{len(chapters)} chapters found "
        f"on {source.label}.\n"
        "Select a chapter to open it on "
        "the source site.",
        reply_markup=chapter_list(
            chapters,
            page,
        ),
    )


async def gather_manga_and_chapters(
    source: object,
    manga_id: str,
) -> tuple[Manga, list]:
    import asyncio

    manga, chapters = await asyncio.gather(
        source.get_manga(manga_id),
        source.get_chapters(manga_id),
    )

    return manga, chapters


async def show_results(
    chat_id: int,
    store: SessionStore,
    message: object,
) -> None:
    session = store.get(chat_id)

    if not session or not session.results:
        await message.reply_text(
            "Your search expired. "
            "Please send /search again."
        )

        return

    await message.reply_text(
        f"📚 Results for: "
        f"{session.query}\n\n"
        "Select a title to view details:",
        reply_markup=result_list(
            session.results
        ),
    )


def manga_message(
    manga: Manga,
) -> str:
    metadata = [
        f"Source: {manga.source.title()}",
        (
            f"Also known as: "
            f"{manga.alternative_title}"
            if manga.alternative_title
            else None
        ),
        (
            f"Status: {manga.status}"
            if manga.status
            else None
        ),
        (
            f"Author: "
            f"{', '.join(manga.authors)}"
            if manga.authors
            else None
        ),
        (
            f"Genres: "
            f"{', '.join(manga.genres[:5])}"
            if manga.genres
            else None
        ),
        (
            f"Chapters listed: "
            f"{manga.chapter_count}"
            if manga.chapter_count
            else None
        ),
    ]

    description = (
        " ".join(
            manga.description.split()
        )[:650].rstrip()
        + "…"
        if manga.description
        and len(manga.description) > 650
        else manga.description
    )

    return "\n".join(
        part
        for part in [
            f"📖 {manga.title}",
            "\n".join(
                part
                for part in metadata
                if part
            ),
            description,
            (
                "Select Chapters to browse "
                "available releases."
            ),
        ]
        if part
    )


def int_or_zero(
    value: str | None,
) -> int:
    try:
        return int(value or "0")
    except ValueError:
        return 0


def register_callback_handlers(
    application: object,
) -> None:
    from telegram.ext import (
        CallbackQueryHandler,
    )

    application.add_handler(
        CallbackQueryHandler(
            callback_router
        )
    )
