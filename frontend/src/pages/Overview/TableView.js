import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { Link } from "react-router-dom";
import { useState } from "react";
import { formatNumber, formatPercent, formatTemperature } from "@/utils/decimal";
import { isPriceFallback, temperatureColor, tierLabel } from "@/utils/temperature";
const num = (s) => (s == null || s === "" ? null : parseFloat(s));
export default function TableView({ indices }) {
    const [sortKey, setSortKey] = useState("temperature");
    const [sortDir, setSortDir] = useState("asc");
    const toggleSort = (key) => {
        if (sortKey === key)
            setSortDir(sortDir === "asc" ? "desc" : "asc");
        else {
            setSortKey(key);
            setSortDir("asc");
        }
    };
    const sorted = [...indices].sort((a, b) => {
        const get = (x) => {
            switch (sortKey) {
                case "name": return x.name;
                case "tier": return x.tier ?? null;
                case "temperature": return num(x.temperature);
                case "pe_ttm": return num(x.pe_ttm);
                case "pe_pct": return num(x.pe_percentile_10y);
                case "pb_pct": return num(x.pb_percentile_10y);
                case "dy": return num(x.dividend_yield);
            }
        };
        const va = get(a);
        const vb = get(b);
        if (va == null && vb == null)
            return 0;
        if (va == null)
            return 1;
        if (vb == null)
            return -1;
        const cmp = typeof va === "number" && typeof vb === "number"
            ? va - vb
            : String(va).localeCompare(String(vb));
        return sortDir === "asc" ? cmp : -cmp;
    });
    const Arrow = ({ k }) => sortKey === k ? _jsx("span", { className: "sort-arrow", children: sortDir === "asc" ? " ▲" : " ▼" }) : null;
    return (_jsxs("table", { className: "table sortable", children: [_jsx("thead", { children: _jsxs("tr", { children: [_jsxs("th", { onClick: () => toggleSort("name"), children: ["\u6307\u6570", _jsx(Arrow, { k: "name" })] }), _jsxs("th", { onClick: () => toggleSort("tier"), children: ["\u6863\u4F4D", _jsx(Arrow, { k: "tier" })] }), _jsxs("th", { onClick: () => toggleSort("temperature"), children: ["\u6E29\u5EA6", _jsx(Arrow, { k: "temperature" })] }), _jsxs("th", { onClick: () => toggleSort("pe_ttm"), children: ["PE", _jsx(Arrow, { k: "pe_ttm" })] }), _jsxs("th", { onClick: () => toggleSort("pe_pct"), children: ["PE 10y%", _jsx(Arrow, { k: "pe_pct" })] }), _jsxs("th", { onClick: () => toggleSort("pb_pct"), children: ["PB 10y%", _jsx(Arrow, { k: "pb_pct" })] }), _jsxs("th", { onClick: () => toggleSort("dy"), children: ["\u80A1\u606F\u7387", _jsx(Arrow, { k: "dy" })] })] }) }), _jsx("tbody", { children: sorted.map((idx) => {
                    const isSnapshot = idx.temperature == null;
                    return (_jsxs("tr", { children: [_jsx("td", { children: _jsxs(Link, { to: `/indices/${encodeURIComponent(idx.code)}`, children: [_jsx("div", { className: "cell-name", children: idx.name }), _jsx("div", { className: "cell-code", children: idx.code })] }) }), _jsx("td", { children: _jsx("span", { className: "tier-badge", style: { backgroundColor: temperatureColor(idx.temperature) }, children: tierLabel(idx.tier) }) }), _jsxs("td", { children: [formatTemperature(idx.temperature), isPriceFallback(idx.temperature_source) && (_jsx("span", { title: "\u4EF7\u683C\u81EA\u6BD4\uFF08PE \u5386\u53F2\u4E0D\u8DB3\u65F6 fallback\uFF1B\u4E0E\u57FA\u91D1 NAV \u81EA\u6BD4\u540C\u53E3\u5F84\uFF0C\u4E0D\u53CD\u6620\u4F30\u503C\uFF09", style: { marginLeft: 4, color: "#d97706", cursor: "help" }, children: "\u26A0" }))] }), _jsxs("td", { children: [formatNumber(idx.pe_ttm), isSnapshot && idx.pe_ttm && (_jsx("span", { className: "pill-now", title: "\u5F53\u524D\u5FEB\u7167\u503C\uFF0C\u65E0\u5386\u53F2\u5206\u4F4D", children: "\u5F53\u524D" }))] }), _jsx("td", { children: formatPercent(idx.pe_percentile_10y) }), _jsx("td", { children: formatPercent(idx.pb_percentile_10y) }), _jsx("td", { children: formatPercent(idx.dividend_yield, 2) })] }, idx.code));
                }) })] }));
}
