from __future__ import annotations

from datetime import date, datetime, timezone


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def today_iso() -> str:
    return date.today().isoformat()


def parse_iso_date(s: str) -> date:
    return date.fromisoformat(s)
