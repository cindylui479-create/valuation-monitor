import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { useState } from "react";
import { fetchIndexDetail } from "@/api/indices";
import { addToWatchlist, fetchWatchlist, removeFromWatchlist } from "@/api/watchlist";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { formatPercent, formatTemperature } from "@/utils/decimal";
import { isPriceFallback, temperatureColor, temperatureSourceLabel, tierLabel, } from "@/utils/temperature";
import PriceValuationChart from "./PriceValuationChart";
import PBChart from "./PBChart";
import ThresholdOverrideDialog from "./ThresholdOverrideDialog";
import DCAPlanEditor from "@/pages/DCA/DCAPlanEditor";
import { usePeSource } from "@/hooks/usePeSource";
const DIRECTION_LABEL = {
    STRONG_BUY: "强买入",
    BUY: "买入",
    SELL: "减持",
    STRONG_SELL: "强减持",
};
const DIRECTION_COLOR = {
    STRONG_BUY: "#15803d",
    BUY: "#22c55e",
    SELL: "#f87171",
    STRONG_SELL: "#b91c1c",
};
const directionColor = (d) => DIRECTION_COLOR[d] ?? "#9ca3af";
export default function IndexDetail() {
    const { code = "" } = useParams();
    const [dialogOpen, setDialogOpen] = useState(false);
    const [dcaOpen, setDcaOpen] = useState(false);
    const qc = useQueryClient();
    const peSource = usePeSource();
    const { data, isLoading, isError, error } = useQuery({
        queryKey: ["index-detail", code, peSource],
        queryFn: () => fetchIndexDetail(code, peSource),
        enabled: !!code,
    });
    const { data: watchlist } = useQuery({
        queryKey: ["watchlist", peSource],
        queryFn: () => fetchWatchlist(peSource),
    });
    const inWatchlist = watchlist?.find((w) => w.index_code === code && !w.tag);
    const addMutation = useMutation({
        mutationFn: () => addToWatchlist(code),
        onSuccess: () => qc.invalidateQueries({ queryKey: ["watchlist"] }),
    });
    const removeMutation = useMutation({
        mutationFn: () => removeFromWatchlist(inWatchlist.id),
        onSuccess: () => qc.invalidateQueries({ queryKey: ["watchlist"] }),
    });
    if (isLoading)
        return _jsx("div", { className: "state", children: "\u52A0\u8F7D\u4E2D\u2026" });
    if (isError)
        return _jsxs("div", { className: "state error", children: ["\u52A0\u8F7D\u5931\u8D25\uFF1A", error.message] });
    if (!data)
        return null;
    const v = data.latest_valuation;
    const pf = isPriceFallback(v?.temperature_source);
    return (_jsxs("div", { className: "detail", children: [_jsxs("header", { className: "detail-header", children: [_jsxs("div", { children: [_jsx(Link, { to: "/", className: "back-link", children: "\u2190 \u603B\u89C8" }), _jsxs("h1", { children: [data.name, _jsx("span", { className: "code", children: data.code })] }), _jsxs("p", { className: "meta", children: [data.market, " \u00B7 ", data.currency, " \u00B7 ", data.category, data.industry_raw && _jsxs(_Fragment, { children: [" \u00B7 ", data.industry_raw] }), data.data_window_note && (_jsxs("span", { className: "window-note", children: [" \u00B7 ", data.data_window_note] }))] })] }), _jsxs("div", { className: "detail-actions", children: [inWatchlist ? (_jsx("button", { className: "btn", onClick: () => removeMutation.mutate(), disabled: removeMutation.isPending, children: "\u4ECE\u81EA\u9009\u79FB\u9664" })) : (_jsx("button", { className: "btn btn-primary", onClick: () => addMutation.mutate(), disabled: addMutation.isPending, children: "\u52A0\u5165\u81EA\u9009" })), _jsx("button", { className: "btn", onClick: () => setDcaOpen(true), children: "\u52A0\u5165\u5B9A\u6295" }), _jsx("button", { className: "btn", onClick: () => setDialogOpen(true), children: "\u8BBE\u7F6E\u4E2A\u6027\u5316\u9608\u503C" }), _jsx("a", { className: "btn", href: `/api/v1/exports/index/${encodeURIComponent(code)}.csv?window=10y`, download: true, children: "\u4E0B\u8F7D CSV" })] })] }), pf && (_jsxs("div", { style: {
                    background: "#fef3c7", color: "#92400e",
                    padding: "10px 14px", borderRadius: 4, margin: "12px 0",
                    fontSize: 13, border: "1px solid #fde68a",
                }, children: ["\u26A0 ", _jsxs("strong", { children: ["\u8BE5\u6307\u6570\u6E29\u5EA6\u57FA\u4E8E\u4EF7\u683C\u5386\u53F2\u767E\u5206\u4F4D\uFF08", temperatureSourceLabel(v?.temperature_source), "\uFF09"] }), "\uFF0C \u975E PE-TTM \u4F30\u503C\u3002\u539F\u56E0\uFF1APE-TTM \u5386\u53F2\u6570\u636E\u70B9\u4E0D\u8DB3\uFF08< 250 \u5929\uFF09\u3002 \u542B\u4E49\uFF1A\u6E29\u5EA6\u9AD8 = \u6307\u6570\u70B9\u4F4D\u63A5\u8FD1\u81EA\u8EAB\u5386\u53F2\u9AD8\u4F4D\uFF0C", _jsx("strong", { children: "\u4E0D\u7B49\u4E8E\"\u4F30\u503C\u8D35\"" }), "\uFF08\u76C8\u5229\u53EF\u80FD\u540C\u6B65\u589E\u957F\uFF0C\u5206\u6BCD\u53D8\u5927\u53CD\u800C\u66F4\u4FBF\u5B9C\uFF09\u3002\u4E0E\u57FA\u91D1 NAV \u81EA\u6BD4\u540C\u53E3\u5F84\uFF0C\u8BF7\u8C28\u614E\u53C2\u8003\u3002"] })), (() => {
                // R7：temperature 为 null = 快照模式（港美股 PE 数据点 < 250）
                const isSnapshot = !v?.temperature;
                const latestQuote = data.quotes[data.quotes.length - 1];
                const latestPe = latestQuote?.pe_ttm;
                const latestPb = latestQuote?.pb;
                const latestDy = latestQuote?.dividend_yield;
                if (isSnapshot) {
                    return (_jsxs("section", { className: "latest-card snapshot-card", children: [_jsx("div", { className: "snapshot-badge", children: "\uD83D\uDCF7 \u5F53\u65E5\u5FEB\u7167" }), _jsxs("div", { className: "stat", children: [_jsx("div", { className: "label", children: "PE-TTM" }), _jsx("div", { className: "value", children: latestPe ? parseFloat(latestPe).toFixed(2) : "—" })] }), _jsxs("div", { className: "stat", children: [_jsx("div", { className: "label", children: "PB" }), _jsx("div", { className: "value", children: latestPb ? parseFloat(latestPb).toFixed(2) : "—" })] }), _jsxs("div", { className: "stat", children: [_jsx("div", { className: "label", children: "\u80A1\u606F\u7387" }), _jsx("div", { className: "value", children: formatPercent(latestDy, 2) })] }), _jsxs("div", { className: "stat", children: [_jsx("div", { className: "label", children: "\u5B9E\u9645\u884C\u60C5\u5386\u53F2" }), _jsxs("div", { className: "value", children: [data.actual_history_years.toFixed(1), " \u5E74"] })] })] }));
                }
                const ls = data.latest_signal;
                return (_jsxs("section", { className: "latest-card", children: [_jsx("div", { className: "tier-pill", style: { backgroundColor: temperatureColor(v.temperature) }, children: tierLabel(v.tier) }), _jsxs("div", { className: "stat", children: [_jsx("div", { className: "label", children: "\u6E29\u5EA6" }), _jsx("div", { className: "value", children: formatTemperature(v.temperature) })] }), _jsxs("div", { className: "stat", children: [_jsx("div", { className: "label", children: "PE-TTM 10y \u5206\u4F4D" }), _jsx("div", { className: "value", children: formatPercent(v.pe_percentile) })] }), _jsxs("div", { className: "stat", children: [_jsx("div", { className: "label", children: "PB 10y \u5206\u4F4D" }), _jsx("div", { className: "value", children: formatPercent(v.pb_percentile) })] }), _jsxs("div", { className: "stat", children: [_jsx("div", { className: "label", children: "\u5B9E\u9645\u5386\u53F2" }), _jsxs("div", { className: "value", children: [data.actual_history_years.toFixed(1), " \u5E74"] })] }), ls && (_jsxs("div", { className: "stat current-signal", children: [_jsxs("div", { className: "label", children: ["\u5F53\u524D\u4FE1\u53F7 (", ls.date, ")"] }), _jsx("div", { className: "value", children: _jsx("span", { className: "tier-badge", style: { backgroundColor: directionColor(ls.direction) }, children: DIRECTION_LABEL[ls.direction] }) })] }))] }));
            })(), _jsx("section", { className: "chart-block", children: _jsx(PriceValuationChart, { quotes: data.quotes, valuations: data.valuation_series, title: v?.temperature ? "价格 + PE-TTM（含 10y 百分位带）" : "价格历史" }) }), v?.temperature && (_jsx("section", { className: "chart-block", children: _jsx(PBChart, { quotes: data.quotes }) })), _jsxs("section", { className: "funds-block", children: [_jsx("h3", { children: "\u8DDF\u8E2A\u57FA\u91D1 / ETF" }), data.funds.length === 0 ? (_jsx("p", { className: "empty", children: "\u6682\u65E0\u8DDF\u8E2A\u57FA\u91D1" })) : (_jsxs("table", { className: "table", children: [_jsx("thead", { children: _jsxs("tr", { children: [_jsx("th", { children: "\u4EE3\u7801" }), _jsx("th", { children: "\u540D\u79F0" }), _jsx("th", { children: "\u7C7B\u578B" }), _jsx("th", { children: "\u8D39\u7387" }), _jsx("th", { children: "\u5907\u6CE8" })] }) }), _jsx("tbody", { children: data.funds.map((f) => (_jsxs("tr", { children: [_jsx("td", { children: f.code }), _jsx("td", { children: f.name }), _jsx("td", { children: f.type }), _jsx("td", { children: formatPercent(f.fee_rate, 2) }), _jsx("td", { children: f.tracking_error_note ?? "—" })] }, f.code))) })] }))] }), data.signal_history.length > 0 && (_jsxs("section", { className: "signal-timeline", children: [_jsxs("h3", { children: ["\u4FE1\u53F7\u5386\u53F2 (", data.signal_history.length, ")"] }), _jsx("ul", { children: data.signal_history.slice(0, 50).map((s, i) => (_jsxs("li", { children: [_jsx("span", { className: "date", children: s.date }), _jsx("span", { className: "tier-badge", style: { backgroundColor: directionColor(s.direction) }, children: DIRECTION_LABEL[s.direction] }), _jsx("span", { className: "tier-text", children: s.tier }), _jsxs("span", { className: "temp", children: ["\u6E29\u5EA6 ", parseFloat(s.temperature).toFixed(1)] })] }, i))) })] })), _jsx(ThresholdOverrideDialog, { open: dialogOpen, indexCode: code, onClose: () => setDialogOpen(false) }), _jsx(DCAPlanEditor, { open: dcaOpen, presetIndexCode: code, onClose: () => setDcaOpen(false) })] }));
}
