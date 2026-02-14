from __future__ import annotations

from pathlib import Path

import pandas as pd

from grab.core.db import GrabRepository


def export_data(repository: GrabRepository, formats: list[str], out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = repository.fetch_export_rows()
    df = pd.DataFrame(rows)

    created_files: list[Path] = []
    if "csv" in formats:
        csv_path = (out_dir / "grab_export.csv").resolve()
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        created_files.append(csv_path)

    if "xlsx" in formats:
        xlsx_path = (out_dir / "grab_export.xlsx").resolve()
        with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="items")
        created_files.append(xlsx_path)

    return created_files
