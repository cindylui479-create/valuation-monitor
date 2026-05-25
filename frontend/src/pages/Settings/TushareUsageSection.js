import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import ReactECharts from "@/components/charts/ReactECharts";
import { fetchTushareUsage } from "@/api/tushareUsage";
export default function TushareUsageSection() {
    const { data, isLoading } = useQuery({
        queryKey: ["tushare-usage"],
        queryFn: fetchTushareUsage,
    });
    // 30 天逐日图：把 API 返回的稀疏点对齐到完整 30 天日历，缺失填 0
    // ⚠ Hook 必须在条件 return 之前调用（React Rules of Hooks）
    const dailyChartOption = useMemo(() => {
        if (!data)
            return null;
        const today = new Date();
        const days = [];
        const byDate = new Map(data.last_30_days.map((d) => [d.date, d]));
        for (let i = 29; i >= 0; i--) {
            const d = new Date(today);
            d.setDate(d.getDate() - i);
            const key = d.toISOString().slice(0, 10);
            const hit = byDate.get(key);
            days.push({
                date: key,
                calls: hit?.n_calls ?? 0,
                failures: hit?.n_failures ?? 0,
            });
        }
        return {
            grid: { left: 50, right: 60, top: 30, bottom: 40 },
            tooltip: {
                trigger: "axis",
                formatter: (params) => {
                    const d = days[params[0].dataIndex];
                    return `${d.date}<br/>调用 ${d.calls.toLocaleString()}<br/>` +
                        (d.failures > 0 ? `<span style="color:#b91c1c">失败 ${d.failures}</span>` : "无失败");
                },
            },
            legend: {
                data: ["调用次数", "失败次数"],
                top: 0,
                textStyle: { fontSize: 11 },
            },
            xAxis: {
                type: "category",
                data: days.map((d) => d.date.slice(5)),
                axisLabel: { fontSize: 10, interval: 4 },
            },
            yAxis: [
                {
                    type: "value",
                    name: "调用",
                    position: "left",
                    nameTextStyle: { fontSize: 10 },
                    axisLabel: { fontSize: 10 },
                },
                {
                    type: "value",
                    name: "失败",
                    position: "right",
                    nameTextStyle: { fontSize: 10 },
                    axisLabel: { fontSize: 10 },
                    splitLine: { show: false },
                },
            ],
            series: [
                {
                    name: "调用次数",
                    type: "bar",
                    data: days.map((d) => d.calls),
                    itemStyle: { color: "#2563eb" },
                    barWidth: "60%",
                },
                {
                    name: "失败次数",
                    type: "line",
                    yAxisIndex: 1,
                    data: days.map((d) => d.failures),
                    itemStyle: { color: "#dc2626" },
                    lineStyle: { width: 2 },
                    symbolSize: 6,
                },
            ],
        };
    }, [data]);
    if (isLoading) {
        return (_jsxs("section", { className: "settings-block", children: [_jsx("h3", { children: "Tushare \u914D\u989D\u76D1\u63A7\uFF08v1.3.0 E\uFF09" }), _jsx("p", { className: "empty", children: "\u52A0\u8F7D\u4E2D\u2026" })] }));
    }
    if (!data)
        return null;
    const todayFailureRate = data.today.total_calls > 0
        ? (data.today.total_failures / data.today.total_calls * 100).toFixed(1)
        : "0.0";
    const monthFailureRate = data.month.total_calls > 0
        ? (data.month.total_failures / data.month.total_calls * 100).toFixed(1)
        : "0.0";
    return (_jsxs("section", { className: "settings-block", children: [_jsxs("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center" }, children: [_jsx("h3", { children: "Tushare \u914D\u989D\u76D1\u63A7\uFF08v1.3.0 E\uFF09" }), _jsx("span", { style: { fontSize: 12, color: "var(--muted)" }, children: "2000 \u79EF\u5206\u7528\u6237\u9650\u5236\uFF1A200 \u8C03\u7528/\u5206\uFF1B\u4E2A\u522B\u63A5\u53E3\uFF08\u6210\u5206\u80A1\u805A\u5408\u5360 80%+\uFF09\u6708\u5EA6\u79EF\u5206\u6709\u4E0A\u9650" })] }), _jsxs("div", { style: {
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
                    gap: 12, margin: "12px 0",
                }, children: [_jsxs("div", { style: { background: "white", padding: 12, borderRadius: 4, border: "1px solid #e5e7eb" }, children: [_jsx("div", { style: { fontSize: 11, color: "#6b7280" }, children: "\u4ECA\u65E5\u8C03\u7528" }), _jsx("div", { style: { fontSize: 24, fontWeight: 600 }, children: data.today.total_calls.toLocaleString() }), _jsxs("div", { style: { fontSize: 11, color: data.today.total_failures > 0 ? "#b91c1c" : "#15803d" }, children: ["\u5931\u8D25 ", data.today.total_failures, "\uFF08", todayFailureRate, "%\uFF09"] })] }), _jsxs("div", { style: { background: "white", padding: 12, borderRadius: 4, border: "1px solid #e5e7eb" }, children: [_jsxs("div", { style: { fontSize: 11, color: "#6b7280" }, children: ["\u672C\u6708\u8C03\u7528\uFF08\u81EA ", data.month.month_start, "\uFF09"] }), _jsx("div", { style: { fontSize: 24, fontWeight: 600 }, children: data.month.total_calls.toLocaleString() }), _jsxs("div", { style: { fontSize: 11, color: data.month.total_failures > 0 ? "#b91c1c" : "#15803d" }, children: ["\u5931\u8D25 ", data.month.total_failures, "\uFF08", monthFailureRate, "%\uFF09"] })] })] }), dailyChartOption && (_jsxs("div", { style: { marginBottom: 12 }, children: [_jsx("div", { style: { fontSize: 12, color: "#6b7280", marginBottom: 4 }, children: "\u8FD1 30 \u5929\u9010\u65E5" }), _jsx(ReactECharts, { option: dailyChartOption, style: { height: 200 } })] })), data.by_interface_30d.length > 0 && (_jsxs("div", { children: [_jsx("div", { style: { fontSize: 12, color: "#6b7280", marginBottom: 4 }, children: "\u8FD1 30 \u5929\u6309\u63A5\u53E3\u5206\u5E03" }), _jsxs("table", { className: "table", style: { fontSize: 12 }, children: [_jsx("thead", { children: _jsxs("tr", { children: [_jsx("th", { children: "\u63A5\u53E3" }), _jsx("th", { children: "\u8C03\u7528\u6B21\u6570" }), _jsx("th", { children: "\u5931\u8D25\u6B21\u6570" }), _jsx("th", { children: "\u5931\u8D25\u7387" }), _jsx("th", { children: "\u6700\u8FD1\u9519\u8BEF" })] }) }), _jsx("tbody", { children: data.by_interface_30d.map((it) => {
                                    const rate = it.n_calls > 0
                                        ? (it.n_failures / it.n_calls * 100).toFixed(1)
                                        : "0.0";
                                    return (_jsxs("tr", { children: [_jsx("td", { children: _jsx("strong", { children: it.interface }) }), _jsx("td", { children: it.n_calls.toLocaleString() }), _jsx("td", { style: { color: it.n_failures > 0 ? "#b91c1c" : undefined }, children: it.n_failures }), _jsxs("td", { children: [rate, "%"] }), _jsx("td", { style: { color: "#6b7280", fontSize: 11 }, children: it.last_error_message ?? "—" })] }, it.interface));
                                }) })] })] })), _jsx("p", { className: "hint", children: "\u82E5\u67D0\u63A5\u53E3\u5931\u8D25\u7387\u7A81\u7136\u98D9\u5347\uFF0C\u53EF\u80FD\u662F\u914D\u989D\u8017\u5C3D \u2014 \u67E5\u770B Tushare \u7528\u6237\u4E2D\u5FC3\u7684\u79EF\u5206\u4F59\u989D\u3002 \u6210\u5206\u80A1\u805A\u5408\uFF08daily_basic + index_weight\uFF09\u6BCF\u65E5 A \u8C03\u5EA6\u8DD1\u4E00\u6B21\u7EA6 250-300 \u6B21\u8C03\u7528\u3002" })] }));
}
