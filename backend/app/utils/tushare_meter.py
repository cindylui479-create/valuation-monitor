"""SRS v1.3.0 E：Tushare API 调用计数器。

实现方式：包装 `tushare.pro_api()` 返回的 pro 对象，把它常用的 API 方法
（daily_basic / index_daily / index_dailybasic / index_weight / stock_basic / trade_cal）
都装饰成自动埋点版本。

每次调用前后：
- 增加调用计数
- 失败时记录错误信息
- 写入 `tushare_call_log` 表（按 (date, interface) upsert）

写入用独立短连接（避免污染调用方的 session）。
"""
from __future__ import annotations

import threading
from datetime import date
from typing import Callable

from app.utils.logging import get_logger
from app.utils.time_utils import now_iso

log = get_logger("tushare_meter")

# 要追踪的接口名
_TRACKED_METHODS = (
    "daily_basic",
    "index_daily",
    "index_dailybasic",
    "index_weight",
    "stock_basic",
    "trade_cal",
)

_lock = threading.Lock()


def _record_call(interface: str, ok: bool, err: str | None = None) -> None:
    """upsert 一行到 tushare_call_log：(date, interface) 唯一，increment count。

    用独立短连接避免污染上层 session。
    """
    from app.db import SessionLocal
    from app.models import TushareCallLog
    from sqlalchemy import select

    with _lock:
        try:
            with SessionLocal() as session:
                today = date.today().isoformat()
                row = session.scalar(
                    select(TushareCallLog).where(
                        TushareCallLog.call_date == today,
                        TushareCallLog.interface == interface,
                    )
                )
                if row is None:
                    row = TushareCallLog(
                        call_date=today, interface=interface,
                        n_calls=0, n_failures=0,
                        last_called_at=now_iso(),
                    )
                    session.add(row)
                    session.flush()
                row.n_calls += 1
                if not ok:
                    row.n_failures += 1
                    if err:
                        row.last_error_message = err[:255]
                row.last_called_at = now_iso()
                session.commit()
        except Exception as e:
            # 不能让计数器自己挂掉影响业务逻辑
            log.warning("tushare_meter.record_failed", error=str(e)[:200])


def wrap_pro(pro):
    """给 Tushare pro 对象的常用 API 方法套埋点装饰器。返回包装后的 pro。

    幂等：已包装过的 pro 不再重复包装。

    注意：Tushare `DataApi` 用 `__getattr__` 代理所有属性访问，所以普通的
    `getattr(pro, '_tushare_metered', False)` 会返回 `functools.partial(...)` 而非 False。
    必须用 `pro.__dict__.get(...)` 绕过代理。
    """
    if pro.__dict__.get("_tushare_metered"):
        return pro
    for method_name in _TRACKED_METHODS:
        original = getattr(pro, method_name, None)
        if not callable(original):
            continue

        def make_wrapper(orig: Callable, name: str):
            def wrapper(*args, **kwargs):
                try:
                    result = orig(*args, **kwargs)
                    _record_call(name, ok=True)
                    return result
                except Exception as e:
                    _record_call(name, ok=False, err=str(e)[:255])
                    raise
            return wrapper

        setattr(pro, method_name, make_wrapper(original, method_name))
    pro.__dict__["_tushare_metered"] = True
    return pro
