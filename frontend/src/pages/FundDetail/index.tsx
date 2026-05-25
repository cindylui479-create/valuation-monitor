import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { useMemo } from "react";
import ReactECharts from "@/components/charts/ReactECharts";
import { fetchFundDetail } from "@/api/funds";
import { temperatureColor, tierLabel } from "@/utils/temperature";

export default function FundDetail() {
  const { code = "" } = useParams<{ code: string }>();

  const { data, isLoading, error } = useQuery({
    queryKey: ["fund-detail", code],
    queryFn: () => fetchFundDetail(code),
    enabled: !!code,
  });

  const navChartOption = useMemo(() => {
    if (!data || data.nav_history.length === 0) return null;
    const dates = data.nav_history.map((n) => n.date);
    const navs = data.nav_history.map((n) => parseFloat(n.nav));
    const sortedNavs = [...navs].sort((a, b) => a - b);
    const q = (p: number) => {
      const idx = Math.max(0, Math.min(sortedNavs.length - 1, Math.floor(p * sortedNavs.length)));
      return sortedNavs[idx];
    };
    const refs = sortedNavs.length >= 250 ? [
      { yAxis: q(0.1), label: "10%", color: "#15803d" },
      { yAxis: q(0.3), label: "30%", color: "#22c55e" },
      { yAxis: q(0.7), label: "70%", color: "#f87171" },
      { yAxis: q(0.9), label: "90%", color: "#b91c1c" },
    ] : [];
    return {
      grid: { left: 50, right: 20, top: 40, bottom: 50 },
      tooltip: { trigger: "axis" },
      xAxis: { type: "category", data: dates, boundaryGap: false },
      yAxis: { type: "value", name: "单位净值", scale: true },
      series: [
        {
          name: "NAV",
          type: "line",
          data: navs,
          showSymbol: false,
          lineStyle: { width: 1.5, color: "#2563eb" },
          markLine: refs.length > 0 ? {
            silent: true,
            symbol: "none",
            data: refs.map((r) => ({
              yAxis: r.yAxis,
              lineStyle: { color: r.color, type: "dashed", width: 1 },
              label: { formatter: r.label, color: r.color, position: "insideEndTop" },
            })),
          } : undefined,
        },
      ],
    };
  }, [data]);

  if (isLoading) return <div className="state">加载中…</div>;
  if (error) return <div className="state error">加载失败：{(error as Error).message}</div>;
  if (!data) return null;

  const v = data.latest_valuation;
  const latestNav = data.nav_history[data.nav_history.length - 1];

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
            主动基金 · {data.market} · CNY
            {data.fund_manager && <> · 基金经理 {data.fund_manager}</>}
            {data.setup_date && <> · 成立 {data.setup_date}</>}
            {data.data_window_note && (
              <span className="window-note"> · {data.data_window_note}</span>
            )}
          </p>
        </div>
      </header>

      <div style={{
        background: "#fef3c7", color: "#92400e",
        padding: "8px 12px", borderRadius: 4, margin: "12px 0",
        fontSize: 13,
      }}>
        ⚠ <strong>主动基金估值口径：NAV 5 年历史百分位</strong>。
        仅反映"基金净值与自身历史比"，<strong>不反映持仓水位</strong>（季报披露 70% 持仓且滞后，未接入）。
        基金经理风格漂移、持仓换手等因素也未考虑。
      </div>

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
          <div className="label">温度（NAV 5y 锚）</div>
          <div className="value">
            {v?.temperature ? parseFloat(v.temperature).toFixed(1) : "—"}
          </div>
        </div>
        <div className="stat">
          <div className="label">最新 NAV</div>
          <div className="value">
            {latestNav ? parseFloat(latestNav.nav).toFixed(4) : "—"}
          </div>
        </div>
        <div className="stat">
          <div className="label">NAV 5y 分位</div>
          <div className="value">
            {v?.nav_percentile ? (parseFloat(v.nav_percentile) * 100).toFixed(1) + "%" : "—"}
          </div>
        </div>
        <div className="stat">
          <div className="label">实际历史</div>
          <div className="value">{data.actual_history_years.toFixed(1)} 年</div>
        </div>
      </section>

      {navChartOption && (
        <section className="chart-block">
          <h3 style={{ margin: 0 }}>NAV 历史（含 5y 百分位带）</h3>
          <ReactECharts option={navChartOption} style={{ height: 420 }} />
        </section>
      )}

      <section className="signal-timeline">
        <h3>分位历史（{data.valuation_series.length} 行 5y 窗口）</h3>
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
                  NAV 分位 {p.nav_percentile ? (parseFloat(p.nav_percentile) * 100).toFixed(1) + "%" : "—"}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
