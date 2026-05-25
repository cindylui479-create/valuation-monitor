"""SRS v1.1.0 方案 B：multpl.com 第三方指数 PE 数据源。

multpl.com 公开发布 S&P 500 等美股大盘指数的月度估值时序：
- s-p-500-pe-ratio        : PE-TTM 月度，1871 至今
- shiller-pe              : Shiller P/E (CAPE) 月度
- s-p-500-dividend-yield  : 股息率月度

每页是简单 HTML 表格，结构稳定（td 日期 + td 数值，含 &#x2002; em space 分隔）。

仅在港美股 yfinance trailingPE 是当前快照、无 PE 历史的场景下使用。
"""
from __future__ import annotations

import html as _html
import re
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Iterable

from app.utils.exceptions import FetchFailure
from app.utils.logging import get_logger

log = get_logger("adapter.multpl")

USER_AGENT = "Mozilla/5.0"


@dataclass(slots=True)
class MultplPoint:
    """multpl 单条月度估值数据。"""

    date: str       # YYYY-MM-DD
    value: Decimal  # PE-TTM / Shiller / DY
    is_estimate: bool = False


# multpl 公开的 slug → 指标名 映射
SLUG_LABEL = {
    "s-p-500-pe-ratio": "S&P 500 PE-TTM",
    "shiller-pe": "Shiller P/E (CAPE)",
    "s-p-500-dividend-yield": "S&P 500 Dividend Yield",
}


class MultplAdapter:
    """multpl.com 月度估值数据抓取适配器。

    用法：
        a = MultplAdapter()
        rows = list(a.fetch_history("s-p-500-pe-ratio"))
    """

    name = "multpl"

    def fetch_history(self, slug: str = "s-p-500-pe-ratio") -> Iterable[MultplPoint]:
        if slug not in SLUG_LABEL:
            log.warning("multpl.unknown_slug", slug=slug)
        url = f"https://www.multpl.com/{slug}/table/by-month"
        try:
            raw = self._http_get(url)
        except Exception as e:
            raise FetchFailure(f"multpl {slug}: {e}") from e

        # 1) 解 HTML entity（&#x2002; em space → 空格，否则会被当成 2002 数字误抓）
        raw = _html.unescape(raw)
        # 2) 去掉 <abbr> 标签（estimate marker），保留其后的数值
        raw = re.sub(r"<abbr[^>]*>.*?</abbr>", " ", raw, flags=re.DOTALL)

        # 表格行结构：<td>Jan 1, 2026</td><td>... 29.60 ...</td>
        pattern = r"<td>([A-Z][a-z]{2}\s+\d+,\s+\d{4})</td>\s*<td>(.*?)</td>"
        n_total = 0
        for d_str, v_block in re.findall(pattern, raw, re.DOTALL):
            # 第一个 float（容错负号）
            m = re.search(r"-?\d+\.\d+|-?\d+", v_block)
            if not m:
                continue
            try:
                dt = datetime.strptime(d_str, "%b %d, %Y").date()
            except ValueError:
                continue
            # 简单标 estimate（若原 v_block 含 †，即 abbr 已被替换 — 这里检查不出 abbr 了）
            # multpl 用 <abbr title="Estimate">† 表示，前面 re.sub 把整个 <abbr>...</abbr> 去掉了；
            # 这里不再尝试还原 is_estimate（如需要可单独 pass）
            try:
                val = Decimal(m.group())
            except Exception:
                continue
            n_total += 1
            yield MultplPoint(date=dt.isoformat(), value=val, is_estimate=False)
        log.info("multpl.fetched", slug=slug, rows=n_total)

    @staticmethod
    def _http_get(url: str, timeout: int = 15) -> str:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="ignore")

    def health_check(self) -> bool:
        try:
            urllib.request.urlopen(
                urllib.request.Request("https://www.multpl.com/", headers={"User-Agent": USER_AGENT}),
                timeout=5,
            )
            return True
        except Exception:
            return False
