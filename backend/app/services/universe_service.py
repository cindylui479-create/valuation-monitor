"""从 YAML 导入 Market / IndexMeta / Fund。"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Fund, IndexMeta, Market


def load_universe_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def import_universe(session: Session, data: dict[str, Any]) -> dict[str, int]:
    """对 markets / indices 进行幂等 upsert。"""
    counts = {"markets": 0, "indices": 0, "funds": 0}

    for m in data.get("markets", []):
        existing = session.scalar(select(Market).where(Market.code == m["code"]))
        if existing is None:
            session.add(
                Market(
                    code=m["code"],
                    name=m["name"],
                    currency=m["currency"],
                    tz=m["tz"],
                )
            )
            counts["markets"] += 1
    session.flush()

    market_by_code = {x.code: x for x in session.scalars(select(Market))}

    for idx in data.get("indices", []):
        market = market_by_code[idx["market"]]
        existing = session.scalar(select(IndexMeta).where(IndexMeta.code == idx["code"]))
        if existing is None:
            im = IndexMeta(
                code=idx["code"],
                name=idx["name"],
                market_id=market.id,
                category=idx["category"],
                industry_raw=idx.get("industry_raw"),
                data_source=idx["data_source"],
                history_start_date=idx["history_start_date"],
                enabled=idx.get("enabled", True),
            )
            session.add(im)
            counts["indices"] += 1
            session.flush()
            idx_id = im.id
        else:
            existing.name = idx["name"]
            existing.category = idx["category"]
            existing.industry_raw = idx.get("industry_raw")
            existing.data_source = idx["data_source"]
            existing.history_start_date = idx["history_start_date"]
            existing.enabled = idx.get("enabled", True)
            idx_id = existing.id

        for f in idx.get("funds", []) or []:
            fexisting = session.scalar(select(Fund).where(Fund.code == f["code"]))
            if fexisting is None:
                session.add(
                    Fund(
                        code=f["code"],
                        name=f["name"],
                        type=f["type"],
                        tracks_index_id=idx_id,
                        market_id=market.id,
                        fee_rate=f.get("fee_rate"),
                        tracking_error_note=f.get("tracking_error_note"),
                    )
                )
                counts["funds"] += 1

    session.commit()
    return counts
