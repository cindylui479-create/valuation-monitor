import Decimal from "decimal.js";
export function toDecimal(s) {
    if (s == null || s === "")
        return null;
    try {
        return new Decimal(s);
    }
    catch {
        return null;
    }
}
export function formatPercent(s, digits = 1) {
    const d = toDecimal(s);
    if (d == null)
        return "—";
    return `${d.mul(100).toFixed(digits)}%`;
}
export function formatNumber(s, digits = 2) {
    const d = toDecimal(s);
    if (d == null)
        return "—";
    return d.toFixed(digits);
}
export function formatTemperature(s) {
    const d = toDecimal(s);
    if (d == null)
        return "—";
    return d.toFixed(1);
}
