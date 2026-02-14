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
        mailru_user = os.getenv("MAILRU_IMAP_USER")
        mailru_pass = os.getenv("MAILRU_IMAP_PASSWORD")
        if mailru_user and mailru_pass:
            imap_accounts.append(
                ImapAccountConfig(
                    provider="mailru",
                    host=os.getenv("MAILRU_IMAP_HOST", "imap.mail.ru"),
                    port=int(os.getenv("MAILRU_IMAP_PORT", "993")),
                    username=mailru_user,
                    password=mailru_pass,
                )
            )

        yandex_user = os.getenv("YANDEX_IMAP_USER")
        yandex_pass = os.getenv("YANDEX_IMAP_PASSWORD")
        if yandex_user and yandex_pass:
            imap_accounts.append(
                ImapAccountConfig(
                    provider="yandex",
                    host=os.getenv("YANDEX_IMAP_HOST", "imap.yandex.ru"),
                    port=int(os.getenv("YANDEX_IMAP_PORT", "993")),
                    username=yandex_user,
                    password=yandex_pass,
                )
            )

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
        )

    def ensure_directories(self) -> None:
        for path in [self.root_dir, self.data_dir, self.media_dir, self.logs_dir, self.raw_dir, self.exports_dir]:
            path.mkdir(parents=True, exist_ok=True)
        self.gmail_token_path.parent.mkdir(parents=True, exist_ok=True)
