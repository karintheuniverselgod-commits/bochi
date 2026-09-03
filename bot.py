import logging

from telegram import BotCommand, Update
from telegram.ext import Application, ApplicationBuilder

from app.config import Settings, settings
from app.database import MongoDatabase
from app.session_store import SessionStore
from handlers.callbacks import (
    register_callback_handlers,
)
from handlers.commands import (
    register_command_handlers,
)


def configure_logging(
    level_name: str,
) -> None:
    level = getattr(
        logging,
        level_name.upper(),
        logging.INFO,
    )

    logging.basicConfig(
        level=level,
        format=(
            "%(asctime)s "
            "%(levelname)s "
            "%(name)s: "
            "%(message)s"
        ),
    )


async def post_init(
    application: Application,
) -> None:
    database: MongoDatabase = (
        application.bot_data["database"]
    )

    await database.connect()

    await application.bot.set_my_commands(
        [
            BotCommand(
                "start",
                "Open the source picker",
            ),
            BotCommand(
                "search",
                "Search for a manga or manhwa",
            ),
            BotCommand(
                "help",
                "Show help",
            ),
            BotCommand(
                "myid",
                "Show your Telegram user ID",
            ),
            BotCommand(
                "admin",
                "Show owner statistics",
            ),
        ]
    )


async def post_shutdown(
    application: Application,
) -> None:
    database: MongoDatabase = (
        application.bot_data["database"]
    )

    await database.close()


def build_application(
    token: str,
    app_settings: Settings,
    database: MongoDatabase,
) -> Application:
    application = (
        ApplicationBuilder()
        .token(token)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    application.bot_data["sessions"] = (
        SessionStore()
    )

    application.bot_data["settings"] = (
        app_settings
    )

    application.bot_data["database"] = (
        database
    )

    register_command_handlers(application)
    register_callback_handlers(application)

    return application


def main() -> None:
    configure_logging(settings.log_level)

    token = settings.telegram_bot_token

    if not token:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is required. "
            "Copy .env.example to .env and add "
            "your BotFather token."
        )

    database = MongoDatabase(settings)

    application = build_application(
        token,
        settings,
        database,
    )

    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=False,
    )


if __name__ == "__main__":
    main()
