import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { useMemo, useState } from "react";
import { fetchEffectiveness } from "@/api/effectiveness";
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
    // SIG-1：拉 365 天 horizon 的实证数据，给每条信号附"该档位 1 年历史参考"
    const effQuery = useQuery({
        queryKey: ["effectiveness", 365, 10, ""],
        queryFn: () => fetchEffectiveness(365, 10),
        staleTime: 60 * 60_000, // 1 小时缓存，避免每次进页面重算 2.4 万样本
    });
    const tierStats = useMemo(() => {
        const map = new Map();
        for (const b of effQuery.data?.coarse_buckets ?? []) {
            if (b.median_return_pct != null && b.win_rate != null) {
                map.set(b.tier, {
                    median: parseFloat(b.median_return_pct),
                    winRate: parseFloat(b.win_rate),
                    n: b.n_samples,
                });
            }
        }
        return map;
    }, [effQuery.data]);
    return (_jsxs("div", { className: "signals-page", children: [_jsxs("div", { className: "page-header", children: [_jsxs("h2", { children: ["\u4F30\u503C\u4FE1\u53F7", _jsx(Link, { to: "/temperature/effectiveness", style: {
                                    fontSize: 13, marginLeft: 16,
                                    color: "#2563eb", textDecoration: "none",
                                }, children: "\uD83D\uDCCA \u6E29\u5EA6\u6709\u6548\u6027 \u2192" })] }), _jsxs("div", { className: "controls", children: [_jsxs("div", { className: "view-toggle", children: [_jsx("button", { className: tab === "today" ? "active" : "", onClick: () => setTab("today"), children: "\u4ECA\u65E5" }), _jsx("button", { className: tab === "history" ? "active" : "", onClick: () => setTab("history"), children: "\u5386\u53F2" })] }), _jsxs("label", { className: "check", children: [_jsx("input", { type: "checkbox", checked: onlySubscribed, onChange: (e) => setOnlySubscribed(e.target.checked) }), "\u4EC5\u663E\u793A\u81EA\u9009/\u5B9A\u6295\u76F8\u5173"] })] })] }), _jsxs("div", { style: {
                    background: "#eff6ff", border: "1px solid #bfdbfe", color: "#1e40af",
                    padding: "10px 14px", borderRadius: 4, marginBottom: 12, fontSize: 13,
                }, children: ["\uD83D\uDCD0 ", _jsx("strong", { children: "\u4FE1\u53F7\u662F\"\u7EA6 1 \u5E74\u89C6\u89D2\"\u7684\u4F30\u503C\u4FE1\u53F7\uFF0C\u4E0D\u662F\u77ED\u7EBF\u62E9\u65F6\u3002" }), "\u672C\u5DE5\u5177 10 \u5E74\u5B9E\u8BC1\uFF082.4 \u4E07\u6837\u672C\uFF09\uFF1A90 \u5929\u5185\u5E02\u573A\u52A8\u91CF\u4E3B\u5BFC\uFF0C\u4F4E\u4F30\u53EF\u4EE5\u66F4\u4F4E\u4F30\u3001 \u9AD8\u4F30\u5E38\u7EE7\u7EED\u4E0A\u6DA8\uFF1B\u6E29\u5EA6\u7684\u9884\u6D4B\u529B\u5728\u7EA6 1 \u5E74 horizon \u624D\u663E\u73B0 \uFF08", _jsx(Link, { to: "/temperature/effectiveness", style: { color: "#1e40af", fontWeight: 600 }, children: "\u67E5\u770B\u5B8C\u6574\u5B9E\u8BC1 \u2192" }), "\uFF09\u3002 \u8868\u4E2D\"1 \u5E74\u5386\u53F2\u53C2\u8003\"\u5217 = \u5386\u53F2\u4E0A\u5904\u4E8E\u8BE5\u6863\u4F4D\u7684\u6240\u6709\u6837\u672C\uFF0C1 \u5E74\u540E\u7684\u4E2D\u4F4D\u6536\u76CA\u4E0E\u4E0A\u6DA8\u5360\u6BD4\u3002"] }), (todayQuery.isLoading || historyQuery.isLoading) && (_jsx("div", { className: "state", children: "\u52A0\u8F7D\u4E2D\u2026" })), data && data.items.length === 0 && (_jsxs("div", { className: "state", children: [_jsx("p", { children: tab === "today" ? "今日无信号" : "暂无历史信号" }), tab === "today" && (_jsx("p", { className: "hint", children: "\u4FE1\u53F7\u5728\u6BCF\u65E5\u6279\u5904\u7406\u540E\u751F\u6210\u3002A \u80A1 16:30 / \u6E2F\u80A1 17:30 / \u7F8E\u80A1 \u6B21\u65E5 07:00\u3002" }))] })), data && data.items.length > 0 && (_jsxs("table", { className: "table", children: [_jsx("thead", { children: _jsxs("tr", { children: [_jsx("th", { children: "\u65E5\u671F" }), _jsx("th", { children: "\u5E02\u573A" }), _jsx("th", { children: "\u6307\u6570" }), _jsx("th", { children: "\u65B9\u5411" }), _jsx("th", { children: "\u6863\u4F4D" }), _jsx("th", { children: "\u6E29\u5EA6" }), _jsx("th", { children: "1 \u5E74\u5386\u53F2\u53C2\u8003" })] }) }), _jsx("tbody", { children: data.items.map((s) => {
                            const stat = tierStats.get(s.tier);
                            return (_jsxs("tr", { children: [_jsx("td", { children: s.date }), _jsx("td", { children: s.market }), _jsx("td", { children: _jsxs(Link, { to: `/indices/${encodeURIComponent(s.index_code)}`, children: [_jsx("div", { className: "cell-name", children: s.index_name }), _jsx("div", { className: "cell-code", children: s.index_code })] }) }), _jsx("td", { children: _jsx("span", { className: "tier-badge", style: { backgroundColor: DIRECTION_COLOR[s.direction] }, children: DIRECTION_LABEL[s.direction] }) }), _jsx("td", { children: _jsx("span", { className: "tier-badge", style: { backgroundColor: temperatureColor(s.temperature) }, children: s.tier }) }), _jsx("td", { children: formatTemperature(s.temperature) }), _jsx("td", { style: { fontSize: 12 }, children: stat ? (_jsxs("span", { title: `基于 ${stat.n.toLocaleString()} 个历史样本（全指数 10 年）`, children: [_jsxs("span", { style: {
                                                        color: stat.median > 0 ? "#dc2626" : "#15803d",
                                                        fontWeight: 600,
                                                    }, children: [stat.median > 0 ? "+" : "", stat.median.toFixed(1), "%"] }), _jsxs("span", { style: { color: "#6b7280", marginLeft: 6 }, children: ["\u4E0A\u6DA8\u5360\u6BD4 ", stat.winRate.toFixed(0), "%"] })] })) : (_jsx("span", { style: { color: "#9ca3af" }, children: effQuery.isLoading ? "计算中…" : "—" })) })] }, s.id));
                        }) })] }))] }));
}
