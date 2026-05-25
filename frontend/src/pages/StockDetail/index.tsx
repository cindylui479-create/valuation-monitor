import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import {
  fetchStockDetail,
  updateStockAnchor,
} from "@/api/stocks";
import { temperatureColor, tierLabel } from "@/utils/temperature";
import PriceValuationChart from "@/pages/IndexDetail/PriceValuationChart";

const ANCHOR_LABEL: Record<string, string> = {
  PE: "PE-TTM",
  PB: "市净率 (PB)",
  PS: "市销率 (PS)",
  PE_REVERSE: "PE 倒置（周期股）",
  DIV_YIELD: "股息率倒置",
};

const ANCHOR_HINT: Record<string, string> = {
  PE: "高 PE 百分位 = 高估值",
  PB: "高 PB 百分位 = 高估值（适用于银行/地产）",
  PS: "高 PS 百分位 = 高估值（适用于互联网/早期科技）",
  PE_REVERSE: "PE 低 = 周期顶部 = 高估；适用于钢铁/煤炭/化工等",
  DIV_YIELD: "股息率低 = 高估；适用于公用事业/交通运输",
};

export default function StockDetail() {
  const { code = "" } = useParams<{ code: string }>();
  const qc = useQueryClient();

  const { data, isLoading, error } = useQuery({
    queryKey: ["stock-detail", code],
    queryFn: () => fetchStockDetail(code),
    enabled: !!code,
  });

  const anchorMut = useMutation({
    mutationFn: (anchor: string) => updateStockAnchor(code, anchor),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["stock-detail", code] });
      qc.invalidateQueries({ queryKey: ["stocks"] });
    },
  });

  if (isLoading) return <div className="state">加载中…</div>;
  if (error) return <div className="state error">加载失败：{(error as Error).message}</div>;
  if (!data) return null;

  const v = data.latest_valuation;
  const latestQuote = data.quotes[data.quotes.length - 1];

  return (
    <div className="detail">
      <header className="detail-header">
        <div>
          <Link to="/watchlist" className="back-link">← 自选</Link>
          <h1>
            {data.name}
            <span className="code">{data.code}</span>
          </h1>
          <p className="meta">
            A 股 · CNY · 个股
            {data.industry && <> · {data.industry}</>}
            {data.listing_date && <> · 上市 {data.listing_date}</>}
            {data.data_window_note && (
              <span className="window-note"> · {data.data_window_note}</span>
            )}
          </p>
        </div>
      </header>

      <section className="latest-card">
        {v?.temperature && (
          <div
            className="tier-pill"
            style={{ backgroundColor: temperatureColor(v.temperature) }}
          >
            {v.tier ? tierLabel(v.tier) : "—"}
          </div>
        )}
        <div className="stat">
          <div className="label">温度（{ANCHOR_LABEL[data.anchor] ?? data.anchor} 锚）</div>
          <div className="value">
            {v?.temperature ? parseFloat(v.temperature).toFixed(1) : "—"}
          </div>
        </div>
        <div className="stat">
          <div className="label">PE-TTM</div>
          <div className="value">
            {latestQuote?.pe_ttm ? parseFloat(latestQuote.pe_ttm).toFixed(2) : "—"}
          </div>
        </div>
        <div className="stat">
          <div className="label">PB</div>
          <div className="value">
            {latestQuote?.pb ? parseFloat(latestQuote.pb).toFixed(2) : "—"}
          </div>
        </div>
        <div className="stat">
          <div className="label">PS-TTM</div>
          <div className="value">
            {latestQuote?.ps_ttm ? parseFloat(latestQuote.ps_ttm).toFixed(2) : "—"}
          </div>
        </div>
        <div className="stat">
          <div className="label">实际历史</div>
          <div className="value">{data.actual_history_years.toFixed(1)} 年</div>
        </div>
      </section>

      <section className="settings-block">
        <label className="field horizontal" style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <span style={{ minWidth: 100 }}>估值锚（SRS R12）</span>
          <select
            value={data.anchor}
            onChange={(e) => anchorMut.mutate(e.target.value)}
            disabled={anchorMut.isPending}
          >
            {data.available_anchors.map((a) => (
              <option key={a} value={a}>
                {ANCHOR_LABEL[a] ?? a}
                {data.industry_default_anchor === a && "（行业默认）"}
              </option>
            ))}
          </select>
          <span className="hint" style={{ margin: 0 }}>{ANCHOR_HINT[data.anchor]}</span>
        </label>

        {/* SRS v1.3.0 J：所有锚对比 */}
        {data.anchor_comparisons.length > 0 && (
          <div style={{ marginTop: 12 }}>
            <p className="hint" style={{ marginBottom: 6 }}>
              <strong>5 种估值锚下的温度对比</strong> — 切换前先看哪个口径与你的判断最一致。
            </p>
            <div style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))",
              gap: 8,
            }}>
              {data.anchor_comparisons.map((c) => {
                const t = c.temperature ? parseFloat(c.temperature) : null;
                const isCurrent = c.anchor === data.anchor;
                const isDefault = c.anchor === data.industry_default_anchor;
                return (
                  <div
                    key={c.anchor}
                    onClick={() => !isCurrent && c.available && anchorMut.mutate(c.anchor)}
                    style={{
                      background: isCurrent ? "#dbeafe" : "white",
                      border: `2px solid ${isCurrent ? "#2563eb" : "#e5e7eb"}`,
                      padding: 10, borderRadius: 4,
                      cursor: c.available && !isCurrent ? "pointer" : "default",
                      opacity: c.available ? 1 : 0.5,
                    }}
                  >
                    <div style={{ fontSize: 11, color: "#6b7280", display: "flex", justifyContent: "space-between" }}>
                      <span>{ANCHOR_LABEL[c.anchor] ?? c.anchor}</span>
                      {isDefault && <span style={{ color: "#15803d" }}>行业默认</span>}
                      {isCurrent && <span style={{ color: "#2563eb" }}>当前</span>}
                    </div>
                    <div style={{
                      fontSize: 20, fontWeight: 600,
                      color: c.available ? "#1f2937" : "#9ca3af",
                    }}>
                      {t != null ? t.toFixed(1) : "—"}
                    </div>
                    <div style={{ fontSize: 11, color: "#6b7280" }}>
                      {c.tier ?? "无数据"}
                    </div>
                  </div>
                );
              })}
            </div>
            <p className="hint" style={{ marginTop: 8 }}>
              点击卡片切换锚（虚显的没有足够分位数据）。锚的语义会显著改变"贵/便宜"的判断：
              银行股 PB 锚低估时 PE 锚可能合理，因为 ROE 高拉低了 PE。
            </p>
          </div>
        )}
      </section>

      <section className="chart-block">
        <PriceValuationChart
          quotes={data.quotes as any}
          title="价格 + PE-TTM 历史（10y 分位带）"
        />
      </section>

      <section className="signal-timeline">
        <h3>分位历史（{data.valuation_series.length} 行 10y 窗口）</h3>
        {data.valuation_series.length === 0 ? (
          <p className="empty">分位序列尚未生成</p>
        ) : (
          <ul>
            {data.valuation_series.slice(-30).reverse().map((p) => (
              <li key={p.date}>
                <span className="date">{p.date}</span>
                <span className="temp">
                  温度 {p.temperature ? parseFloat(p.temperature).toFixed(1) : "—"}
                </span>
                <span className="tier-text">{p.tier ?? "—"}</span>
                <span style={{ color: "#6b7280", fontSize: 11 }}>
                  PE 分位 {p.pe_percentile ? (parseFloat(p.pe_percentile) * 100).toFixed(1) + "%" : "—"}
                  {" · "}
                  PB 分位 {p.pb_percentile ? (parseFloat(p.pb_percentile) * 100).toFixed(1) + "%" : "—"}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
