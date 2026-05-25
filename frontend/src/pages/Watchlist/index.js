import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { useState } from "react";
import { fetchWatchlist, removeFromWatchlist } from "@/api/watchlist";
import { usePeSource } from "@/hooks/usePeSource";
import { isPriceFallback, temperatureColor, temperatureSourceLabel, tierLabel, } from "@/utils/temperature";
import StockListSection from "./StockListSection";
import FundListSection from "./FundListSection";
export default function Watchlist() {
    const [tab, setTab] = useState("INDEX");
    return (_jsxs("div", { className: "watchlist-page", children: [_jsx("h2", { children: "\u81EA\u9009" }), _jsxs("div", { className: "view-toggle", style: { marginBottom: 16 }, children: [_jsx("button", { className: tab === "INDEX" ? "active" : "", onClick: () => setTab("INDEX"), children: "\u6307\u6570" }), _jsx("button", { className: tab === "STOCK" ? "active" : "", onClick: () => setTab("STOCK"), children: "A \u80A1\u4E2A\u80A1" }), _jsx("button", { className: tab === "FUND" ? "active" : "", onClick: () => setTab("FUND"), children: "\u57FA\u91D1" })] }), tab === "INDEX" && _jsx(IndexList, {}), tab === "STOCK" && _jsx(StockListSection, {}), tab === "FUND" && _jsx(FundListSection, {})] }));
}
function IndexList() {
    const qc = useQueryClient();
    const peSource = usePeSource();
    const { data, isLoading } = useQuery({
        queryKey: ["watchlist", peSource],
        queryFn: () => fetchWatchlist(peSource),
    });
    const removeMut = useMutation({
        mutationFn: (id) => removeFromWatchlist(id),
        onSuccess: () => qc.invalidateQueries({ queryKey: ["watchlist"] }),
    });
    if (isLoading)
        return _jsx("p", { className: "empty", children: "\u52A0\u8F7D\u4E2D\u2026" });
    if (!data || data.length === 0) {
        return (_jsxs("div", { className: "state", children: [_jsx("p", { children: "\u6682\u65E0\u81EA\u9009\u6307\u6570\u3002\u524D\u5F80\u603B\u89C8\u9875\u70B9\u51FB\"\u52A0\u5165\u81EA\u9009\"\uFF0C\u6216\u5728\u8BE6\u60C5\u9875\u5E95\u90E8\u6DFB\u52A0\u3002" }), _jsx(Link, { to: "/", children: "\u56DE\u5230\u603B\u89C8" })] }));
    }
    // 按市场分组（与基金 Tab 视觉一致）
    const byMarket = {};
    for (const w of data) {
        const mkt = w.market ?? "?";
        (byMarket[mkt] = byMarket[mkt] ?? []).push(w);
    }
    return (_jsxs("div", { children: [_jsxs("p", { className: "hint", style: { marginBottom: 12 }, children: ["\u5171 ", data.length, " \u53EA\u81EA\u9009\u6307\u6570\uFF0C\u6E29\u5EA6\u6309\u5F53\u524D ", _jsxs("code", { children: ["pe_source=", peSource] }), " \u53D6\uFF08Settings \u5168\u5C40\u5207\u6362 LG/CSI\uFF09\u3002 \u70B9\u51FB\u4EE3\u7801\u8FDB\u5165\u8BE6\u60C5\u9875\u67E5\u770B\u5B8C\u6574\u56FE\u8868\u4E0E\u5386\u53F2\u4FE1\u53F7\u3002"] }), ["A", "HK", "US"].map((mkt) => {
                const arr = byMarket[mkt] ?? [];
                if (arr.length === 0)
                    return null;
                return (_jsxs("section", { className: "settings-block", children: [_jsxs("h3", { children: [mkt, " \u5E02\u573A\uFF08", arr.length, "\uFF09"] }), _jsxs("table", { className: "table", children: [_jsx("thead", { children: _jsxs("tr", { children: [_jsx("th", { children: "\u4EE3\u7801" }), _jsx("th", { children: "\u540D\u79F0" }), _jsx("th", { children: "\u7C7B\u522B" }), _jsx("th", { children: "\u6807\u7B7E" }), _jsx("th", { children: "\u6E29\u5EA6" }), _jsx("th", { children: "\u6863\u4F4D" }), _jsx("th", { children: "PE-TTM" }), _jsx("th", { children: "PB" }), _jsx("th", { children: "\u80A1\u606F\u7387" }), _jsx("th", { children: "\u53E3\u5F84" }), _jsx("th", { children: "\u5386\u53F2" }), _jsx("th", {})] }) }), _jsx("tbody", { children: arr.map((w) => {
                                        const temp = w.temperature ? parseFloat(w.temperature) : null;
                                        const dy = w.dividend_yield ? parseFloat(w.dividend_yield) : null;
                                        const pf = isPriceFallback(w.temperature_source);
                                        return (_jsxs("tr", { children: [_jsx("td", { children: _jsx(Link, { to: `/indices/${encodeURIComponent(w.index_code)}`, children: _jsx("strong", { children: w.index_code }) }) }), _jsx("td", { children: w.index_name }), _jsx("td", { children: w.category && (_jsx("span", { style: {
                                                            fontSize: 11, padding: "1px 6px",
                                                            background: "#e0f2fe", color: "#075985",
                                                            borderRadius: 4,
                                                        }, children: w.category })) }), _jsx("td", { children: w.tag ?? "—" }), _jsx("td", { children: temp != null ? (_jsxs(_Fragment, { children: [_jsx("span", { style: {
                                                                    background: temperatureColor(temp.toString()),
                                                                    color: "white", padding: "1px 8px",
                                                                    borderRadius: 4, fontSize: 11,
                                                                }, children: temp.toFixed(1) }), pf && (_jsx("span", { title: "\u4EF7\u683C\u81EA\u6BD4\uFF08PE \u5386\u53F2\u4E0D\u8DB3\u65F6 fallback\uFF0C\u4E0E\u57FA\u91D1 NAV \u81EA\u6BD4\u540C\u53E3\u5F84\uFF0C\u4E0D\u53CD\u6620\u4F30\u503C\uFF09", style: { marginLeft: 4, color: "#d97706", fontSize: 11, cursor: "help" }, children: "\u26A0" }))] })) : "—" }), _jsx("td", { children: w.tier ? tierLabel(w.tier) : "—" }), _jsx("td", { children: w.pe_ttm ? parseFloat(w.pe_ttm).toFixed(2) : "—" }), _jsx("td", { children: w.pb ? parseFloat(w.pb).toFixed(2) : "—" }), _jsx("td", { children: dy != null ? (dy * 100).toFixed(2) + "%" : "—" }), _jsx("td", { style: { fontSize: 11, color: pf ? "#d97706" : "#6b7280" }, children: w.temperature_source
                                                        ? temperatureSourceLabel(w.temperature_source)
                                                        : (w.valuation_source ?? "—") }), _jsxs("td", { style: { whiteSpace: "nowrap" }, children: [w.actual_history_years != null ? w.actual_history_years.toFixed(1) + "y" : "—", w.data_window_note && (_jsx("span", { title: w.data_window_note, style: { marginLeft: 4, color: "#d97706", fontSize: 11 }, children: "\u24D8" }))] }), _jsx("td", { children: _jsx("button", { className: "btn", onClick: () => {
                                                            if (confirm(`确认从自选移除 ${w.index_code} ${w.index_name}？`)) {
                                                                removeMut.mutate(w.id);
                                                            }
                                                        }, disabled: removeMut.isPending, style: { fontSize: 11, padding: "2px 6px" }, children: "\u79FB\u9664" }) })] }, w.id));
                                    }) })] })] }, mkt));
            })] }));
}
