import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


def _int_env(
    name: str,
    default: int,
) -> int:
    value = os.getenv(name)

    if not value:
        return default

    try:
        return int(value)
    except ValueError as error:
        raise ValueError(
            f"{name} must be an integer, "
            f"received: {value!r}"
        ) from error


def _float_env(
    name: str,
    default: float,
) -> float:
    value = os.getenv(name)

    if not value:
        return default

    try:
        return float(value)
    except ValueError as error:
        raise ValueError(
            f"{name} must be a number, "
            f"received: {value!r}"
        ) from error


def _owner_ids() -> frozenset[int]:
    raw_value = os.getenv(
        "OWNER_IDS",
        "",
    )

    if not raw_value.strip():
        return frozenset()

    owner_ids: set[int] = set()

    for raw_id in raw_value.split(","):
        value = raw_id.strip()

        if not value:
            continue

        try:
            owner_ids.add(int(value))
        except ValueError as error:
            raise ValueError(
                "OWNER_IDS must be comma-separated "
                "Telegram numeric IDs"
            ) from error

    return frozenset(owner_ids)


@dataclass(frozen=True, slots=True)
class Settings:
    telegram_bot_token: str | None
    owner_ids: frozenset[int]
    mongodb_uri: str | None
    mongodb_database: str
    mongodb_min_pool_size: int
    mongodb_max_pool_size: int
    mongodb_server_selection_timeout_ms: int
    mongodb_connect_timeout_ms: int
    source_timeout_seconds: float
    search_result_limit: int
    chapters_per_page: int
    log_level: str

    @classmethod
    def from_environment(
        cls,
    ) -> "Settings":
        return cls(
            telegram_bot_token=os.getenv(
                "TELEGRAM_BOT_TOKEN"
            ),
            owner_ids=_owner_ids(),
            mongodb_uri=(
                os.getenv("MONGODB_URI")
                or None
            ),
            mongodb_database=os.getenv(
                "MONGODB_DATABASE",
                "manga_search_bot",
            ),
            mongodb_min_pool_size=_int_env(
                "MONGODB_MIN_POOL_SIZE",
                1,
            ),
            mongodb_max_pool_size=_int_env(
                "MONGODB_MAX_POOL_SIZE",
                10,
            ),
            mongodb_server_selection_timeout_ms=(
                _int_env(
                    "MONGODB_SERVER_SELECTION_TIMEOUT_MS",
                    5000,
                )
            ),
            mongodb_connect_timeout_ms=_int_env(
                "MONGODB_CONNECT_TIMEOUT_MS",
                5000,
            ),
            source_timeout_seconds=_float_env(
                "SOURCE_TIMEOUT_SECONDS",
                15.0,
            ),
            search_result_limit=_int_env(
                "SEARCH_RESULT_LIMIT",
                8,
            ),
            chapters_per_page=_int_env(
                "CHAPTERS_PER_PAGE",
                20,
            ),
            log_level=os.getenv(
                "LOG_LEVEL",
                "INFO",
            ).upper(),
        )

    @property
    def mongodb_enabled(self) -> bool:
        return bool(self.mongodb_uri)

    def is_owner(
        self,
        telegram_user_id: int | None,
    ) -> bool:
        return bool(
            telegram_user_id is not None
            and telegram_user_id in self.owner_ids
        )


settings = Settings.from_environment()
