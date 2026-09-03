from telegram import Update
from telegram.ext import ContextTypes

from app.keyboards import source_picker
from app.session_store import SessionStore


async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    if not update.effective_chat or not update.message:
        return

    store: SessionStore = (
        context.application.bot_data["sessions"]
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
    ) **…**

_This response is too long to display in full._
