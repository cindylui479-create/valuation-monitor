"""SQLite 在线备份。

用法：
    python -m scripts.backup_db [--out data/backups]
"""
from __future__ import annotations

import argparse
import sqlite3
from datetime import date
from pathlib import Path

from app.config import get_settings


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path("data/backups"))
    args = parser.parse_args()

    settings = get_settings()
    src = Path(settings.db_path).expanduser().resolve()
    args.out.mkdir(parents=True, exist_ok=True)
    dest = args.out / f"valuation-{date.today().isoformat()}.db"

    with sqlite3.connect(src) as srcdb, sqlite3.connect(dest) as dstdb:
        srcdb.backup(dstdb)
    print(f"Backup written: {dest}")


if __name__ == "__main__":
    main()
