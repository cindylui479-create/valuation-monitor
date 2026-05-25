import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
/**
 * SRS v1.3.0 EFF：温度有效性分析。
 *
 * 不再回顾"信号事件"（样本太少），改为回顾"温度档位 → 未来收益"的统计关系。
 * 每只指数每个交易日都是一个数据点（10 年 × 24 指数 ≈ 5 万样本）。
 */
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import ReactECharts from "@/components/charts/ReactECharts";
import { fetchEffectiveness } from "@/api/effectiveness";
const TIER_COLOR = {
    极度低估: "#15803d",
    低估: "#22c55e",
    合理: "#9ca3af",
    高估: "#f87171",
    极度高估: "#b91c1c",
};
export default function TemperatureEffectiveness() {
    const [horizon, setHorizon] = useState(90);
    const [years, setYears] = useState(10);
    const [indexCode, setIndexCode] = useState("");
    const { data, isLoading } = useQuery({
        queryKey: ["effectiveness", horizon, years, indexCode],
        queryFn: () => fetchEffectiveness(horizon, years, indexCode || undefined),
    });
    // 主图：5 档位柱状图 + P25/P75 误差棒
    const coarseOption = useMemo(() => {
        if (!data)
            return null;
        const buckets = data.coarse_buckets;
        return {
            grid: { left: 60, right: 30, top: 40, bottom: 60 },
            tooltip: {
                trigger: "axis",
                formatter: (params) => {
                    const i = params[0].dataIndex;
                    const b = buckets[i];
                    if (b.n_samples === 0)
                        return `${b.tier}：无样本`;
                    return `<strong>${b.tier}</strong> (温度 ${b.temp_range}, n=${b.n_samples})<br/>
            中位收益 ${b.median_return_pct}%<br/>
            均值 ${b.mean_return_pct}%<br/>
            P25/P75 ${b.p25}% / ${b.p75}%<br/>
            P10/P90 ${b.p10}% / ${b.p90}%<br/>
            胜率 ${b.win_rate}%`;
                },
            },
            xAxis: {
                type: "category",
                data: buckets.map((b) => `${b.tier}\n${b.temp_range}`),
                axisLabel: { interval: 0 },
            },
            yAxis: {
                type: "value",
                name: `${horizon} 天后中位收益 %`,
                axisLine: { onZero: true },
            },
            series: [
                {
                    type: "bar",
                    name: "中位收益",
                    data: buckets.map((b) => ({
                        value: b.median_return_pct ? parseFloat(b.median_return_pct) : 0,
                        itemStyle: { color: TIER_COLOR[b.tier] ?? "#9ca3af" },
                    })),
                    barWidth: "45%",
                    markLine: {
                        silent: true,
                        symbol: "none",
                        data: [{ yAxis: 0, lineStyle: { color: "#000", type: "solid", width: 1 } }],
                    },
                },
                {
                    type: "custom",
                    name: "P25–P75 区间",
                    renderItem: (params, api) => {
                        const b = buckets[params.dataIndex];
                        if (!b.p25 || !b.p75)
                            return null;
                        const x = api.coord([params.dataIndex, 0])[0];
                        const yTop = api.coord([params.dataIndex, parseFloat(b.p75)])[1];
                        const yBot = api.coord([params.dataIndex, parseFloat(b.p25)])[1];
                        return {
                            type: "group",
                            children: [
                                {
                                    type: "line",
                                    shape: { x1: x, y1: yTop, x2: x, y2: yBot },
                                    style: { stroke: "#374151", lineWidth: 1.5 },
                                },
                                {
                                    type: "line",
                                    shape: { x1: x - 10, y1: yTop, x2: x + 10, y2: yTop },
                                    style: { stroke: "#374151", lineWidth: 1.5 },
                                },
                                {
                                    type: "line",
                                    shape: { x1: x - 10, y1: yBot, x2: x + 10, y2: yBot },
                                    style: { stroke: "#374151", lineWidth: 1.5 },
                                },
                            ],
                        };
                    },
                    data: buckets.map(() => 0),
                },
            ],
        };
    }, [data, horizon]);
    // 散点图：10 度细分
    const fineOption = useMemo(() => {
        if (!data)
            return null;
        const points = data.fine_buckets.filter((p) => p.n_samples > 0);
        return {
            grid: { left: 60, right: 30, top: 40, bottom: 60 },
            tooltip: {
                trigger: "axis",
                formatter: (params) => {
                    const p = points[params[0].dataIndex];
                    return `温度 ${p.temp_center} (±5)，n=${p.n_samples}<br/>中位收益 ${p.median_return_pct}%`;
                },
            },
            xAxis: {
                type: "value",
                name: "温度档位（10 度细分）",
                min: 0, max: 100,
                splitLine: { show: true },
            },
            yAxis: {
                type: "value",
                name: `${horizon} 天后中位收益 %`,
                axisLine: { onZero: true },
            },
            series: [
                {
                    type: "line",
                    smooth: true,
                    symbolSize: 12,
                    data: points.map((p) => [
                        p.temp_center,
                        p.median_return_pct ? parseFloat(p.median_return_pct) : null,
                    ]),
                    lineStyle: { width: 2, color: "#2563eb" },
                    itemStyle: { color: "#2563eb" },
                    markLine: {
                        silent: true,
                        symbol: "none",
                        data: [{ yAxis: 0, lineStyle: { color: "#000", type: "solid", width: 1 } }],
                    },
                },
            ],
        };
    }, [data, horizon]);
    if (isLoading)
        return _jsx("div", { className: "state", children: "\u52A0\u8F7D\u4E2D\u2026" });
    if (!data)
        return null;
    return (_jsxs("div", { className: "watchlist-page", children: [_jsx("h2", { children: "\u6E29\u5EA6\u6709\u6548\u6027\u5206\u6790" }), _jsxs("p", { className: "hint", children: ["\u628A\u6BCF\u53EA\u6307\u6570\u7684\u6BCF\u4E2A\u4EA4\u6613\u65E5\u5F53\u4E00\u4E2A\u6570\u636E\u70B9\uFF0C\u770B\u4E0D\u540C\u6E29\u5EA6\u6863\u4F4D\u7684", _jsx("strong", { children: "\u672A\u6765 N \u5929\u6536\u76CA" }), "\u5206\u5E03\u3002 \u82E5\"\u4F4E\u4F30\u4E70\u5165\"\u5047\u8BBE\u6210\u7ACB\uFF0C\u5E94\u8BE5\u770B\u5230\u6E29\u5EA6 < 30 \u7684\u4E2D\u4F4D\u6536\u76CA\u663E\u8457\u9AD8\u4E8E\u6E29\u5EA6 > 70 \u7684\uFF08\u5355\u8C03\u5DE6\u9AD8\u53F3\u4F4E\uFF09\u3002 \u5B9E\u8BC1\u53EF\u80FD\u53CD\u76F4\u89C9 \u2014 \u8BA9\u4F60\u8BDA\u5B9E\u9762\u5BF9\u5F53\u524D\u6E29\u5EA6\u9608\u503C\u662F\u5426\u771F\u6709\u9884\u6D4B\u529B\u3002"] }), _jsxs("div", { style: { display: "flex", gap: 16, alignItems: "center", marginBottom: 16, flexWrap: "wrap" }, children: [_jsxs("label", { style: { display: "flex", alignItems: "center", gap: 6 }, children: ["Horizon\uFF1A", _jsxs("select", { value: horizon, onChange: (e) => setHorizon(Number(e.target.value)), children: [_jsx("option", { value: 30, children: "30 \u5929" }), _jsx("option", { value: 90, children: "90 \u5929" }), _jsx("option", { value: 180, children: "180 \u5929" }), _jsx("option", { value: 365, children: "365 \u5929" }), _jsx("option", { value: 730, children: "730 \u5929\uFF082 \u5E74\uFF09" })] })] }), _jsxs("label", { style: { display: "flex", alignItems: "center", gap: 6 }, children: ["\u5386\u53F2\u8303\u56F4\uFF1A", _jsxs("select", { value: years, onChange: (e) => setYears(Number(e.target.value)), children: [_jsx("option", { value: 3, children: "3 \u5E74" }), _jsx("option", { value: 5, children: "5 \u5E74" }), _jsx("option", { value: 10, children: "10 \u5E74" }), _jsx("option", { value: 15, children: "15 \u5E74" })] })] }), _jsxs("label", { style: { display: "flex", alignItems: "center", gap: 6 }, children: ["\u8303\u56F4\uFF1A", _jsxs("select", { value: indexCode, onChange: (e) => setIndexCode(e.target.value), children: [_jsx("option", { value: "", children: "\u5168\u90E8\u6307\u6570" }), data.indices_coverage.map((c) => (_jsxs("option", { value: c.code, children: [c.code, " ", c.name, " (", c.n_samples, ")"] }, c.code)))] })] }), _jsxs("span", { style: { marginLeft: "auto", fontSize: 12, color: "#6b7280" }, children: ["\u6837\u672C\u91CF\uFF1A", data.total_samples.toLocaleString()] })] }), data.spearman_ic != null && (_jsxs("section", { className: "settings-block", children: [_jsxs("h3", { children: ["Spearman IC\uFF08\u6E29\u5EA6 \u2194 \u672A\u6765 ", horizon, " \u5929\u6536\u76CA\u7684\u79E9\u76F8\u5173\uFF09"] }), _jsxs("div", { style: { display: "flex", alignItems: "center", gap: 16 }, children: [_jsx("div", { style: {
                                    fontSize: 36, fontWeight: 700,
                                    color: (() => {
                                        const ic = parseFloat(data.spearman_ic);
                                        return ic <= -0.05 ? "#15803d" : ic >= 0.05 ? "#dc2626" : "#6b7280";
                                    })(),
                                }, children: parseFloat(data.spearman_ic).toFixed(4) }), _jsxs("div", { style: { fontSize: 12, color: "#6b7280" }, children: [_jsxs("div", { children: ["\u8D1F\u503C\uFF08\u63A5\u8FD1 -1\uFF09= \u6E29\u5EA6\u8D8A\u9AD8\uFF0C\u672A\u6765\u6536\u76CA\u8D8A\u4F4E\uFF0C", _jsx("strong", { children: "\u9006\u6E29\u5EA6\u7B56\u7565\u6709\u6548" }), "\u3002"] }), _jsx("div", { children: "0 \u9644\u8FD1 = \u6E29\u5EA6\u65E0\u9884\u6D4B\u529B\u3002" }), _jsx("div", { children: "\u6B63\u503C = \u53CD\u5411\uFF08\u9AD8\u6E29\u5EA6\u53CD\u800C\u540E\u7EED\u6DA8\uFF09\u2014 \u4E0E\u9006\u5411\u6295\u8D44\u5047\u8BBE\u76F8\u6096\u3002" }), _jsx("div", { style: { marginTop: 4, fontSize: 11 }, children: "|IC| < 0.05 \u901A\u5E38\u89C6\u4E3A\"\u65E0\u663E\u8457\u4FE1\u53F7\"\uFF1B|IC| \u2265 0.05 \u7B97\"\u5F31\u4FE1\u53F7\"\uFF1B\u2265 0.10 \u7B97\"\u4E2D\u7B49\u4FE1\u53F7\"\u3002" })] })] })] })), _jsxs("section", { className: "settings-block", children: [_jsxs("h3", { children: ["5 \u6863\u4F4D vs \u672A\u6765 ", horizon, " \u5929\u6536\u76CA"] }), coarseOption && (_jsx(ReactECharts, { option: coarseOption, style: { height: 360 } })), _jsxs("p", { className: "hint", children: ["\u67F1\u9AD8 = \u8BE5\u6863\u4F4D\u5386\u53F2\u6837\u672C\u7684\u672A\u6765\u6536\u76CA", _jsx("strong", { children: "\u4E2D\u4F4D\u6570" }), "\uFF1B\u7AD6\u7EBF = P25\u2013P75 \u533A\u95F4\uFF08\u4E2D\u95F4 50% \u6837\u672C\u7684\u6536\u76CA\uFF09\u3002 \u7406\u60F3\u5047\u8BBE\uFF1A\u5DE6\u4FA7\uFF08\u4F4E\u4F30\uFF09\u67F1\u9AD8 > 0\uFF0C\u53F3\u4FA7\uFF08\u9AD8\u4F30\uFF09\u67F1\u9AD8 < 0\u3002"] })] }), _jsxs("section", { className: "settings-block", children: [_jsx("h3", { children: "\u6E29\u5EA6\u7CBE\u7EC6\u5206\u6876\uFF0810 \u5EA6\u4E00\u6863\uFF09" }), fineOption && (_jsx(ReactECharts, { option: fineOption, style: { height: 320 } })), _jsx("p", { className: "hint", children: "\u6BCF 10 \u5EA6\u4E00\u4E2A\u6570\u636E\u70B9\u3002\u7406\u60F3\u5047\u8BBE\uFF1A\u6298\u7EBF\u4ECE\u5DE6\u4E0A\u5F80\u53F3\u4E0B\u8D70\uFF08\u6E29\u5EA6\u8D8A\u9AD8\u672A\u6765\u6536\u76CA\u8D8A\u4F4E\uFF09\u3002" })] }), _jsxs("section", { className: "settings-block", children: [_jsx("h3", { children: "\u660E\u7EC6\u6570\u636E" }), _jsxs("table", { className: "table", children: [_jsx("thead", { children: _jsxs("tr", { children: [_jsx("th", { children: "\u6863\u4F4D" }), _jsx("th", { children: "\u6E29\u5EA6" }), _jsx("th", { children: "\u6837\u672C" }), _jsx("th", { children: "\u4E2D\u4F4D\u6536\u76CA" }), _jsx("th", { children: "\u5747\u503C" }), _jsx("th", { children: "P10" }), _jsx("th", { children: "P25" }), _jsx("th", { children: "P75" }), _jsx("th", { children: "P90" }), _jsx("th", { children: "\u80DC\u7387" })] }) }), _jsx("tbody", { children: data.coarse_buckets.map((b) => (_jsxs("tr", { children: [_jsx("td", { children: _jsx("span", { style: {
                                                    background: TIER_COLOR[b.tier] ?? "#9ca3af",
                                                    color: "white", padding: "1px 8px",
                                                    borderRadius: 4, fontSize: 11,
                                                }, children: b.tier }) }), _jsx("td", { children: b.temp_range }), _jsx("td", { children: b.n_samples.toLocaleString() }), _jsx("td", { children: _jsxs("strong", { children: [b.median_return_pct ?? "—", "%"] }) }), _jsxs("td", { children: [b.mean_return_pct ?? "—", "%"] }), _jsxs("td", { children: [b.p10 ?? "—", "%"] }), _jsxs("td", { children: [b.p25 ?? "—", "%"] }), _jsxs("td", { children: [b.p75 ?? "—", "%"] }), _jsxs("td", { children: [b.p90 ?? "—", "%"] }), _jsxs("td", { children: [b.win_rate ?? "—", "%"] })] }, b.tier))) })] })] }), data.by_index_effectiveness.length > 0 && (_jsxs("section", { className: "settings-block", children: [_jsxs("h3", { children: ["\u6309\u6307\u6570\u5BF9\u6BD4\uFF08", data.by_index_effectiveness.length, " \u53EA \u2265 50 \u6837\u672C\uFF09"] }), _jsxs("p", { className: "hint", children: ["\u6309 |IC| \u964D\u5E8F \u2014 \u54EA\u4E9B\u6307\u6570\u7684\u6E29\u5EA6\u4FE1\u53F7\u6700\u6709\u6548\u3002", _jsx("strong", { children: "edge = \u9AD8\u6E29\u5EA6\u6876\u4E2D\u4F4D\u6536\u76CA \u2212 \u4F4E\u6E29\u5EA6\u6876\u4E2D\u4F4D\u6536\u76CA" }), "\uFF0C\u7406\u60F3\u4E3A\u8D1F \uFF08\u4F4E\u4F30\u65F6\u672A\u6765\u6DA8\u5F97\u6BD4\u9AD8\u4F30\u65F6\u591A\uFF09\u3002"] }), _jsxs("table", { className: "table", children: [_jsx("thead", { children: _jsxs("tr", { children: [_jsx("th", { children: "\u4EE3\u7801" }), _jsx("th", { children: "\u540D\u79F0" }), _jsx("th", { children: "\u6837\u672C\u6570" }), _jsx("th", { children: "Spearman IC" }), _jsxs("th", { children: ["\u4F4E\u4F30\u6876", _jsx("br", {}), "\u4E2D\u4F4D\u6536\u76CA"] }), _jsxs("th", { children: ["\u9AD8\u4F30\u6876", _jsx("br", {}), "\u4E2D\u4F4D\u6536\u76CA"] }), _jsxs("th", { children: ["edge", _jsx("br", {}), "\uFF08\u9AD8\u2212\u4F4E\uFF09"] })] }) }), _jsx("tbody", { children: data.by_index_effectiveness.map((b) => {
                                    const ic = b.spearman_ic ? parseFloat(b.spearman_ic) : null;
                                    const edge = b.edge_pct ? parseFloat(b.edge_pct) : null;
                                    const icColor = ic == null ? "#6b7280"
                                        : ic <= -0.05 ? "#15803d"
                                            : ic >= 0.05 ? "#dc2626"
                                                : "#6b7280";
                                    const edgeColor = edge == null ? "#6b7280"
                                        : edge < -2 ? "#15803d"
                                            : edge > 2 ? "#dc2626"
                                                : "#6b7280";
                                    return (_jsxs("tr", { children: [_jsx("td", { children: _jsx("strong", { children: b.code }) }), _jsx("td", { children: b.name }), _jsx("td", { children: b.n_samples.toLocaleString() }), _jsx("td", { style: { color: icColor, fontWeight: 600 }, children: ic != null ? ic.toFixed(4) : "—" }), _jsxs("td", { children: [b.low_temp_median_return ?? "—", "%"] }), _jsxs("td", { children: [b.high_temp_median_return ?? "—", "%"] }), _jsx("td", { style: { color: edgeColor, fontWeight: 600 }, children: edge != null ? `${edge > 0 ? "+" : ""}${edge.toFixed(2)}%` : "—" })] }, b.code));
                                }) })] })] }))] }));
}
