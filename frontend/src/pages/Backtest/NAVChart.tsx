import { useMemo } from "react";
import ReactECharts from "@/components/charts/ReactECharts";
import type { StrategyResultDTO } from "@/types/api";

const STRATEGY_LABEL: Record<string, string> = {
  threshold: "阈值策略",
  dca: "定投策略",
  buy_hold: "买入持有（基准）",
};
const STRATEGY_COLOR: Record<string, string> = {
  threshold: "#2563eb",
  dca: "#f59e0b",
  buy_hold: "#6b7280",
};

interface Props {
  strategies: (StrategyResultDTO | null)[];
}

export default function NAVChart({ strategies }: Props) {
  const option = useMemo(() => {
    const active = strategies.filter((s): s is StrategyResultDTO => s != null);
    // 取最长 nav_curve 的日期序列作为 X 轴
    const longest = active.reduce<StrategyResultDTO | null>(
      (a, b) => (b.nav_curve.length > (a?.nav_curve.length ?? 0) ? b : a),
      null,
    );
    const dates = longest?.nav_curve.map((p) => p.date) ?? [];

    const series = active.map((s) => {
      const byDate = new Map(s.nav_curve.map((p) => [p.date, p.nav]));
      // 标注买卖点
      const markPoints = s.trades.slice(0, 100).map((t) => ({
        coord: [t.date, parseFloat(byDate.get(t.date) ?? "1")],
        value: t.action === "SELL" ? "S" : "B",
        itemStyle: { color: t.action === "SELL" ? "#b91c1c" : "#15803d" },
        symbolSize: 14,
      }));
      return {
        name: STRATEGY_LABEL[s.name],
        type: "line",
        data: dates.map((d) => (byDate.has(d) ? parseFloat(byDate.get(d)!) : null)),
        showSymbol: false,
        lineStyle: { width: 1.6, color: STRATEGY_COLOR[s.name] },
        markPoint: s.trades.length > 0 ? {
          symbol: "circle",
          label: { fontSize: 10, color: "white" },
          data: markPoints,
        } : undefined,
      };
    });

    return {
      title: { text: "NAV 曲线（起始=1）", left: "center", textStyle: { fontSize: 14 } },
      tooltip: { trigger: "axis" },
      legend: { data: active.map((s) => STRATEGY_LABEL[s.name]), top: 28 },
      grid: { left: 60, right: 30, top: 70, bottom: 50 },
      xAxis: { type: "category", data: dates, boundaryGap: false },
      yAxis: { type: "value", scale: true },
      dataZoom: [
        { type: "inside", start: 0, end: 100 },
        { type: "slider", start: 0, end: 100, bottom: 6, height: 16 },
      ],
      series,
    };
  }, [strategies]);

  return <ReactECharts option={option} style={{ height: 380, width: "100%" }} />;
}
