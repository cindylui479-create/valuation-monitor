import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
/**
 * SRS v1.3.1 I-fix：再平衡建议（纯逆向模式）。
 *
 * 移除 target slider —— 之前实现"机械求解组合温度 = X"导致升温场景下
 * 推荐"加仓高估、减仓低估"，反直觉。
 *
 * 新逻辑（与"低买高卖"逆向投资直觉一致）：
 *   - 减仓所有温度 > 70 的高估持仓（按 reduce_pct）
 *   - 释放资金按现有 mv 比例加仓所有温度 < 30 的低估持仓
 *   - MID (30-70) 桶保持不变
 */
import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { rebalanceSuggest } from "@/api/rebalance";
const REDUCE_OPTIONS = [
    { value: 0.10, label: "保守 10%" },
    { value: 0.20, label: "适中 20%" },
    { value: 0.30, label: "标准 30%" },
    { value: 0.50, label: "激进 50%" },
];
export default function RebalancePanel({ currentTemp }) {
    const [reducePct, setReducePct] = useState(0.30);
    const [result, setResult] = useState(null);
    const [meta, setMeta] = useState(null);
    const [err, setErr] = useState(null);
    const mut = useMutation({
        mutationFn: () => rebalanceSuggest(reducePct),
        onSuccess: (data) => {
            setResult(data.adjustments);
            setMeta({
                feasible: data.feasible,
                current: data.current_temp,
                projected: data.projected_temp,
                released: data.total_released,
                n_high: data.n_high,
                n_low: data.n_low,
                n_mid: data.n_mid,
                notes: data.notes,
            });
            setErr(null);
        },
        onError: (e) => setErr(e.message),
    });
    const directionColor = (d) => d === "REDUCE" ? "#dc2626" : d === "ADD" ? "#15803d" : "#6b7280";
    return (_jsxs("section", { className: "settings-block", children: [_jsx("h3", { children: "\u7EC4\u5408\u518D\u5E73\u8861\u5EFA\u8BAE\uFF08\u7EAF\u9006\u5411\u6A21\u5F0F\uFF09" }), _jsxs("p", { className: "hint", children: [_jsx("strong", { children: "\"\u4F4E\u4E70\u9AD8\u5356\"\u903B\u8F91" }), "\uFF1A\u51CF\u4ED3\u6240\u6709\u6E29\u5EA6 > 70 \u7684\u9AD8\u4F30\u6301\u4ED3\uFF0C \u91CA\u653E\u8D44\u91D1\u6309\u6BD4\u4F8B\u52A0\u4ED3\u6240\u6709\u6E29\u5EA6 < 30 \u7684\u4F4E\u4F30\u6301\u4ED3\u3002 30-70 \u5408\u7406\u533A\u95F4\u6301\u4ED3\u4FDD\u6301\u4E0D\u53D8\u3002", _jsx("br", {}), "\u82E5\u7EC4\u5408\u65E0\u9AD8\u4F30/\u4F4E\u4F30\u6301\u4ED3\uFF0C\u5C06\u63D0\u793A\"\u65E0\u9700\u518D\u5E73\u8861\"\u6216\"\u5EFA\u8BAE\u4FDD\u7559\u73B0\u91D1\"\u3002"] }), _jsxs("div", { style: { display: "flex", gap: 16, alignItems: "center", flexWrap: "wrap", marginTop: 8 }, children: [_jsxs("span", { style: { fontSize: 12, color: "#6b7280" }, children: ["\u5F53\u524D\u7EC4\u5408\u6E29\u5EA6\uFF1A", _jsx("strong", { children: currentTemp != null ? currentTemp.toFixed(1) : "—" })] }), _jsxs("div", { style: { display: "flex", alignItems: "center", gap: 6 }, children: [_jsx("span", { style: { fontSize: 12 }, children: "\u51CF\u4ED3\u6BD4\u4F8B\uFF1A" }), _jsx("div", { style: { display: "flex", border: "1px solid #d1d5db", borderRadius: 4, overflow: "hidden" }, children: REDUCE_OPTIONS.map((opt) => (_jsx("button", { type: "button", onClick: () => setReducePct(opt.value), style: {
                                        padding: "4px 10px", fontSize: 12,
                                        background: reducePct === opt.value ? "#2563eb" : "white",
                                        color: reducePct === opt.value ? "white" : "#374151",
                                        border: "none", cursor: "pointer",
                                        borderLeft: opt.value !== 0.10 ? "1px solid #d1d5db" : "none",
                                    }, children: opt.label }, opt.value))) })] }), _jsx("button", { className: "btn btn-primary", onClick: () => mut.mutate(), disabled: mut.isPending, children: mut.isPending ? "计算中…" : "生成建议" })] }), err && _jsx("p", { style: { color: "#b91c1c", fontSize: 12, marginTop: 8 }, children: err }), meta && (_jsxs("div", { style: { marginTop: 12 }, children: [_jsxs("div", { style: {
                            display: "flex", gap: 16, padding: 10,
                            background: meta.feasible && parseFloat(meta.released) > 0 ? "#f0fdf4" : "#fef3c7",
                            border: `1px solid ${meta.feasible && parseFloat(meta.released) > 0 ? "#86efac" : "#fde68a"}`,
                            borderRadius: 4, fontSize: 13, flexWrap: "wrap",
                        }, children: [_jsxs("span", { children: ["\u6876\u5206\u5E03\uFF1A", _jsxs("strong", { style: { color: "#dc2626" }, children: ["HIGH ", meta.n_high] }), " \u00B7 ", _jsxs("strong", { style: { color: "#6b7280" }, children: ["MID ", meta.n_mid] }), " \u00B7 ", _jsxs("strong", { style: { color: "#15803d" }, children: ["LOW ", meta.n_low] })] }), parseFloat(meta.released) > 0 && (_jsxs("span", { children: ["\u91CA\u653E\u8D44\u91D1 ", _jsxs("strong", { children: ["\u00A5", parseFloat(meta.released).toLocaleString("zh-CN", { maximumFractionDigits: 0 })] })] })), _jsxs("span", { children: ["\u7EC4\u5408\u6E29\u5EA6 ", meta.current ? parseFloat(meta.current).toFixed(1) : "—", " \u2192", _jsxs("strong", { children: [" ", meta.projected ? parseFloat(meta.projected).toFixed(1) : "—"] })] })] }), meta.notes.length > 0 && (_jsx("ul", { style: { fontSize: 12, color: "#6b7280", marginTop: 6, paddingLeft: 20 }, children: meta.notes.map((n, i) => _jsx("li", { children: n }, i)) }))] })), result && result.length > 0 && (_jsxs("table", { className: "table", style: { marginTop: 12, fontSize: 13 }, children: [_jsx("thead", { children: _jsxs("tr", { children: [_jsx("th", { children: "\u6876" }), _jsx("th", { children: "\u4EE3\u7801" }), _jsx("th", { children: "\u540D\u79F0" }), _jsx("th", { children: "\u6E29\u5EA6" }), _jsx("th", { children: "\u6863\u4F4D" }), _jsx("th", { children: "\u5F53\u524D \u00A5" }), _jsx("th", { children: "\u5EFA\u8BAE \u00A5" }), _jsx("th", { children: "\u52A8\u4F5C" })] }) }), _jsx("tbody", { children: result.map((a) => {
                            const delta = parseFloat(a.delta_mv);
                            const bucketColor = a.bucket === "HIGH" ? "#fee2e2" :
                                a.bucket === "LOW" ? "#dcfce7" : "#f3f4f6";
                            const bucketFg = a.bucket === "HIGH" ? "#b91c1c" :
                                a.bucket === "LOW" ? "#166534" : "#6b7280";
                            return (_jsxs("tr", { children: [_jsx("td", { children: _jsx("span", { style: {
                                                fontSize: 11, padding: "1px 6px",
                                                background: bucketColor, color: bucketFg, borderRadius: 3,
                                            }, children: a.bucket }) }), _jsx("td", { children: _jsx("strong", { children: a.entity_code }) }), _jsx("td", { children: a.entity_name }), _jsx("td", { children: parseFloat(a.current_temp).toFixed(1) }), _jsx("td", { style: { fontSize: 11, color: "#6b7280" }, children: a.tier ?? "—" }), _jsx("td", { children: parseFloat(a.current_mv).toLocaleString("zh-CN", { maximumFractionDigits: 0 }) }), _jsx("td", { children: parseFloat(a.suggested_mv).toLocaleString("zh-CN", { maximumFractionDigits: 0 }) }), _jsxs("td", { style: { color: directionColor(a.direction), fontWeight: 600 }, children: [a.direction === "REDUCE" && `- 减仓 ${Math.abs(delta).toLocaleString("zh-CN", { maximumFractionDigits: 0 })}`, a.direction === "ADD" && `+ 加仓 ${delta.toLocaleString("zh-CN", { maximumFractionDigits: 0 })}`, a.direction === "HOLD" && "持平"] })] }, `${a.entity_type}-${a.entity_code}`));
                        }) })] }))] }));
}
