from __future__ import annotations

import hashlib
import json
import mimetypes
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests

from grab.core.db import GrabRepository


class MediaManager:
    def __init__(self, repository: GrabRepository, media_root: Path):
        self.repository = repository
        self.media_root = media_root
        self.media_root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _sha256(data: bytes) -> str:
        digest = hashlib.sha256()
        digest.update(data)
        return digest.hexdigest()

    @staticmethod
    def _detect_bucket(mime: str | None, filename: str | None, source_url: str | None) -> str:
        probe = (mime or "") + " " + (filename or "") + " " + (source_url or "")
        probe_lower = probe.lower()
        if "video" in probe_lower or any(ext in probe_lower for ext in [".mp4", ".webm", ".mov", ".avi"]):
            return "videos"
        if "image" in probe_lower or any(ext in probe_lower for ext in [".jpg", ".jpeg", ".png", ".webp", ".gif"]):
            return "images"
        return "files"

    @staticmethod
    def _safe_ref(value: str | None, fallback: str) -> str:
        cleaned = (value or "").strip()
        if not cleaned:
            return fallback
        cleaned = cleaned.replace("/", "_").replace("\\", "_")
        return cleaned[:120]

    def _build_item_dir(self, store_code: str, order_ref: str | None, item_ref: str) -> Path:
        order_part = self._safe_ref(order_ref, "unknown_order")
        return self.media_root / store_code / order_part / item_ref

    def _pick_filename(self, sha256_value: str, filename: str | None, mime: str | None) -> str:
        ext = ""
        if filename:
            ext = Path(filename).suffix
        if not ext and mime:
            ext = mimetypes.guess_extension(mime) or ""
        if not ext:
            ext = ".bin"
        return f"{sha256_value[:20]}{ext}"

    def _append_meta(self, item_dir: Path, meta_entry: dict) -> None:
        meta_path = item_dir / "meta.json"
        if meta_path.exists():
            current = json.loads(meta_path.read_text(encoding="utf-8"))
            if not isinstance(current, list):
                current = [current]
        else:
            current = []
        current.append(meta_entry)
        meta_path.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")

    def save_bytes(
        self,
        *,
        store_code: str,
        order_ref: str | None,
        item_id: int,
        filename: str | None,
        content: bytes,
        mime: str | None,
        source_url: str | None,
        source: str,
    ) -> str:
        sha256_value = self._sha256(content)
        existing = self.repository.find_media_by_sha256(sha256_value)

        item_dir = self._build_item_dir(store_code, order_ref, str(item_id))
        bucket = self._detect_bucket(mime, filename, source_url)
        target_dir = item_dir / bucket
        target_dir.mkdir(parents=True, exist_ok=True)

        if existing and existing["local_path_abs"] and Path(existing["local_path_abs"]).exists():
            local_path = Path(existing["local_path_abs"]).resolve()
            size_bytes = local_path.stat().st_size
        else:
            file_name = self._pick_filename(sha256_value, filename, mime)
            local_path = (target_dir / file_name).resolve()
            local_path.write_bytes(content)
            size_bytes = len(content)

        downloaded_at = datetime.now(timezone.utc).isoformat()
        meta_entry = {
            "source": source,
            "source_url": source_url,
            "filename": filename,
            "downloaded_at": downloaded_at,
            "sha256": sha256_value,
            "mime": mime,
            "size_bytes": size_bytes,
            "local_path_abs": str(local_path),
        }
        self._append_meta(item_dir, meta_entry)

        self.repository.upsert_media(
            related_item_id=item_id,
            source_url=source_url,
            local_path_abs=str(local_path),
            mime=mime,
            sha256_value=sha256_value,
            size_bytes=size_bytes,
            source=source,
            meta_json=meta_entry,
        )
        return str(local_path)

    def download_from_url(
        self,
        *,
        store_code: str,
        order_ref: str | None,
        item_id: int,
        url: str,
        source: str,
        timeout_sec: int = 30,
        max_bytes: int = 50_000_000,
    ) -> str | None:
        response = requests.get(url, timeout=timeout_sec)
        response.raise_for_status()

        content = response.content
        if len(content) > max_bytes:
            raise ValueError(f"Слишком большой медиа-файл: {len(content)} bytes")

        parsed = urlparse(url)
        filename = Path(parsed.path).name or None
        mime = response.headers.get("Content-Type")

        return self.save_bytes(
            store_code=store_code,
            order_ref=order_ref,
            item_id=item_id,
            filename=filename,
            content=content,
            mime=mime,
            source_url=url,
            source=source,
        )
