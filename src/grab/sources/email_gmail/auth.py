from __future__ import annotations

import json
from pathlib import Path

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


class GmailAuthManager:
    def __init__(self, client_secret_path: Path, token_path: Path):
        self.client_secret_path = client_secret_path
        self.token_path = token_path

    def ensure_credentials(self):
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow

        creds = None
        if self.token_path.exists():
            try:
                creds = Credentials.from_authorized_user_file(str(self.token_path), SCOPES)
            except Exception:  # noqa: BLE001
                # Поврежденный токен лучше пересоздать
                creds = None

        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())

        if not creds or not creds.valid:
            if not self.client_secret_path.exists():
                raise FileNotFoundError(
                    f"Не найден OAuth client secret: {self.client_secret_path}"
                )
            try:
                with self.client_secret_path.open("r", encoding="utf-8-sig") as fh:
                    client_config = json.load(fh)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    "Невалидный OAuth JSON. Пересохраните файл без BOM или скачайте заново."
                ) from exc

            flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
            creds = flow.run_local_server(port=0)

        self.token_path.parent.mkdir(parents=True, exist_ok=True)
        self.token_path.write_text(creds.to_json(), encoding="utf-8")
        return creds
