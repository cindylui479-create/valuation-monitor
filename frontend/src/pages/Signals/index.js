import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { useState } from "react";
import { fetchSignals, fetchTodaySignals } from "@/api/signals";
import { formatTemperature } from "@/utils/decimal";
import { temperatureColor } from "@/utils/temperature";
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
export default function Signals() {
    const [tab, setTab] = useState("today");
    const [onlySubscribed, setOnlySubscribed] = useState(false);
    const peSource = usePeSource();
    const todayQuery = useQuery({
        queryKey: ["signals", "today", onlySubscribed, peSource],
        queryFn: () => fetchTodaySignals(onlySubscribed, peSource),
        enabled: tab === "today",
    });
    const historyQuery = useQuery({
        queryKey: ["signals", "history", onlySubscribed, peSource],
        queryFn: () => fetchSignals({
            only_subscribed: onlySubscribed,
            limit: 200,
            pe_source: peSource,
        }),
        enabled: tab === "history",
    });
    const data = tab === "today" ? todayQuery.data : historyQuery.data;
    return (_jsxs("div", { className: "signals-page", children: [_jsxs("div", { className: "page-header", children: [_jsx("h2", { children: "\u4F30\u503C\u4FE1\u53F7" }), _jsxs("div", { className: "controls", children: [_jsxs("div", { className: "view-toggle", children: [_jsx("button", { className: tab === "today" ? "active" : "", onClick: () => setTab("today"), children: "\u4ECA\u65E5" }), _jsx("button", { className: tab === "history" ? "active" : "", onClick: () => setTab("history"), children: "\u5386\u53F2" })] }), _jsxs("label", { className: "check", children: [_jsx("input", { type: "checkbox", checked: onlySubscribed, onChange: (e) => setOnlySubscribed(e.target.checked) }), "\u4EC5\u663E\u793A\u81EA\u9009/\u5B9A\u6295\u76F8\u5173"] })] })] }), (todayQuery.isLoading || historyQuery.isLoading) && (_jsx("div", { className: "state", children: "\u52A0\u8F7D\u4E2D\u2026" })), data && data.items.length === 0 && (_jsxs("div", { className: "state", children: [_jsx("p", { children: tab === "today" ? "今日无信号" : "暂无历史信号" }), tab === "today" && (_jsx("p", { className: "hint", children: "\u4FE1\u53F7\u5728\u6BCF\u65E5\u6279\u5904\u7406\u540E\u751F\u6210\u3002A \u80A1 16:30 / \u6E2F\u80A1 17:30 / \u7F8E\u80A1 \u6B21\u65E5 07:00\u3002" }))] })), data && data.items.length > 0 && (_jsxs("table", { className: "table", children: [_jsx("thead", { children: _jsxs("tr", { children: [_jsx("th", { children: "\u65E5\u671F" }), _jsx("th", { children: "\u5E02\u573A" }), _jsx("th", { children: "\u6307\u6570" }), _jsx("th", { children: "\u65B9\u5411" }), _jsx("th", { children: "\u6863\u4F4D" }), _jsx("th", { children: "\u6E29\u5EA6" })] }) }), _jsx("tbody", { children: data.items.map((s) => (_jsxs("tr", { children: [_jsx("td", { children: s.date }), _jsx("td", { children: s.market }), _jsx("td", { children: _jsxs(Link, { to: `/indices/${encodeURIComponent(s.index_code)}`, children: [_jsx("div", { className: "cell-name", children: s.index_name }), _jsx("div", { className: "cell-code", children: s.index_code })] }) }), _jsx("td", { children: _jsx("span", { className: "tier-badge", style: { backgroundColor: DIRECTION_COLOR[s.direction] }, children: DIRECTION_LABEL[s.direction] }) }), _jsx("td", { children: _jsx("span", { className: "tier-badge", style: { backgroundColor: temperatureColor(s.temperature) }, children: s.tier }) }), _jsx("td", { children: formatTemperature(s.temperature) })] }, s.id))) })] }))] }));
}
