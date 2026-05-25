import Decimal from "decimal.js";
/** 温度 → 颜色：深绿(低估) → 灰(合理) → 深红(高估)。 */
export function temperatureColor(temperature) {
    if (temperature == null)
        return "#e5e7eb";
    let t;
    try {
        t = new Decimal(temperature).toNumber();
    }
    catch {
        return "#e5e7eb";
    }
    if (t < 10)
        return "#15803d"; // 极度低估 深绿
    if (t < 30)
        return "#22c55e"; // 低估 浅绿
    if (t < 70)
        return "#9ca3af"; // 合理 灰
    if (t < 90)
        return "#f87171"; // 高估 浅红
    return "#b91c1c"; // 极度高估 深红
}
export function tierLabel(tier) {
    return tier ?? "—";
}
/** 温度来源 → 是否为价格 fallback（与基金 NAV 自比同思路，需要 ⚠ 警示）。 */
export function isPriceFallback(source) {
    return !!source && source.startsWith("price_");
}
/** 人类可读的温度来源标签。 */
export function temperatureSourceLabel(source) {
    if (!source)
        return "";
    switch (source) {
        case "pe_10y": return "PE 10y";
        case "pe_all": return "PE 全历史";
        case "price_10y": return "价格 10y";
        case "price_all": return "价格 全历史";
        default: return source;
    }
}
