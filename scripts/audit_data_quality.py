"""SRS R11：一次性全量数据异常审计。

扫描所有指数 10 年历史 PE/PB/CSI 字段，落到 data_anomaly 表。
用法：
    python -m scripts.audit_data_quality              # 全量扫所有指数
    python -m scripts.audit_data_quality --market A   # 仅 A 股
    python -m scripts.audit_data_quality --code 000001.SH --reset
    python -m scripts.audit_data_quality --reset      # 先清空再重扫
"""
from __future__ import annotations

import argparse
import time

from app.db import SessionLocal
from app.repositories import anomaly_repo, index_repo
from app.services import data_quality
from app.utils.logging import get_logger, setup_logging

log = get_logger("audit_dq")


def main() -> None:
    setup_logging()
    parser = argparse.ArgumentParser()
    parser.add_argument("--market", choices=["A", "HK", "US"], default=None)
    parser.add_argument("--code", default=None)
    parser.add_argument("--reset", action="store_true",
                        help="先清空目标指数的旧异常记录")
    args = parser.parse_args()

    with SessionLocal() as session:
        if args.code:
            idx = index_repo.get_by_code(session, args.code)
            indices = [idx] if idx else []
        else:
            indices = index_repo.list_indices(session, market_code=args.market)
        log.info("audit.start", indices=len(indices))

        total_new = 0
        total_refresh = 0
        for idx in indices:
            t0 = time.monotonic()
            if args.reset:
                n_del = anomaly_repo.delete_for_index(session, idx.id)
                session.commit()
            else:
                n_del = 0
            n_new, n_refresh = data_quality.detect_and_persist(
                session, idx, full_history=True
            )
            session.commit()
            total_new += n_new
            total_refresh += n_refresh
            log.info("audit.done",
                     code=idx.code, name=idx.name,
                     new=n_new, refreshed=n_refresh, deleted=n_del,
                     seconds=round(time.monotonic() - t0, 2))

        log.info("audit.summary", indices=len(indices),
                 total_new=total_new, total_refreshed=total_refresh)


if __name__ == "__main__":
    main()
