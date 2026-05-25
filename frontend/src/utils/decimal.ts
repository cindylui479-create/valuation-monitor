import Decimal from "decimal.js";

export function toDecimal(s: string | null | undefined): Decimal | null {
  if (s == null || s === "") return null;
  try {
    return new Decimal(s);
  } catch {
    return null;
  }
}

export function formatPercent(s: string | null | undefined, digits = 1): string {
  const d = toDecimal(s);
  if (d == null) return "—";
  return `${d.mul(100).toFixed(digits)}%`;
}

export function formatNumber(s: string | null | undefined, digits = 2): string {
  const d = toDecimal(s);
  if (d == null) return "—";
  return d.toFixed(digits);
}

export function formatTemperature(s: string | null | undefined): string {
  const d = toDecimal(s);
  if (d == null) return "—";
  return d.toFixed(1);
}
