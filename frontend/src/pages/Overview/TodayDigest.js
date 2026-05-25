import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { fetchOpportunities, fetchTierTransitions, } from "@/api/opportunities";
import { temperatureColor } from "@/utils/temperature";
const TYPE_COLOR = {
    INDEX: { bg: "#dbeafe", fg: "#1e40af" },
    STOCK: { bg: "#fce7f3", fg: "#9d174d" },
    FUND: { bg: "#fef3c7", fg: "#92400e" },
};
function entityPath(t, code) {
    if (t === "INDEX")
        return `/indices/${encodeURIComponent(code)}`;
    if (t === "STOCK")
        return `/stocks/${encodeURIComponent(code)}`;
    return `/funds/${encodeURIComponent(code)}`;
}
function OppPill({ o }) {
    const c = TYPE_COLOR[o.entity_type];
    const t = parseFloat(o.temperature);
    return (_jsxs(Link, { to: entityPath(o.entity_type, o.entity_code), style: {
            display: "inline-flex", alignItems: "center", gap: 6,
            padding: "4px 10px", borderRadius: 999,
            background: "white", border: "1px solid #e5e7eb",
            textDecoration: "none", color: "inherit",
            fontSize: 12,
        }, children: [_jsx("span", { style: {
                    fontSize: 10, padding: "1px 5px",
                    background: c.bg, color: c.fg, borderRadius: 3,
                }, children: o.entity_type }), _jsx("strong", { children: o.entity_name }), _jsx("span", { style: { color: "#9ca3af" }, children: o.entity_code }), _jsx("span", { style: {
                    background: temperatureColor(o.temperature),
                    color: "white", padding: "1px 6px",
                    borderRadius: 3, fontSize: 10,
                }, children: t.toFixed(1) })] }));
}
function TransitionRow({ t }) {
    const c = TYPE_COLOR[t.entity_type];
    const delta = parseFloat(t.temperature_delta);
    const sevColor = t.severity === "HIGH" ? "#b91c1c" :
        t.severity === "MEDIUM" ? "#d97706" : "#6b7280";
    return (_jsxs(Link, { to: entityPath(t.entity_type, t.entity_code), style: {
            display: "flex", alignItems: "center", gap: 8,
            padding: "6px 10px", textDecoration: "none", color: "inherit",
            fontSize: 12, borderBottom: "1px solid #f3f4f6",
        }, children: [_jsx("span", { style: {
                    fontSize: 10, padding: "1px 5px",
                    background: sevColor, color: "white",
                    borderRadius: 3, minWidth: 50, textAlign: "center",
                }, children: t.severity }), _jsx("span", { style: { color: "#6b7280", minWidth: 80 }, children: t.date }), _jsx("span", { style: {
                    fontSize: 10, padding: "1px 5px",
                    background: c.bg, color: c.fg, borderRadius: 3,
                }, children: t.entity_type }), _jsx("strong", { children: t.entity_name }), _jsx("span", { style: { color: "#9ca3af" }, children: t.entity_code }), _jsxs("span", { style: { marginLeft: "auto" }, children: [_jsx("span", { style: { color: "#9ca3af" }, children: t.from_tier ?? "—" }), " → ", _jsx("strong", { children: t.to_tier }), _jsxs("span", { style: {
                            marginLeft: 8,
                            color: delta > 0 ? "#dc2626" : "#15803d",
                        }, children: [delta > 0 ? "↑" : "↓", " ", Math.abs(delta).toFixed(1), "\u00B0"] })] })] }));
}
export default function TodayDigest() {
    const opps = useQuery({
        queryKey: ["opportunities"],
        queryFn: fetchOpportunities,
    });
    const transitions = useQuery({
        queryKey: ["tier-transitions", 7],
        queryFn: () => fetchTierTransitions(7),
    });
    const low = opps.data?.low_valuations ?? [];
    const high = opps.data?.high_valuations ?? [];
    const trans = transitions.data?.items ?? [];
    if (opps.isLoading || transitions.isLoading) {
        return null;
    }
    if (low.length === 0 && high.length === 0 && trans.length === 0) {
        return null;
    }
    return (_jsxs("section", { className: "settings-block", style: { marginBottom: 16 }, children: [_jsx("h3", { children: "\uD83D\uDD14 \u4ECA\u65E5\u52A8\u6001" }), low.length > 0 && (_jsxs("div", { style: { marginBottom: 12 }, children: [_jsxs("div", { style: { fontSize: 12, color: "#15803d", marginBottom: 6, fontWeight: 600 }, children: ["\u2728 \u4F4E\u4F30\u673A\u4F1A\uFF08", low.length, "\uFF09"] }), _jsx("div", { style: { display: "flex", flexWrap: "wrap", gap: 6 }, children: low.slice(0, 12).map((o) => (_jsx(OppPill, { o: o }, `${o.entity_type}-${o.entity_code}`))) })] })), high.length > 0 && (_jsxs("div", { style: { marginBottom: 12 }, children: [_jsxs("div", { style: { fontSize: 12, color: "#b91c1c", marginBottom: 6, fontWeight: 600 }, children: ["\u26A0 \u6781\u5EA6\u9AD8\u4F30\uFF08", high.length, "\uFF09"] }), _jsx("div", { style: { display: "flex", flexWrap: "wrap", gap: 6 }, children: high.slice(0, 12).map((o) => (_jsx(OppPill, { o: o }, `${o.entity_type}-${o.entity_code}`))) })] })), trans.length > 0 && (_jsxs("div", { children: [_jsxs("div", { style: { fontSize: 12, color: "#374151", marginBottom: 6, fontWeight: 600 }, children: ["\uD83D\uDCCA 7 \u5929\u5185\u6863\u4F4D\u8DF3\u53D8\uFF08", trans.length, "\uFF09"] }), _jsx("div", { style: { border: "1px solid #e5e7eb", borderRadius: 4 }, children: trans.slice(0, 8).map((t, i) => (_jsx(TransitionRow, { t: t }, `${t.entity_type}-${t.entity_code}-${t.date}-${i}`))) })] }))] }));
}
