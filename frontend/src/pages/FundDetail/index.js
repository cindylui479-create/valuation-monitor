import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { useMemo } from "react";
import ReactECharts from "@/components/charts/ReactECharts";
import { fetchFundDetail } from "@/api/funds";
import { temperatureColor, tierLabel } from "@/utils/temperature";
export default function FundDetail() {
    const { code = "" } = useParams();
    const { data, isLoading, error } = useQuery({
        queryKey: ["fund-detail", code],
        queryFn: () => fetchFundDetail(code),
        enabled: !!code,
    });
    const navChartOption = useMemo(() => {
        if (!data || data.nav_history.length === 0)
            return null;
        const dates = data.nav_history.map((n) => n.date);
        const navs = data.nav_history.map((n) => parseFloat(n.nav));
        const sortedNavs = [...navs].sort((a, b) => a - b);
        const q = (p) => {
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
    if (isLoading)
        return _jsx("div", { className: "state", children: "\u52A0\u8F7D\u4E2D\u2026" });
    if (error)
        return _jsxs("div", { className: "state error", children: ["\u52A0\u8F7D\u5931\u8D25\uFF1A", error.message] });
    if (!data)
        return null;
    const v = data.latest_valuation;
    const latestNav = data.nav_history[data.nav_history.length - 1];
    return (_jsxs("div", { className: "detail", children: [_jsx("header", { className: "detail-header", children: _jsxs("div", { children: [_jsx(Link, { to: "/watchlist", className: "back-link", children: "\u2190 \u81EA\u9009" }), _jsxs("h1", { children: [data.name, _jsx("span", { className: "code", children: data.code })] }), _jsxs("p", { className: "meta", children: ["\u4E3B\u52A8\u57FA\u91D1 \u00B7 ", data.market, " \u00B7 CNY", data.fund_manager && _jsxs(_Fragment, { children: [" \u00B7 \u57FA\u91D1\u7ECF\u7406 ", data.fund_manager] }), data.setup_date && _jsxs(_Fragment, { children: [" \u00B7 \u6210\u7ACB ", data.setup_date] }), data.data_window_note && (_jsxs("span", { className: "window-note", children: [" \u00B7 ", data.data_window_note] }))] })] }) }), _jsxs("div", { style: {
                    background: "#fef3c7", color: "#92400e",
                    padding: "8px 12px", borderRadius: 4, margin: "12px 0",
                    fontSize: 13,
                }, children: ["\u26A0 ", _jsx("strong", { children: "\u4E3B\u52A8\u57FA\u91D1\u4F30\u503C\u53E3\u5F84\uFF1ANAV 5 \u5E74\u5386\u53F2\u767E\u5206\u4F4D" }), "\u3002 \u4EC5\u53CD\u6620\"\u57FA\u91D1\u51C0\u503C\u4E0E\u81EA\u8EAB\u5386\u53F2\u6BD4\"\uFF0C", _jsx("strong", { children: "\u4E0D\u53CD\u6620\u6301\u4ED3\u6C34\u4F4D" }), "\uFF08\u5B63\u62A5\u62AB\u9732 70% \u6301\u4ED3\u4E14\u6EDE\u540E\uFF0C\u672A\u63A5\u5165\uFF09\u3002 \u57FA\u91D1\u7ECF\u7406\u98CE\u683C\u6F02\u79FB\u3001\u6301\u4ED3\u6362\u624B\u7B49\u56E0\u7D20\u4E5F\u672A\u8003\u8651\u3002"] }), _jsxs("section", { className: "latest-card", children: [v?.temperature && (_jsx("div", { className: "tier-pill", style: { backgroundColor: temperatureColor(v.temperature) }, children: v.tier ? tierLabel(v.tier) : "—" })), _jsxs("div", { className: "stat", children: [_jsx("div", { className: "label", children: "\u6E29\u5EA6\uFF08NAV 5y \u951A\uFF09" }), _jsx("div", { className: "value", children: v?.temperature ? parseFloat(v.temperature).toFixed(1) : "—" })] }), _jsxs("div", { className: "stat", children: [_jsx("div", { className: "label", children: "\u6700\u65B0 NAV" }), _jsx("div", { className: "value", children: latestNav ? parseFloat(latestNav.nav).toFixed(4) : "—" })] }), _jsxs("div", { className: "stat", children: [_jsx("div", { className: "label", children: "NAV 5y \u5206\u4F4D" }), _jsx("div", { className: "value", children: v?.nav_percentile ? (parseFloat(v.nav_percentile) * 100).toFixed(1) + "%" : "—" })] }), _jsxs("div", { className: "stat", children: [_jsx("div", { className: "label", children: "\u5B9E\u9645\u5386\u53F2" }), _jsxs("div", { className: "value", children: [data.actual_history_years.toFixed(1), " \u5E74"] })] })] }), navChartOption && (_jsxs("section", { className: "chart-block", children: [_jsx("h3", { style: { margin: 0 }, children: "NAV \u5386\u53F2\uFF08\u542B 5y \u767E\u5206\u4F4D\u5E26\uFF09" }), _jsx(ReactECharts, { option: navChartOption, style: { height: 420 } })] })), _jsxs("section", { className: "signal-timeline", children: [_jsxs("h3", { children: ["\u5206\u4F4D\u5386\u53F2\uFF08", data.valuation_series.length, " \u884C 5y \u7A97\u53E3\uFF09"] }), data.valuation_series.length === 0 ? (_jsx("p", { className: "empty", children: "\u5206\u4F4D\u5E8F\u5217\u5C1A\u672A\u751F\u6210" })) : (_jsx("ul", { children: data.valuation_series.slice(-30).reverse().map((p) => (_jsxs("li", { children: [_jsx("span", { className: "date", children: p.date }), _jsxs("span", { className: "temp", children: ["\u6E29\u5EA6 ", p.temperature ? parseFloat(p.temperature).toFixed(1) : "—"] }), _jsx("span", { className: "tier-text", children: p.tier ?? "—" }), _jsxs("span", { style: { color: "#6b7280", fontSize: 11 }, children: ["NAV \u5206\u4F4D ", p.nav_percentile ? (parseFloat(p.nav_percentile) * 100).toFixed(1) + "%" : "—"] })] }, p.date))) }))] })] }));
}
