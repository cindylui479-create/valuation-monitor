import { jsx as _jsx } from "react/jsx-runtime";
import { useMemo } from "react";
import ReactECharts from "@/components/charts/ReactECharts";
export default function PBChart({ quotes }) {
    const option = useMemo(() => {
        const dates = quotes.map((q) => q.date);
        const pbs = quotes.map((q) => (q.pb == null ? null : parseFloat(q.pb)));
        const validPbs = pbs.filter((v) => v != null).sort((a, b) => a - b);
        const quantile = (q) => {
            if (validPbs.length === 0)
                return null;
            const idx = Math.max(0, Math.min(validPbs.length - 1, Math.floor(q * validPbs.length)));
            return validPbs[idx];
        };
        const refs = [
            { y: quantile(0.1), label: "10%", color: "#15803d" },
            { y: quantile(0.3), label: "30%", color: "#22c55e" },
            { y: quantile(0.7), label: "70%", color: "#f87171" },
            { y: quantile(0.9), label: "90%", color: "#b91c1c" },
        ].filter((r) => r.y != null);
        return {
            title: { text: "PB（10y 百分位带）", left: "center", textStyle: { fontSize: 13 } },
            tooltip: { trigger: "axis" },
            grid: { left: 50, right: 60, top: 36, bottom: 30 },
            xAxis: { type: "category", data: dates, boundaryGap: false },
            yAxis: { type: "value", scale: true },
            series: [
                {
                    name: "PB",
                    type: "line",
                    data: pbs,
                    showSymbol: false,
                    lineStyle: { width: 1.3, color: "#7c3aed" },
                    markLine: {
                        silent: true,
                        symbol: "none",
                        label: { formatter: "{b}", position: "end", fontSize: 10 },
                        data: refs.map((r) => ({
                            name: `PB分位 ${r.label}`,
                            yAxis: r.y,
                            lineStyle: { type: "dashed", color: r.color, width: 1 },
                        })),
                    },
                },
            ],
        };
    }, [quotes]);
    return _jsx(ReactECharts, { option: option, style: { height: 220, width: "100%" } });
}
