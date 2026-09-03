from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from app.config import Settings
from app.database import MongoDatabase
from app.keyboards import source_picker
from app.session_store import SessionStore


def services(
    context: ContextTypes.DEFAULT_TYPE,
) -> tuple[SessionStore, Settings, MongoDatabase]:
    bot_data = context.application.bot_data

    return (
        bot_data["sessions"],
        bot_data["settings"],
        bot_data["database"],
    )


async def remember_user(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    action: str,
) -> None:
    database = services(context)[2]

    await database.record_user(
        update.effective_user,
        update.effective_chat.id
        if update.effective_chat
        else None,
        action,
    )


async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    if not update.effective_chat or not update.message:
        return

    store, _, _ = services(context)

    await remember_user(
        update,
        context,
        "start",
    )

    store.start(
        update.effective_chat.id,
        "",
    )

    await update.message.reply_text(
        "🌐 Manga Search\n\n"
        "Search KaliScan, Comick, and MangaDex "
        "from one bot.\n\n"
        "Use /search <manga or manhwa name> "
        "to begin.",
        reply_markup=source_picker(),
    )


async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    if not update.message:
        return

    await remember_user(
        update,
        context,
        "help",
    )

    await update.message.reply_text(
        "Commands\n"
        "/search <title> — choose a source and search\n"
        "/start — open the source picker\n"
        "/help — show this help\n"
        "/myid — show your Telegram ID\n"
        "/admin — owner-only statistics\n\n"
        "Chapter buttons open the source website directly."
    )


async def search_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    if not update.effective_chat or not update.message:
        return

    await remember_user(
        update,
        context,
        "search",
    )

    query = " ".join(
        context.args
    ).strip()

    if not query:
        await update.message.reply_text(
            "Please add a title after /search.\n\n"
            "Example: /search Solo Leveling"
        )
        return

    store, _, _ = services(context)

    store.start(
        update.effective_chat.id,
        query,
    )

    await update.message.reply_text(
        f"🌐 Manga Search\n\n"
        f"Select a source for: {query}",
        reply_markup=source_picker(),
    )


async def my_id(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    if not update.effective_user or not update.message:
        return

    await remember_user(
        update,
        context,
        "myid",
    )

    chat_id = (
        update.effective_chat.id
        if update.effective_chat
        else "unknown"
    )

    await update.message.reply_text(
        f"Your Telegram user ID: "
        f"{update.effective_user.id}\n"
        f"Current chat ID: {chat_id}"
    )


async def admin(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    if not update.message or not update.effective_user:
        return

    await remember_user(
        update,
        context,
        "admin",
    )

    _, app_settings, database = services(context)

    if not app_settings.is_owner(
        update.effective_user.id
    ):
        await update.message.reply_text(
            "This command is available only "
            "to the bot owner."
        )
        return

    stats = await database.stats()

    database_status = (
        "connected"
        if database.enabled
        else "not configured"
    )

    await update.message.reply_text(
        "🔐 Owner dashboard\n\n"
        f"MongoDB: {database_status}\n"
        f"Registered users: {stats['users']}\n"
        f"Recorded searches: {stats['searches']}\n"
        f"Configured owners: "
        f"{len(app_settings.owner_ids)}"
    )


def register_command_handlers(
    application: Application,
) -> None:
    application.add_handler(
        CommandHandler("start", start)
    )

    application.add_handler(
        CommandHandler("help", help_command)
    )

    application.add_handler(
        CommandHandler("search", search_command)
    )

    application.add_handler(
        CommandHandler("myid", my_id)
    )

    application.add_handler(
        CommandHandler("admin", admin)
    )
