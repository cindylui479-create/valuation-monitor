import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Fragment, useState } from "react";
import { fetchDataQualityDetail, fetchDataQualitySummary, setAnomalyAck, } from "@/api/dataQuality";
const SEVERITY_COLOR = {
    HIGH: "#b91c1c",
    MEDIUM: "#d97706",
    LOW: "#2563eb",
    INFO: "#6b7280",
};
const TYPE_LABEL = {
    NEGATIVE: "负值",
    DAILY_JUMP: "单日跳变",
    MAD_OUTLIER: "MAD 离群",
    STALE: "数据冻结",
    CROSS_DIVERGE: "跨源分歧",
    CROSS_IDENTICAL: "跨源同源",
    LOW_VARIANCE: "方差过小",
};
function pill(severity) {
    return {
        display: "inline-block",
        padding: "1px 6px",
        borderRadius: 4,
        background: SEVERITY_COLOR[severity] ?? "#9ca3af",
        color: "white",
        fontSize: 11,
        minWidth: 32,
        textAlign: "center",
    };
}
function AckButton({ anomaly, onChanged, }) {
    const [editing, setEditing] = useState(false);
    const [note, setNote] = useState("");
    const isAcked = !!anomaly.acknowledged_at;
    const mut = useMutation({
        mutationFn: (vars) => setAnomalyAck(anomaly.id, vars.ack, vars.note),
        onSuccess: () => {
            setEditing(false);
            setNote("");
            onChanged();
        },
    });
    if (isAcked) {
        return (_jsx("button", { className: "btn", style: { fontSize: 11, padding: "2px 6px", color: "#15803d" }, title: `${anomaly.acknowledged_at}\n${anomaly.acknowledged_note ?? ""}`, onClick: (e) => { e.stopPropagation(); mut.mutate({ ack: false }); }, disabled: mut.isPending, children: "\u2713 \u5DF2\u6838\u5BF9" }));
    }
    if (editing) {
        return (_jsxs("span", { style: { display: "inline-flex", gap: 4 }, onClick: (e) => e.stopPropagation(), children: [_jsx("input", { autoFocus: true, value: note, placeholder: "\u5907\u6CE8\uFF08\u53EF\u9009\uFF09", onChange: (e) => setNote(e.target.value), onKeyDown: (e) => {
                        if (e.key === "Enter")
                            mut.mutate({ ack: true, note: note || undefined });
                        if (e.key === "Escape")
                            setEditing(false);
                    }, style: { fontSize: 11, padding: "1px 4px", width: 120 } }), _jsx("button", { className: "btn", style: { fontSize: 11, padding: "2px 6px" }, onClick: () => mut.mutate({ ack: true, note: note || undefined }), disabled: mut.isPending, children: "\u786E\u8BA4" }), _jsx("button", { className: "btn", style: { fontSize: 11, padding: "2px 6px" }, onClick: () => setEditing(false), children: "\u53D6\u6D88" })] }));
    }
    return (_jsx("button", { className: "btn", style: { fontSize: 11, padding: "2px 6px" }, onClick: (e) => { e.stopPropagation(); setEditing(true); }, children: "\u6807\u8BB0\u5DF2\u6838\u5BF9" }));
}
function AnomalyDetailRows({ code }) {
    const qc = useQueryClient();
    const detail = useQuery({
        queryKey: ["data-quality-detail", code],
        queryFn: () => fetchDataQualityDetail(code),
    });
    const invalidate = () => {
        qc.invalidateQueries({ queryKey: ["data-quality-detail", code] });
        qc.invalidateQueries({ queryKey: ["data-quality-summary"] });
    };
    if (detail.isLoading)
        return _jsx("tr", { children: _jsx("td", { colSpan: 8, className: "empty", children: "\u52A0\u8F7D\u4E2D\u2026" }) });
    if (!detail.data)
        return null;
    if (detail.data.anomalies.length === 0) {
        return _jsx("tr", { children: _jsx("td", { colSpan: 8, className: "empty", children: "\u65E0\u5F02\u5E38\u8BB0\u5F55" }) });
    }
    return (_jsxs(_Fragment, { children: [detail.data.anomalies.slice(0, 200).map((a) => {
                const isAcked = !!a.acknowledged_at;
                return (_jsxs("tr", { style: isAcked ? { opacity: 0.45 } : undefined, children: [_jsx("td", { children: a.date }), _jsx("td", { children: _jsx("span", { style: pill(a.severity), children: a.severity }) }), _jsx("td", { children: TYPE_LABEL[a.anomaly_type] ?? a.anomaly_type }), _jsxs("td", { children: [a.field, "/", a.source] }), _jsx("td", { children: a.value ?? "—" }), _jsx("td", { children: a.baseline ?? "—" }), _jsx("td", { style: { color: "#6b7280" }, children: a.note ?? "" }), _jsx("td", { children: _jsx(AckButton, { anomaly: a, onChanged: invalidate }) })] }, a.id));
            }), detail.data.anomalies.length > 200 && (_jsx("tr", { children: _jsxs("td", { colSpan: 8, className: "empty", children: ["\u4EC5\u5C55\u793A\u524D 200 \u6761\uFF08\u5171 ", detail.data.anomalies.length, "\uFF09"] }) }))] }));
}
export default function DataQualitySection() {
    const [expandedCode, setExpandedCode] = useState(null);
    const [includeAcked, setIncludeAcked] = useState(false);
    const summary = useQuery({
        queryKey: ["data-quality-summary", includeAcked],
        queryFn: () => fetchDataQualitySummary(includeAcked),
    });
    if (summary.isLoading) {
        return (_jsxs("section", { className: "settings-block", children: [_jsx("h3", { children: "\u6570\u636E\u8D28\u91CF\uFF08SRS R11\uFF09" }), _jsx("p", { className: "empty", children: "\u52A0\u8F7D\u4E2D\u2026" })] }));
    }
    const items = summary.data?.items ?? [];
    const withAnomalies = items.filter((i) => i.total > 0);
    const clean = items.filter((i) => i.total === 0 && i.acknowledged === 0);
    const fullyAcked = items.filter((i) => i.total === 0 && i.acknowledged > 0);
    return (_jsxs("section", { className: "settings-block", children: [_jsxs("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center" }, children: [_jsx("h3", { children: "\u6570\u636E\u8D28\u91CF\uFF08SRS R11\uFF09" }), _jsxs("span", { style: { fontSize: 12, color: "var(--muted)" }, children: ["\u5171 ", summary.data?.total_anomalies ?? 0, " \u6761", includeAcked ? "" : "未核对", "\u5F02\u5E38\uFF0C\u8986\u76D6 ", withAnomalies.length, "/", items.length, " \u53EA\u6307\u6570"] })] }), _jsxs("p", { className: "hint", children: ["\u6BCF\u65E5\u6279\u5904\u7406\u540E\u81EA\u52A8\u68C0\u6D4B 7 \u7C7B\u5F02\u5E38\uFF1A\u8D1F\u503C\u3001\u5355\u65E5\u8DF3\u53D8\u3001MAD \u79BB\u7FA4\u3001\u6570\u636E\u51BB\u7ED3\u3001\u8DE8\u6E90\u5206\u6B67\u3001\u8DE8\u6E90\u540C\u6E90\u3001\u65B9\u5DEE\u8FC7\u5C0F\u3002", _jsx("strong", { children: "\u4E0D\u4FEE\u6539\u6E29\u5EA6/\u5206\u4F4D\u6570\u5B57" }), "\uFF0C\u4EC5\u7528\u4E8E\u544A\u8B66\u3002\u8BE6\u7EC6\u89C4\u5219\u89C1 SRS R11 \u51B3\u7B56\u8868\u3002"] }), _jsxs("label", { style: { display: "inline-flex", alignItems: "center", gap: 6, marginTop: 6, marginBottom: 6, fontSize: 12 }, children: [_jsx("input", { type: "checkbox", checked: includeAcked, onChange: (e) => setIncludeAcked(e.target.checked) }), "\u663E\u793A\u5DF2\u6838\u5BF9\u7684\u5F02\u5E38"] }), withAnomalies.length === 0 ? (_jsxs("p", { className: "empty", children: ["\u6240\u6709\u6307\u6570\u6570\u636E\u8D28\u91CF\u826F\u597D \u2713", includeAcked ? "" : "（或全部已核对）"] })) : (_jsxs("table", { className: "table", children: [_jsx("thead", { children: _jsxs("tr", { children: [_jsx("th", { children: "\u4EE3\u7801" }), _jsx("th", { children: "\u540D\u79F0" }), _jsx("th", { children: "\u5E02\u573A" }), _jsx("th", { children: "HIGH" }), _jsx("th", { children: "MEDIUM" }), _jsx("th", { children: "LOW" }), _jsx("th", { children: "INFO" }), _jsx("th", { children: "\u603B\u8BA1" }), _jsx("th", { children: "\u5DF2\u6838\u5BF9" }), _jsx("th", { children: "\u6700\u8FD1" })] }) }), _jsx("tbody", { children: withAnomalies.map((it) => {
                            const isExpanded = expandedCode === it.code;
                            return (_jsxs(Fragment, { children: [_jsxs("tr", { style: { cursor: "pointer", background: isExpanded ? "#f9fafb" : undefined }, onClick: () => setExpandedCode(isExpanded ? null : it.code), children: [_jsx("td", { children: _jsx("strong", { children: it.code }) }), _jsx("td", { children: it.name }), _jsx("td", { children: it.market }), _jsx("td", { children: it.high > 0 ? _jsx("span", { style: pill("HIGH"), children: it.high }) : "—" }), _jsx("td", { children: it.medium > 0 ? _jsx("span", { style: pill("MEDIUM"), children: it.medium }) : "—" }), _jsx("td", { children: it.low > 0 ? _jsx("span", { style: pill("LOW"), children: it.low }) : "—" }), _jsx("td", { children: it.info > 0 ? _jsx("span", { style: pill("INFO"), children: it.info }) : "—" }), _jsx("td", { children: _jsx("strong", { children: it.total }) }), _jsx("td", { style: { color: "#15803d" }, children: it.acknowledged > 0 ? `✓ ${it.acknowledged}` : "—" }), _jsx("td", { children: it.latest_anomaly_date ?? "—" })] }), isExpanded && (_jsx("tr", { children: _jsx("td", { colSpan: 10, style: { background: "#f9fafb", padding: 0 }, children: _jsxs("table", { className: "table", style: { margin: 0, fontSize: 12 }, children: [_jsx("thead", { children: _jsxs("tr", { children: [_jsx("th", { children: "\u65E5\u671F" }), _jsx("th", { children: "\u7EA7\u522B" }), _jsx("th", { children: "\u7C7B\u578B" }), _jsx("th", { children: "\u5B57\u6BB5/\u6E90" }), _jsx("th", { children: "\u503C" }), _jsx("th", { children: "\u57FA\u7EBF" }), _jsx("th", { children: "\u8BF4\u660E" }), _jsx("th", { style: { width: 200 }, children: "\u64CD\u4F5C" })] }) }), _jsx("tbody", { children: _jsx(AnomalyDetailRows, { code: it.code }) })] }) }) }))] }, it.code));
                        }) })] })), (clean.length > 0 || fullyAcked.length > 0) && (_jsxs("p", { className: "hint", style: { marginTop: 12 }, children: [clean.length > 0 && _jsxs(_Fragment, { children: ["\u2713 \u65E0\u5F02\u5E38\uFF1A", clean.map((c) => c.code).join("、")] }), clean.length > 0 && fullyAcked.length > 0 && " ｜ ", fullyAcked.length > 0 && _jsxs(_Fragment, { children: ["\u2713 \u5168\u90E8\u5DF2\u6838\u5BF9\uFF1A", fullyAcked.map((c) => c.code).join("、")] })] }))] }));
}
