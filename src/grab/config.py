from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

DEFAULT_EMAIL_KEYWORDS = [
    "заказ",
    "чек",
    "receipt",
    "order",
    "ozon",
    "wildberries",
    "market",
    "мегамаркет",
    "dns",
    "ашан",
    "яндекс маркет",
    "aliexpress",
    "ali express",
    "алиэкспресс",
]


@dataclass(slots=True)
class ImapAccountConfig:
    provider: str
    host: str
    port: int
    username: str
    password: str
    mailbox: str = "INBOX"


@dataclass(slots=True)
class Settings:
    root_dir: Path
    data_dir: Path
    db_path: Path
    media_dir: Path
    logs_dir: Path
    raw_dir: Path
    exports_dir: Path
    gmail_client_secret_path: Path
    gmail_token_path: Path
    gmail_account: str | None
    email_keywords: list[str] = field(default_factory=lambda: DEFAULT_EMAIL_KEYWORDS.copy())
    imap_accounts: list[ImapAccountConfig] = field(default_factory=list)
    email_max_messages: int = 200
    imap_retry_attempts: int = 2
    imap_retry_delay_sec: float = 2.0
    media_timeout_sec: int = 30
    media_retries: int = 2

    @classmethod
    def load(cls, base_dir: Path | None = None) -> Settings:
        load_dotenv(override=False)

        root_env = os.getenv("GRAB_HOME")
        root_dir = Path(root_env).expanduser().resolve() if root_env else (base_dir or Path.cwd()).resolve()

        data_dir = Path(os.getenv("GRAB_DATA_DIR", root_dir / "data")).expanduser().resolve()
        db_path = Path(os.getenv("GRAB_DB_PATH", data_dir / "grab.sqlite3")).expanduser().resolve()
        media_dir = Path(os.getenv("GRAB_MEDIA_DIR", data_dir / "media")).expanduser().resolve()
        logs_dir = Path(os.getenv("GRAB_LOG_DIR", root_dir / "logs")).expanduser().resolve()
        raw_dir = Path(os.getenv("GRAB_RAW_DIR", data_dir / "raw")).expanduser().resolve()
        exports_dir = Path(os.getenv("GRAB_EXPORT_DIR", root_dir / "exports")).expanduser().resolve()

        gmail_client_secret_path = Path(
            os.getenv("GMAIL_OAUTH_CLIENT_SECRET_PATH", root_dir / "secrets" / "gmail_client_secret.json")
        ).expanduser().resolve()
        gmail_token_path = Path(
            os.getenv("GMAIL_OAUTH_TOKEN_PATH", data_dir / "auth" / "gmail_token.json")
        ).expanduser().resolve()
        gmail_account = os.getenv("GMAIL_ACCOUNT")

        keywords_env = os.getenv("GRAB_EMAIL_KEYWORDS")
        if keywords_env:
            email_keywords = [k.strip() for k in keywords_env.split(",") if k.strip()]
        else:
            email_keywords = DEFAULT_EMAIL_KEYWORDS.copy()

        imap_accounts = []
        imap_accounts.extend(
            cls._load_imap_provider_accounts(
                env_prefix="MAILRU",
                provider="mailru",
                default_host="imap.mail.ru",
                default_port=993,
            )
        )
        imap_accounts.extend(
            cls._load_imap_provider_accounts(
                env_prefix="YANDEX",
                provider="yandex",
                default_host="imap.yandex.ru",
                default_port=993,
            )
        )

        email_max_messages = int(os.getenv("GRAB_EMAIL_MAX_MESSAGES", "200"))
        imap_retry_attempts = int(os.getenv("GRAB_IMAP_RETRY_ATTEMPTS", "2"))
        imap_retry_delay_sec = float(os.getenv("GRAB_IMAP_RETRY_DELAY_SEC", "2"))
        media_timeout_sec = int(os.getenv("GRAB_MEDIA_TIMEOUT_SEC", "30"))
        media_retries = int(os.getenv("GRAB_MEDIA_RETRIES", "2"))

        return cls(
            root_dir=root_dir,
            data_dir=data_dir,
            db_path=db_path,
            media_dir=media_dir,
            logs_dir=logs_dir,
            raw_dir=raw_dir,
            exports_dir=exports_dir,
            gmail_client_secret_path=gmail_client_secret_path,
            gmail_token_path=gmail_token_path,
            gmail_account=gmail_account,
            email_keywords=email_keywords,
            imap_accounts=imap_accounts,
            email_max_messages=email_max_messages,
            imap_retry_attempts=imap_retry_attempts,
            imap_retry_delay_sec=imap_retry_delay_sec,
            media_timeout_sec=media_timeout_sec,
            media_retries=media_retries,
        )

    @staticmethod
    def _load_imap_provider_accounts(
        *,
        env_prefix: str,
        provider: str,
        default_host: str,
        default_port: int,
    ) -> list[ImapAccountConfig]:
        """
        Поддерживает несколько аккаунтов одного провайдера.
        Формат ключей:
        - базовый: PREFIX_IMAP_USER / PREFIX_IMAP_PASSWORD
        - дополнительные: PREFIX_IMAP_USER_2 / PREFIX_IMAP_PASSWORD_2 и т.д.
        """
        accounts: list[ImapAccountConfig] = []
        for index in range(1, 11):
            suffix = "" if index == 1 else f"_{index}"
            user = os.getenv(f"{env_prefix}_IMAP_USER{suffix}")
            password = os.getenv(f"{env_prefix}_IMAP_PASSWORD{suffix}")
            if not user or not password:
                continue

            host = os.getenv(
                f"{env_prefix}_IMAP_HOST{suffix}",
                os.getenv(f"{env_prefix}_IMAP_HOST", default_host),
            )
            port_raw = os.getenv(
                f"{env_prefix}_IMAP_PORT{suffix}",
                os.getenv(f"{env_prefix}_IMAP_PORT", str(default_port)),
            )
            mailbox = os.getenv(f"{env_prefix}_IMAP_MAILBOX{suffix}", "INBOX")
            accounts.append(
                ImapAccountConfig(
                    provider=provider,
                    host=host,
                    port=int(port_raw),
                    username=user,
                    password=password,
                    mailbox=mailbox,
                )
            )
        return accounts

    def ensure_directories(self) -> None:
        for path in [self.root_dir, self.data_dir, self.media_dir, self.logs_dir, self.raw_dir, self.exports_dir]:
            path.mkdir(parents=True, exist_ok=True)
        self.gmail_token_path.parent.mkdir(parents=True, exist_ok=True)
