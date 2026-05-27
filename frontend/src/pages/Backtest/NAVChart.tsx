import { useMemo, useState } from "react";
import ReactECharts from "@/components/charts/ReactECharts";
import type { StrategyResultDTO } from "@/types/api";

const STRATEGY_LABEL: Record<string, string> = {
  threshold: "阈值策略",
  dca: "定投策略",
  buy_hold: "买入持有（基准）",
  by_temperature: "按温度调仓",
  temperature_dca: "温度反向定投",
};
const STRATEGY_COLOR: Record<string, string> = {
  threshold: "#2563eb",
  dca: "#f59e0b",
  buy_hold: "#6b7280",
  by_temperature: "#a855f7",
  temperature_dca: "#0ea5e9",
};

interface Props {
  strategies: (StrategyResultDTO | null)[];
}

type YMode = "nav" | "pct" | "log";

export default function NAVChart({ strategies }: Props) {
  const [yMode, setYMode] = useState<YMode>("pct");

  const option = useMemo(() => {
    const active = strategies.filter((s): s is StrategyResultDTO => s != null);
    const longest = active.reduce<StrategyResultDTO | null>(
      (a, b) => (b.nav_curve.length > (a?.nav_curve.length ?? 0) ? b : a),
      null,
    );
    const dates = longest?.nav_curve.map((p) => p.date) ?? [];

    const transform = (nav: number, baseNav: number): number => {
      if (yMode === "nav") return nav;
      if (yMode === "pct") return (nav - baseNav) / baseNav * 100;
      // log
      return nav <= 0 ? 0 : Math.log(nav);
    };

    const series = active.map((s) => {
      const byDate = new Map(s.nav_curve.map((p) => [p.date, p.nav]));
      const baseNav = s.nav_curve.length > 0 ? parseFloat(s.nav_curve[0].nav) : 1;

      // 标注买卖点
      const markPoints = s.trades.slice(0, 100).map((t) => {
        const navRaw = byDate.has(t.date) ? parseFloat(byDate.get(t.date)!) : 1;
        return {
          coord: [t.date, transform(navRaw, baseNav)],
          value: t.action === "SELL" ? "S" : "B",
          itemStyle: { color: t.action === "SELL" ? "#b91c1c" : "#15803d" },
          symbolSize: 14,
        };
      });

      return {
        name: STRATEGY_LABEL[s.name],
        type: "line",
        data: dates.map((d) => byDate.has(d) ? transform(parseFloat(byDate.get(d)!), baseNav) : null),
        showSymbol: false,
        lineStyle: { width: 1.6, color: STRATEGY_COLOR[s.name] },
        markPoint: s.trades.length > 0 ? {
          symbol: "circle",
          label: { fontSize: 10, color: "white" },
          data: markPoints,
        } : undefined,
      };
    });

    const yAxisFormatter =
      yMode === "pct" ? (v: number) => `${v >= 0 ? "+" : ""}${v.toFixed(0)}%`
      : yMode === "log" ? (v: number) => Math.exp(v).toFixed(2)
      : undefined;

    return {
      title: {
        text: yMode === "pct" ? "相对涨跌（每条曲线起点 = 0%）"
            : yMode === "log" ? "NAV 对数刻度"
            : "NAV 曲线（起始=1）",
        left: "center", textStyle: { fontSize: 14 },
      },
      tooltip: {
        trigger: "axis",
        valueFormatter: (v: number | null) =>
          v == null ? "—"
          : yMode === "pct" ? `${v >= 0 ? "+" : ""}${v.toFixed(2)}%`
          : yMode === "log" ? Math.exp(v).toFixed(4)
          : v.toFixed(4),
      },
      legend: { data: active.map((s) => STRATEGY_LABEL[s.name]), top: 28 },
      grid: { left: 70, right: 30, top: 70, bottom: 50 },
      xAxis: { type: "category", data: dates, boundaryGap: false },
      yAxis: {
        type: "value",
        scale: true,
        axisLabel: yAxisFormatter ? { formatter: yAxisFormatter } : undefined,
        splitLine: { show: true },
      },
      dataZoom: [
        { type: "inside", start: 0, end: 100 },
        { type: "slider", start: 0, end: 100, bottom: 6, height: 16 },
      ],
      series,
    };
  }, [strategies, yMode]);

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "flex-end", gap: 4, marginBottom: 4 }}>
        <div style={{
          display: "inline-flex", border: "1px solid #d1d5db", borderRadius: 4, overflow: "hidden",
        }}>
          {(["pct", "nav", "log"] as YMode[]).map((m) => (
            <button
              key={m}
              type="button"
              onClick={() => setYMode(m)}
              style={{
                padding: "3px 10px", fontSize: 11,
                background: yMode === m ? "#2563eb" : "white",
                color: yMode === m ? "white" : "#374151",
                border: "none",
                borderLeft: m !== "pct" ? "1px solid #d1d5db" : "none",
                cursor: "pointer",
              }}
            >
              {m === "pct" ? "相对涨跌 %" : m === "nav" ? "NAV 绝对" : "对数 Y"}
            </button>
          ))}
        </div>
      </div>
      <ReactECharts option={option} style={{ height: 380, width: "100%" }} />
    </div>
  );
}
