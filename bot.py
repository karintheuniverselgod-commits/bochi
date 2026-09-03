import logging
import os

from dotenv import load_dotenv
from telegram import BotCommand, Update
from telegram.ext import Application, ApplicationBuilder

from app.session_store import SessionStore
from handlers.callbacks import register_callback_handlers
from handlers.commands import register_command_handlers


def configure_logging() -> None:
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


async def post_init(application: Application) -> None:
    await application.bot.set_my_commands(
        [
            BotCommand("start", "Open the source picker"),
            BotCommand("search", "Search for a manga or manhwa"),
            BotCommand("help", "Show help"),
        ]
    )


def build_application(token: str) -> Application:
    application = (
        ApplicationBuilder()
        .token(token)
        .post_init(post_init)
        .build()
    )

    application.bot_data["sessions"] = SessionStore()

    register_command_handlers(application)
    register_callback_handlers(application)

    return application


def main() -> None:
    load_dotenv()
    configure_logging()

    token = os.getenv("TELEGRAM_BOT_TOKEN")

    if not token:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is required. "
            "Copy .env.example to .env and add your BotFather token."
        )

    application = build_application(token)

    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=False,
    )


if __name__ == "__main__":
    main()
