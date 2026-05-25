import { useMemo } from "react";
import ReactECharts from "@/components/charts/ReactECharts";
import type { QuotePoint, ValuationPoint } from "@/types/api";

interface Props {
  quotes: QuotePoint[];
  /** Reserved for future use（M3+ 在图上叠加 valuations 序列） */
  valuations?: ValuationPoint[];
  title?: string;
}

/**
 * 主图：左轴价格 (close)；右轴 PE-TTM；4 条百分位水平参考线（10/30/70/90 → 0.10/0.30/0.70/0.90 对应的 PE 值）
 */
export default function PriceValuationChart({ quotes, title }: Props) {
  const option = useMemo(() => {
    const dates = quotes.map((q) => q.date);
    const closes = quotes.map((q) => parseFloat(q.close));
    const pes = quotes.map((q) =>
      q.pe_ttm == null ? null : parseFloat(q.pe_ttm),
    );

    // 计算 PE 历史的分位数（基于 valuations 中存的 pe_percentile + 当日 PE_TTM 估算）
    // 更精确：直接用 PE 历史序列的 10/30/70/90 百分位
    const validPes = pes.filter((v): v is number => v != null).sort((a, b) => a - b);
    // PE 数据点 < 250 视为"快照"，不画 PE 折线和参考线（与后端 R7 阈值一致）
    const hasHistoricalPe = validPes.length >= 250;

    const quantile = (q: number): number | null => {
      if (validPes.length === 0) return null;
      const idx = Math.max(0, Math.min(validPes.length - 1, Math.floor(q * validPes.length)));
      return validPes[idx];
    };
    const refLines = hasHistoricalPe
      ? [
          { yAxis: quantile(0.1), label: "10%", color: "#15803d" },
          { yAxis: quantile(0.3), label: "30%", color: "#22c55e" },
          { yAxis: quantile(0.7), label: "70%", color: "#f87171" },
          { yAxis: quantile(0.9), label: "90%", color: "#b91c1c" },
        ].filter((r): r is { yAxis: number; label: string; color: string } => r.yAxis != null)
      : [];

    const series: Record<string, unknown>[] = [
      {
        name: "收盘价",
        type: "line",
        data: closes,
        yAxisIndex: 0,
        showSymbol: false,
        lineStyle: { width: 1.5, color: "#1f2937" },
      },
    ];
    if (hasHistoricalPe) {
      series.push({
        name: "PE-TTM",
        type: "line",
        data: pes,
        yAxisIndex: 1,
        showSymbol: false,
        lineStyle: { width: 1.5, color: "#2563eb" },
        markLine: {
          silent: true,
          symbol: "none",
          label: { formatter: "{b}", position: "end", fontSize: 10 },
          data: refLines.map((r) => ({
            name: `PE分位 ${r.label}`,
            yAxis: r.yAxis,
            lineStyle: { type: "dashed", color: r.color, width: 1 },
          })),
        },
      });
    }

    return {
      title: title ? { text: title, left: "center", textStyle: { fontSize: 14 } } : undefined,
      tooltip: { trigger: "axis" },
      legend: hasHistoricalPe ? { data: ["收盘价", "PE-TTM"], top: 26 } : { data: ["收盘价"], top: 26 },
      grid: { left: 50, right: hasHistoricalPe ? 60 : 16, top: 60, bottom: 50 },
      xAxis: { type: "category", data: dates, boundaryGap: false },
      yAxis: hasHistoricalPe
        ? [
            { type: "value", name: "收盘", scale: true, position: "left" },
            { type: "value", name: "PE", scale: true, position: "right" },
          ]
        : [{ type: "value", name: "收盘", scale: true }],
      dataZoom: [
        { type: "inside", start: 0, end: 100 },
        { type: "slider", start: 0, end: 100, bottom: 6, height: 16 },
      ],
      series,
    };
  }, [quotes, title]);

  return <ReactECharts option={option} style={{ height: 380, width: "100%" }} />;
}
