from __future__ import annotations

import platform
import sys

from grab.config import Settings
from grab.sources.email_imap import ImapEmailSource


def run_doctor_checks(settings: Settings) -> list[dict[str, str]]:
    checks: list[dict[str, str]] = []

    checks.append(
        {
            "check": "python_version",
            "status": "ok" if sys.version_info >= (3, 11) else "warn",
            "detail": platform.python_version(),
        }
    )

    checks.append(
        {
            "check": "db_parent",
            "status": "ok" if settings.db_path.parent.exists() else "warn",
            "detail": str(settings.db_path.parent),
        }
    )

    checks.append(
        {
            "check": "gmail_oauth_client_secret",
            "status": "ok" if settings.gmail_client_secret_path.exists() else "warn",
            "detail": str(settings.gmail_client_secret_path),
        }
    )

    for account in settings.imap_accounts:
        try:
            ImapEmailSource(account).check_connection()
            checks.append(
                {
                    "check": f"imap_{account.provider}",
                    "status": "ok",
                    "detail": f"{account.username}@{account.host}:{account.port}",
                }
            )
        except Exception as exc:  # noqa: BLE001
            checks.append(
                {
                    "check": f"imap_{account.provider}",
                    "status": "warn",
                    "detail": str(exc),
                }
            )

    if not settings.imap_accounts:
        checks.append(
            {
                "check": "imap_accounts",
                "status": "warn",
                "detail": "IMAP аккаунты не настроены",
            }
        )

    return checks
