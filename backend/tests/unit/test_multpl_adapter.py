"""SRS v1.1.0：multpl adapter HTML 解析单测（mock 网络）。"""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import patch

from app.adapters.multpl_adapter import MultplAdapter


SAMPLE_HTML = """
<table>
<tr class="even">
<td>Jan 1, 2026</td>
<td>
<abbr title="Estimate">&dagger;</abbr>
29.60
</td>
</tr>
<tr class="odd">
<td>Dec 1, 2025</td>
<td>
&#x2002;
28.50
</td>
</tr>
<tr class="even">
<td>Jun 1, 2016</td>
<td>
&#x2002;
23.97
</td>
</tr>
</table>
"""


def test_multpl_parser_handles_em_space():
    """关键回归：&#x2002; em space 不应被误抓成 2002。"""
    a = MultplAdapter()
    with patch.object(MultplAdapter, "_http_get", return_value=SAMPLE_HTML):
        rows = list(a.fetch_history("s-p-500-pe-ratio"))

    assert len(rows) == 3
    by_date = {r.date: float(r.value) for r in rows}
    assert by_date["2026-01-01"] == 29.60
    assert by_date["2025-12-01"] == 28.50
    assert by_date["2016-06-01"] == 23.97
    # 关键：2016-06 不能是 2002
    assert by_date["2016-06-01"] != 2002.0


def test_multpl_decimal_precision():
    a = MultplAdapter()
    with patch.object(MultplAdapter, "_http_get", return_value=SAMPLE_HTML):
        rows = list(a.fetch_history("s-p-500-pe-ratio"))
    assert rows[0].value == Decimal("29.60")
