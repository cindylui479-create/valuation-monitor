import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { rebalanceSuggest } from "@/api/rebalance";
export default function RebalancePanel({ currentTemp }) {
    const [target, setTarget] = useState(50);
    const [result, setResult] = useState(null);
    const [meta, setMeta] = useState(null);
    const [err, setErr] = useState(null);
    const mut = useMutation({
        mutationFn: () => rebalanceSuggest(target),
        onSuccess: (data) => {
            setResult(data.adjustments);
            setMeta({
                feasible: data.feasible,
                current: data.current_temp,
                projected: data.projected_temp,
                notes: data.notes,
            });
            setErr(null);
        },
        onError: (e) => setErr(e.message),
    });
    return (_jsxs("section", { className: "settings-block", children: [_jsx("h3", { children: "\u7EC4\u5408\u518D\u5E73\u8861\u5EFA\u8BAE\uFF08SRS I\uFF09" }), _jsx("p", { className: "hint", children: "\u8D2A\u5FC3\u7B97\u6CD5\uFF1A\u76EE\u6807\u4F4E\u6E29\u5EA6\u65F6\u51CF\u4ED3\"\u6E29\u5EA6\u9AD8\u4E8E\u76EE\u6807\"\u7684\u6807\u7684\uFF0C\u52A0\u4ED3\"\u6E29\u5EA6\u4F4E\u4E8E\u76EE\u6807\"\u7684\u6807\u7684\uFF08\u91D1\u989D\u4EC5\u4F5C\u5EFA\u8BAE\u53C2\u8003\uFF09\u3002 \u53D7\u73B0\u6709\u6301\u4ED3\u6E29\u5EA6\u9650\u5236\u2014\u2014\u5982\u6240\u6709\u6301\u4ED3\u90FD\u5728\u67D0\u4E00\u533A\u95F4\uFF0C\u53EF\u80FD\u4E0D\u53EF\u8FBE\u3002" }), _jsxs("div", { style: { display: "flex", gap: 16, alignItems: "center", flexWrap: "wrap", marginTop: 8 }, children: [_jsxs("label", { style: { display: "flex", alignItems: "center", gap: 6 }, children: [_jsx("span", { style: { fontSize: 12, color: "#6b7280" }, children: "\u5F53\u524D\uFF1A" }), _jsx("strong", { children: currentTemp != null ? currentTemp.toFixed(1) : "—" })] }), _jsxs("label", { style: { display: "flex", alignItems: "center", gap: 6 }, children: ["\u76EE\u6807\u6E29\u5EA6\uFF1A", _jsx("input", { type: "range", min: 0, max: 100, step: 1, value: target, onChange: (e) => setTarget(Number(e.target.value)), style: { width: 200 } }), _jsx("strong", { style: { minWidth: 32 }, children: target })] }), _jsx("button", { className: "btn btn-primary", onClick: () => mut.mutate(), disabled: mut.isPending, children: mut.isPending ? "计算中…" : "生成建议" })] }), err && _jsx("p", { style: { color: "#b91c1c", fontSize: 12, marginTop: 8 }, children: err }), meta && (_jsxs("div", { style: { marginTop: 12 }, children: [_jsxs("div", { style: {
                            display: "flex", gap: 16, padding: 10,
                            background: meta.feasible ? "#f0fdf4" : "#fef3c7",
                            border: `1px solid ${meta.feasible ? "#86efac" : "#fde68a"}`,
                            borderRadius: 4, fontSize: 13,
                        }, children: [_jsxs("span", { children: ["\u5F53\u524D ", meta.current ? parseFloat(meta.current).toFixed(1) : "—", " \u2192"] }), _jsxs("span", { children: ["\u9884\u671F ", _jsx("strong", { children: meta.projected ? parseFloat(meta.projected).toFixed(1) : "—" })] }), _jsxs("span", { children: ["\uFF08\u76EE\u6807 ", target, "\uFF09"] }), !meta.feasible && _jsx("span", { style: { color: "#d97706" }, children: "\u26A0 \u76EE\u6807\u4E0D\u53EF\u8FBE" })] }), meta.notes.length > 0 && (_jsx("ul", { style: { fontSize: 12, color: "#6b7280", marginTop: 6 }, children: meta.notes.map((n, i) => _jsx("li", { children: n }, i)) }))] })), result && result.length > 0 && (_jsxs("table", { className: "table", style: { marginTop: 12, fontSize: 13 }, children: [_jsx("thead", { children: _jsxs("tr", { children: [_jsx("th", { children: "\u4EE3\u7801" }), _jsx("th", { children: "\u540D\u79F0" }), _jsx("th", { children: "\u6E29\u5EA6" }), _jsx("th", { children: "\u5F53\u524D \u00A5" }), _jsx("th", { children: "\u5EFA\u8BAE \u00A5" }), _jsx("th", { children: "\u52A8\u4F5C" })] }) }), _jsx("tbody", { children: result.map((a) => {
                            const delta = parseFloat(a.delta_mv);
                            const color = a.direction === "ADD" ? "#15803d" : a.direction === "REDUCE" ? "#dc2626" : "#6b7280";
                            return (_jsxs("tr", { children: [_jsx("td", { children: _jsx("strong", { children: a.entity_code }) }), _jsx("td", { children: a.entity_name }), _jsx("td", { children: parseFloat(a.current_temp).toFixed(1) }), _jsx("td", { children: parseFloat(a.current_mv).toLocaleString("zh-CN", { maximumFractionDigits: 0 }) }), _jsx("td", { children: parseFloat(a.suggested_mv).toLocaleString("zh-CN", { maximumFractionDigits: 0 }) }), _jsxs("td", { style: { color, fontWeight: 600 }, children: [a.direction === "ADD" ? "+加仓 " : a.direction === "REDUCE" ? "-减仓 " : "持平", a.direction !== "HOLD" && (Math.abs(delta).toLocaleString("zh-CN", { maximumFractionDigits: 0 }))] })] }, `${a.entity_type}-${a.entity_code}`));
                        }) })] }))] }));
}
