import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { fetchStockDetail, updateStockAnchor, } from "@/api/stocks";
import { temperatureColor, tierLabel } from "@/utils/temperature";
import PriceValuationChart from "@/pages/IndexDetail/PriceValuationChart";
const ANCHOR_LABEL = {
    PE: "PE-TTM",
    PB: "市净率 (PB)",
    PS: "市销率 (PS)",
    PE_REVERSE: "PE 倒置（周期股）",
    DIV_YIELD: "股息率倒置",
};
const ANCHOR_HINT = {
    PE: "高 PE 百分位 = 高估值",
    PB: "高 PB 百分位 = 高估值（适用于银行/地产）",
    PS: "高 PS 百分位 = 高估值（适用于互联网/早期科技）",
    PE_REVERSE: "PE 低 = 周期顶部 = 高估；适用于钢铁/煤炭/化工等",
    DIV_YIELD: "股息率低 = 高估；适用于公用事业/交通运输",
};
export default function StockDetail() {
    const { code = "" } = useParams();
    const qc = useQueryClient();
    const { data, isLoading, error } = useQuery({
        queryKey: ["stock-detail", code],
        queryFn: () => fetchStockDetail(code),
        enabled: !!code,
    });
    const anchorMut = useMutation({
        mutationFn: (anchor) => updateStockAnchor(code, anchor),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ["stock-detail", code] });
            qc.invalidateQueries({ queryKey: ["stocks"] });
        },
    });
    if (isLoading)
        return _jsx("div", { className: "state", children: "\u52A0\u8F7D\u4E2D\u2026" });
    if (error)
        return _jsxs("div", { className: "state error", children: ["\u52A0\u8F7D\u5931\u8D25\uFF1A", error.message] });
    if (!data)
        return null;
    const v = data.latest_valuation;
    const latestQuote = data.quotes[data.quotes.length - 1];
    return (_jsxs("div", { className: "detail", children: [_jsx("header", { className: "detail-header", children: _jsxs("div", { children: [_jsx(Link, { to: "/watchlist", className: "back-link", children: "\u2190 \u81EA\u9009" }), _jsxs("h1", { children: [data.name, _jsx("span", { className: "code", children: data.code })] }), _jsxs("p", { className: "meta", children: ["A \u80A1 \u00B7 CNY \u00B7 \u4E2A\u80A1", data.industry && _jsxs(_Fragment, { children: [" \u00B7 ", data.industry] }), data.listing_date && _jsxs(_Fragment, { children: [" \u00B7 \u4E0A\u5E02 ", data.listing_date] }), data.data_window_note && (_jsxs("span", { className: "window-note", children: [" \u00B7 ", data.data_window_note] }))] })] }) }), _jsxs("section", { className: "latest-card", children: [v?.temperature && (_jsx("div", { className: "tier-pill", style: { backgroundColor: temperatureColor(v.temperature) }, children: v.tier ? tierLabel(v.tier) : "—" })), _jsxs("div", { className: "stat", children: [_jsxs("div", { className: "label", children: ["\u6E29\u5EA6\uFF08", ANCHOR_LABEL[data.anchor] ?? data.anchor, " \u951A\uFF09"] }), _jsx("div", { className: "value", children: v?.temperature ? parseFloat(v.temperature).toFixed(1) : "—" })] }), _jsxs("div", { className: "stat", children: [_jsx("div", { className: "label", children: "PE-TTM" }), _jsx("div", { className: "value", children: latestQuote?.pe_ttm ? parseFloat(latestQuote.pe_ttm).toFixed(2) : "—" })] }), _jsxs("div", { className: "stat", children: [_jsx("div", { className: "label", children: "PB" }), _jsx("div", { className: "value", children: latestQuote?.pb ? parseFloat(latestQuote.pb).toFixed(2) : "—" })] }), _jsxs("div", { className: "stat", children: [_jsx("div", { className: "label", children: "PS-TTM" }), _jsx("div", { className: "value", children: latestQuote?.ps_ttm ? parseFloat(latestQuote.ps_ttm).toFixed(2) : "—" })] }), _jsxs("div", { className: "stat", children: [_jsx("div", { className: "label", children: "\u5B9E\u9645\u5386\u53F2" }), _jsxs("div", { className: "value", children: [data.actual_history_years.toFixed(1), " \u5E74"] })] })] }), _jsx("section", { className: "settings-block", children: _jsxs("label", { className: "field horizontal", style: { display: "flex", alignItems: "center", gap: 12 }, children: [_jsx("span", { style: { minWidth: 100 }, children: "\u4F30\u503C\u951A\uFF08SRS R12\uFF09" }), _jsx("select", { value: data.anchor, onChange: (e) => anchorMut.mutate(e.target.value), disabled: anchorMut.isPending, children: data.available_anchors.map((a) => (_jsx("option", { value: a, children: ANCHOR_LABEL[a] ?? a }, a))) }), _jsx("span", { className: "hint", style: { margin: 0 }, children: ANCHOR_HINT[data.anchor] })] }) }), _jsx("section", { className: "chart-block", children: _jsx(PriceValuationChart, { quotes: data.quotes, title: "\u4EF7\u683C + PE-TTM \u5386\u53F2\uFF0810y \u5206\u4F4D\u5E26\uFF09" }) }), _jsxs("section", { className: "signal-timeline", children: [_jsxs("h3", { children: ["\u5206\u4F4D\u5386\u53F2\uFF08", data.valuation_series.length, " \u884C 10y \u7A97\u53E3\uFF09"] }), data.valuation_series.length === 0 ? (_jsx("p", { className: "empty", children: "\u5206\u4F4D\u5E8F\u5217\u5C1A\u672A\u751F\u6210" })) : (_jsx("ul", { children: data.valuation_series.slice(-30).reverse().map((p) => (_jsxs("li", { children: [_jsx("span", { className: "date", children: p.date }), _jsxs("span", { className: "temp", children: ["\u6E29\u5EA6 ", p.temperature ? parseFloat(p.temperature).toFixed(1) : "—"] }), _jsx("span", { className: "tier-text", children: p.tier ?? "—" }), _jsxs("span", { style: { color: "#6b7280", fontSize: 11 }, children: ["PE \u5206\u4F4D ", p.pe_percentile ? (parseFloat(p.pe_percentile) * 100).toFixed(1) + "%" : "—", " · ", "PB \u5206\u4F4D ", p.pb_percentile ? (parseFloat(p.pb_percentile) * 100).toFixed(1) + "%" : "—"] })] }, p.date))) }))] })] }));
}
