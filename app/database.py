from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from motor.motor_asyncio import (
    AsyncIOMotorClient,
    AsyncIOMotorDatabase,
)
from telegram import User

from app.config import Settings


logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class MongoDatabase:
    """
    Optional MongoDB persistence for users,
    searches, and future features.
    """

    def __init__(
        self,
        settings: Settings,
    ) -> None:
        self.settings = settings

        self.client: (
            AsyncIOMotorClient[Any] | None
        ) = None

        self.db: (
            AsyncIOMotorDatabase[Any] | None
        ) = None

    @property
    def enabled(self) -> bool:
        return self.db is not None

    async def connect(self) -> None:
        if not self.settings.mongodb_enabled:
            logger.info(
                "MONGODB_URI is not configured; "
                "using in-memory sessions only"
            )
            return

        self.client = AsyncIOMotorClient(
            self.settings.mongodb_uri,
            minPoolSize=(
                self.settings.mongodb_min_pool_size
            ),
            maxPoolSize=(
                self.settings.mongodb_max_pool_size
            ),
            serverSelectionTimeoutMS=(
                self.settings
                .mongodb_server_selection_timeout_ms
            ),
            connectTimeoutMS=(
                self.settings
                .mongodb_connect_timeout_ms
            ),
        )

        try:
            await self.client.admin.command(
                "ping"
            )

            self.db = self.client[
                self.settings.mongodb_database
            ]

            await self.db.users.create_index(
                "telegram_id",
                unique=True,
            )

            await self.db.searches.create_index(
                "created_at",
            )

            logger.info(
                "MongoDB connected: %s",
                self.settings.mongodb_database,
            )

        except Exception:
            await self.close()

            logger.exception(
                "MongoDB connection failed"
            )

            raise

    async def close(self) -> None:
        if self.client is not None:
            self.client.close()

        self.client = None
        self.db = None

    async def record_user(
        self,
        user: User | None,
        chat_id: int | None = None,
        last_action: str | None = None,
    ) -> None:
        if self.db is None or user is None:
            return

        now = utc_now()

        document = {
            "telegram_id": user.id,
            "is_bot": user.is_bot,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "last_chat_id": chat_id,
            "last_action": last_action,
            "last_seen_at": now,
        }

        await self.db.users.update_one(
            {"telegram_id": user.id},
            {
                "$set": document,
                "$setOnInsert": {
                    "created_at": now,
                },
            },
            upsert=True,
        )

    async def record_search(
        self,
        telegram_user_id: int,
        chat_id: int,
        search_query: str,
        source: str,
        result_count: int,
    ) -> None:
        if self.db is None:
            return

        await self.db.searches.insert_one(
            {
                "telegram_user_id": (
                    telegram_user_id
                ),
                "chat_id": chat_id,
                "query": search_query,
                "source": source,
                "result_count": result_count,
                "created_at": utc_now(),
            }
        )

    async def stats(self) -> dict[str, int]:
        if self.db is None:
            return {
                "users": 0,
                "searches": 0,
            }

        return {
            "users": await self.db.users.count_documents(
                {}
            ),
            "searches": await self.db.searches.count_documents(
                {}
            ),
        }
