"""SRS v1.3.0 工程韧性 D：每日 SQLite 在线备份 + rolling 保留。

策略：
- 每日批处理末尾调一次 backup_to_path
- 保留近 30 天 daily 备份 + 月末归档（永久）
- 文件结构：
    data/backups/daily/valuation-2026-05-25.db    （30 天滚动）
    data/backups/monthly/valuation-2026-04.db     （月末归档，每月一次）
"""
from __future__ import annotations

import re
import sqlite3
from datetime import date
from pathlib import Path

from app.config import get_settings
from app.utils.logging import get_logger

log = get_logger("backup")

DAILY_KEEP_DAYS = 30


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def backup_dir() -> Path:
    return _project_root() / "data" / "backups"


def _backup_to(dest: Path) -> None:
    settings = get_settings()
    src = Path(settings.db_path).expanduser()
    if not src.is_absolute():
        src = _project_root() / src
    dest.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(src) as srcdb, sqlite3.connect(dest) as dstdb:
        srcdb.backup(dstdb)


def _is_last_day_of_month(d: date) -> bool:
    """判断 d 是该月最后一天。"""
    from calendar import monthrange
    return d.day == monthrange(d.year, d.month)[1]


def daily_backup() -> Path:
    """每日批处理末尾调一次。

    总是写 daily/valuation-{today}.db；若今天是月末，再写一份 monthly。
    完成后清理 30 天前的 daily 文件。
    """
    today = date.today()
    daily_dir = backup_dir() / "daily"
    daily_dest = daily_dir / f"valuation-{today.isoformat()}.db"
    _backup_to(daily_dest)
    log.info("backup.daily", dest=str(daily_dest), size_mb=round(daily_dest.stat().st_size / 1024 / 1024, 1))

    if _is_last_day_of_month(today):
        monthly_dir = backup_dir() / "monthly"
        monthly_dest = monthly_dir / f"valuation-{today.strftime('%Y-%m')}.db"
        _backup_to(monthly_dest)
        log.info("backup.monthly", dest=str(monthly_dest))

    # 清理 30 天前的 daily 文件
    cleaned = _prune_old_daily(daily_dir, today)
    if cleaned:
        log.info("backup.pruned", n=cleaned, keep_days=DAILY_KEEP_DAYS)

    return daily_dest


def _prune_old_daily(daily_dir: Path, today: date) -> int:
    """删除 daily/ 下文件名日期早于 today - 30 的备份。"""
    if not daily_dir.is_dir():
        return 0
    pat = re.compile(r"^valuation-(\d{4}-\d{2}-\d{2})\.db$")
    cutoff = today.toordinal() - DAILY_KEEP_DAYS
    deleted = 0
    for f in daily_dir.iterdir():
        m = pat.match(f.name)
        if not m:
            continue
        try:
            file_date = date.fromisoformat(m.group(1))
        except ValueError:
            continue
        if file_date.toordinal() < cutoff:
            f.unlink()
            deleted += 1
    return deleted
