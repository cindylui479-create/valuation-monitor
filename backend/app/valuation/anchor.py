"""SRS R12 §11.2.2 + §11.2.3：个股估值锚 & 温度公式。

5 种锚：PE / PB / PS / PE_REVERSE / DIV_YIELD
"""
from __future__ import annotations

from decimal import Decimal


ANCHOR_PE = "PE"
ANCHOR_PB = "PB"
ANCHOR_PS = "PS"
ANCHOR_PE_REVERSE = "PE_REVERSE"
ANCHOR_DIV_YIELD = "DIV_YIELD"

ALL_ANCHORS = (ANCHOR_PE, ANCHOR_PB, ANCHOR_PS, ANCHOR_PE_REVERSE, ANCHOR_DIV_YIELD)


# §11.2.2：申万一级行业 → 默认锚
INDUSTRY_TO_ANCHOR: dict[str, str] = {
    # PB 锚
    "银行": ANCHOR_PB,
    "非银金融": ANCHOR_PB,
    "房地产": ANCHOR_PB,
    # 周期股 PE 倒置
    "钢铁": ANCHOR_PE_REVERSE,
    "基础化工": ANCHOR_PE_REVERSE,
    "化工": ANCHOR_PE_REVERSE,
    "有色金属": ANCHOR_PE_REVERSE,
    "建筑材料": ANCHOR_PE_REVERSE,
    "农林牧渔": ANCHOR_PE_REVERSE,
    "煤炭": ANCHOR_PE_REVERSE,
    "石油石化": ANCHOR_PE_REVERSE,
    "采掘": ANCHOR_PE_REVERSE,
    # PS 锚（早期盈利不稳）
    "计算机": ANCHOR_PS,
    "传媒": ANCHOR_PS,
    # 股息率锚
    "公用事业": ANCHOR_DIV_YIELD,
    "交通运输": ANCHOR_DIV_YIELD,
    # 其余全部 PE
}


def default_anchor_for_industry(industry: str | None) -> str:
    """根据行业名称返回默认锚；未匹配 → PE。"""
    if not industry:
        return ANCHOR_PE
    # 容错匹配（行业名可能带"申万："前缀或多余空白）
    name = industry.strip()
    for key, anchor in INDUSTRY_TO_ANCHOR.items():
        if key in name:
            return anchor
    return ANCHOR_PE


def temperature_from_anchor(
    anchor: str,
    pe_pctl: Decimal | None,
    pb_pctl: Decimal | None,
    ps_pctl: Decimal | None,
    dy_pctl: Decimal | None,
) -> Decimal | None:
    """按锚返回温度 0–100；锚字段分位缺失则返回 None。

    公式（§11.2.3）：
      PE          → pe_pctl × 100
      PB          → pb_pctl × 100
      PS          → ps_pctl × 100
      PE_REVERSE  → (1 − pe_pctl) × 100   周期股 PE 倒置
      DIV_YIELD   → (1 − dy_pctl) × 100   股息率倒置
    """
    p: Decimal | None
    if anchor == ANCHOR_PE:
        p = pe_pctl
    elif anchor == ANCHOR_PB:
        p = pb_pctl
    elif anchor == ANCHOR_PS:
        p = ps_pctl
    elif anchor == ANCHOR_PE_REVERSE:
        p = (Decimal(1) - pe_pctl) if pe_pctl is not None else None
    elif anchor == ANCHOR_DIV_YIELD:
        p = (Decimal(1) - dy_pctl) if dy_pctl is not None else None
    else:
        return None
    if p is None:
        return None
    return p * Decimal(100)
