import { Link } from "react-router-dom";
import { useState } from "react";
import type { OverviewIndex } from "@/types/api";
import { formatNumber, formatPercent, formatTemperature } from "@/utils/decimal";
import { isPriceFallback, temperatureColor, tierLabel } from "@/utils/temperature";

interface Props {
  indices: OverviewIndex[];
}

type SortKey = "name" | "tier" | "temperature" | "pe_ttm" | "pe_pct" | "pb_pct" | "dy";
type SortDir = "asc" | "desc";

const num = (s: string | null | undefined) => (s == null || s === "" ? null : parseFloat(s));

export default function TableView({ indices }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>("temperature");
  const [sortDir, setSortDir] = useState<SortDir>("asc");

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) setSortDir(sortDir === "asc" ? "desc" : "asc");
    else { setSortKey(key); setSortDir("asc"); }
  };

  const sorted = [...indices].sort((a, b) => {
    const get = (x: OverviewIndex): number | string | null => {
      switch (sortKey) {
        case "name": return x.name;
        case "tier": return x.tier ?? null;
        case "temperature": return num(x.temperature);
        case "pe_ttm": return num(x.pe_ttm);
        case "pe_pct": return num(x.pe_percentile_10y);
        case "pb_pct": return num(x.pb_percentile_10y);
        case "dy": return num(x.dividend_yield);
      }
    };
    const va = get(a); const vb = get(b);
    if (va == null && vb == null) return 0;
    if (va == null) return 1;
    if (vb == null) return -1;
    const cmp = typeof va === "number" && typeof vb === "number"
      ? va - vb
      : String(va).localeCompare(String(vb));
    return sortDir === "asc" ? cmp : -cmp;
  });

  const Arrow = ({ k }: { k: SortKey }) =>
    sortKey === k ? <span className="sort-arrow">{sortDir === "asc" ? " ▲" : " ▼"}</span> : null;

  return (
    <table className="table sortable">
      <thead>
        <tr>
          <th onClick={() => toggleSort("name")}>指数<Arrow k="name" /></th>
          <th onClick={() => toggleSort("tier")}>档位<Arrow k="tier" /></th>
          <th onClick={() => toggleSort("temperature")}>温度<Arrow k="temperature" /></th>
          <th onClick={() => toggleSort("pe_ttm")}>PE<Arrow k="pe_ttm" /></th>
          <th onClick={() => toggleSort("pe_pct")}>PE 10y%<Arrow k="pe_pct" /></th>
          <th onClick={() => toggleSort("pb_pct")}>PB 10y%<Arrow k="pb_pct" /></th>
          <th onClick={() => toggleSort("dy")}>股息率<Arrow k="dy" /></th>
        </tr>
      </thead>
      <tbody>
        {sorted.map((idx) => {
          const isSnapshot = idx.temperature == null;
          return (
            <tr key={idx.code}>
              <td>
                <Link to={`/indices/${encodeURIComponent(idx.code)}`}>
                  <div className="cell-name">{idx.name}</div>
                  <div className="cell-code">{idx.code}</div>
                </Link>
              </td>
              <td>
                <span
                  className="tier-badge"
                  style={{ backgroundColor: temperatureColor(idx.temperature) }}
                >
                  {tierLabel(idx.tier)}
                </span>
              </td>
              <td>
                {formatTemperature(idx.temperature)}
                {isPriceFallback(idx.temperature_source) && (
                  <span
                    title="价格自比（PE 历史不足时 fallback；与基金 NAV 自比同口径，不反映估值）"
                    style={{ marginLeft: 4, color: "#d97706", cursor: "help" }}
                  >⚠</span>
                )}
              </td>
              <td>
                {formatNumber(idx.pe_ttm)}
                {isSnapshot && idx.pe_ttm && (
                  <span className="pill-now" title="当前快照值，无历史分位">当前</span>
                )}
              </td>
              <td>{formatPercent(idx.pe_percentile_10y)}</td>
              <td>{formatPercent(idx.pb_percentile_10y)}</td>
              <td>{formatPercent(idx.dividend_yield, 2)}</td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
