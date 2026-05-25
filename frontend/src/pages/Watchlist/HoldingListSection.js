import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { useState } from "react";
import { addHolding, deleteHolding, fetchPortfolio, updateHolding, } from "@/api/holdings";
import EntityCombo from "@/components/EntityCombo";
import { isPriceFallback, temperatureColor, tierLabel, } from "@/utils/temperature";
const TYPE_LABEL = {
    INDEX: "指数",
    STOCK: "个股",
    FUND: "基金",
};
const TYPE_COLOR = {
    INDEX: { bg: "#dbeafe", fg: "#1e40af" },
    STOCK: { bg: "#fce7f3", fg: "#9d174d" },
    FUND: { bg: "#fef3c7", fg: "#92400e" },
};
const TIER_ORDER = ["极度低估", "低估", "合理", "高估", "极度高估"];
function detailPath(t, code) {
    if (t === "INDEX")
        return `/indices/${encodeURIComponent(code)}`;
    if (t === "STOCK")
        return `/stocks/${encodeURIComponent(code)}`;
    return `/funds/${encodeURIComponent(code)}`;
}
export default function HoldingListSection() {
    const qc = useQueryClient();
    const [selected, setSelected] = useState(null);
    const [mode, setMode] = useState("value");
    const [amount, setAmount] = useState(""); // 数字（金额或数量）
    const [note, setNote] = useState("");
    const [err, setErr] = useState(null);
    const [editingId, setEditingId] = useState(null);
    const [editMode, setEditMode] = useState("value");
    const [editAmount, setEditAmount] = useState("");
    const portfolio = useQuery({
        queryKey: ["portfolio"],
        queryFn: fetchPortfolio,
        refetchInterval: 30_000, // 30s 自动刷新一次，让数量模式持仓的市值跟随单价
    });
    const addMut = useMutation({
        mutationFn: () => {
            if (!selected)
                throw new Error("请先选择标的");
            const n = parseFloat(amount);
            if (!Number.isFinite(n) || n <= 0)
                throw new Error("数值必须 > 0");
            return addHolding({
                entity_type: selected.entity_type,
                entity_code: selected.code,
                market_value: mode === "value" ? n : undefined,
                quantity: mode === "quantity" ? n : undefined,
                note: note.trim() || undefined,
            });
        },
        onSuccess: () => {
            setSelected(null);
            setAmount("");
            setNote("");
            setErr(null);
            qc.invalidateQueries({ queryKey: ["portfolio"] });
        },
        onError: (e) => setErr(e.message),
    });
    const delMut = useMutation({
        mutationFn: (id) => deleteHolding(id),
        onSuccess: () => qc.invalidateQueries({ queryKey: ["portfolio"] }),
    });
    const updMut = useMutation({
        mutationFn: () => {
            if (editingId == null)
                throw new Error("no id");
            const n = parseFloat(editAmount);
            if (!Number.isFinite(n) || n <= 0)
                throw new Error("数值必须 > 0");
            return updateHolding(editingId, {
                market_value: editMode === "value" ? n : undefined,
                quantity: editMode === "quantity" ? n : undefined,
            });
        },
        onSuccess: () => {
            setEditingId(null);
            qc.invalidateQueries({ queryKey: ["portfolio"] });
        },
    });
    if (portfolio.isLoading)
        return _jsx("p", { className: "empty", children: "\u52A0\u8F7D\u4E2D\u2026" });
    const data = portfolio.data;
    if (!data)
        return null;
    const total = parseFloat(data.total_value);
    const weightedTemp = data.weighted_temperature ? parseFloat(data.weighted_temperature) : null;
    const coverage = parseFloat(data.coverage_pct);
    return (_jsxs("div", { children: [_jsxs("section", { className: "latest-card", style: { marginBottom: 16 }, children: [weightedTemp != null && (_jsx("div", { className: "tier-pill", style: { backgroundColor: temperatureColor(weightedTemp.toString()) }, children: "\u7EC4\u5408\u6E29\u5EA6" })), _jsxs("div", { className: "stat", children: [_jsx("div", { className: "label", children: "\u603B\u5E02\u503C" }), _jsxs("div", { className: "value", children: ["\u00A5", total.toLocaleString("zh-CN", { maximumFractionDigits: 0 })] })] }), _jsxs("div", { className: "stat", children: [_jsx("div", { className: "label", children: "\u52A0\u6743\u6E29\u5EA6\uFF08\u6309\u5E02\u503C\uFF09" }), _jsx("div", { className: "value", children: weightedTemp != null ? weightedTemp.toFixed(1) : "—" })] }), _jsxs("div", { className: "stat", children: [_jsx("div", { className: "label", children: "\u6E29\u5EA6\u8986\u76D6\u7387" }), _jsxs("div", { className: "value", children: [coverage.toFixed(0), "%"] })] }), _jsxs("div", { className: "stat", children: [_jsx("div", { className: "label", children: "\u6301\u4ED3\u9879" }), _jsx("div", { className: "value", children: data.items.length })] })] }), Object.keys(data.tier_distribution).length > 0 && (_jsxs("section", { className: "settings-block", children: [_jsx("h3", { children: "\u6863\u4F4D\u5206\u5E03\uFF08\u6309\u5E02\u503C\u5360\u6BD4\uFF09" }), _jsx("div", { style: { display: "flex", height: 32, borderRadius: 4, overflow: "hidden", border: "1px solid #e5e7eb" }, children: TIER_ORDER.map((tier) => {
                            const pct = parseFloat(data.tier_distribution[tier] ?? "0");
                            if (pct === 0)
                                return null;
                            return (_jsx("div", { title: `${tier} ${pct.toFixed(1)}%`, style: {
                                    width: `${pct}%`,
                                    background: temperatureColor(tier === "极度低估" ? "5" : tier === "低估" ? "20" :
                                        tier === "合理" ? "50" : tier === "高估" ? "80" : "95"),
                                    color: "white", fontSize: 11,
                                    display: "flex", alignItems: "center", justifyContent: "center",
                                }, children: pct >= 8 ? `${tier} ${pct.toFixed(0)}%` : "" }, tier));
                        }) })] })), _jsxs("section", { className: "settings-block", children: [_jsx("h3", { children: "\u6DFB\u52A0\u6301\u4ED3" }), _jsxs("div", { style: { display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }, children: [_jsx(EntityCombo, { value: selected, onChange: setSelected }), _jsxs("div", { style: { display: "flex", border: "1px solid #d1d5db", borderRadius: 4, overflow: "hidden" }, children: [_jsx("button", { type: "button", onClick: () => setMode("value"), style: {
                                            padding: "4px 10px", fontSize: 12,
                                            background: mode === "value" ? "#2563eb" : "white",
                                            color: mode === "value" ? "white" : "#374151",
                                            border: "none", cursor: "pointer",
                                        }, children: "\u6309\u91D1\u989D" }), _jsx("button", { type: "button", onClick: () => setMode("quantity"), style: {
                                            padding: "4px 10px", fontSize: 12,
                                            background: mode === "quantity" ? "#2563eb" : "white",
                                            color: mode === "quantity" ? "white" : "#374151",
                                            border: "none", cursor: "pointer",
                                            borderLeft: "1px solid #d1d5db",
                                        }, children: "\u6309\u6570\u91CF" })] }), _jsx("input", { placeholder: mode === "value" ? "市值（¥）" : "股数 / 份数", type: "number", value: amount, onChange: (e) => setAmount(e.target.value), style: { width: 140, padding: "4px 8px" } }), _jsx("input", { placeholder: "\u5907\u6CE8\uFF08\u53EF\u9009\uFF09", value: note, onChange: (e) => setNote(e.target.value), style: { width: 160, padding: "4px 8px" } }), _jsx("button", { className: "btn btn-primary", disabled: !selected || !amount || addMut.isPending, onClick: () => addMut.mutate(), children: addMut.isPending ? "..." : "加入" })] }), err && _jsx("p", { style: { color: "#b91c1c", fontSize: 12, marginTop: 8 }, children: err }), _jsx("p", { className: "hint", children: mode === "value"
                            ? "按金额：直接录入当前市值（人民币）。"
                            : "按数量：录入股数/份数，系统自动按最新价 × 数量算市值，并每 30 秒刷新一次。" })] }), _jsxs("section", { className: "settings-block", children: [_jsxs("h3", { children: ["\u6301\u4ED3\u660E\u7EC6\uFF08", data.items.length, "\uFF09"] }), data.items.length === 0 ? (_jsx("p", { className: "empty", children: "\u8FD8\u6CA1\u6709\u6301\u4ED3\u3002\u5728\u4E0A\u65B9\u5F55\u5165\u3002" })) : (_jsxs("table", { className: "table", children: [_jsx("thead", { children: _jsxs("tr", { children: [_jsx("th", { children: "\u7C7B\u578B" }), _jsx("th", { children: "\u4EE3\u7801" }), _jsx("th", { children: "\u540D\u79F0" }), _jsx("th", { children: "\u5F55\u5165" }), _jsx("th", { children: "\u5E02\u503C\uFF08\u00A5\uFF09" }), _jsx("th", { children: "\u6743\u91CD" }), _jsx("th", { children: "\u6E29\u5EA6" }), _jsx("th", { children: "\u6863\u4F4D" }), _jsx("th", { children: "PE / PB" }), _jsx("th", { children: "\u53E3\u5F84" }), _jsx("th", { children: "\u5907\u6CE8" }), _jsx("th", {})] }) }), _jsx("tbody", { children: data.items.map((h) => {
                                    const temp = h.temperature ? parseFloat(h.temperature) : null;
                                    const c = TYPE_COLOR[h.entity_type];
                                    const pf = isPriceFallback(h.temperature_source);
                                    const isEditing = editingId === h.id;
                                    const qty = h.quantity ? parseFloat(h.quantity) : null;
                                    const price = h.latest_price ? parseFloat(h.latest_price) : null;
                                    return (_jsxs("tr", { children: [_jsx("td", { children: _jsx("span", { style: {
                                                        fontSize: 11, padding: "1px 6px",
                                                        background: c.bg, color: c.fg, borderRadius: 4,
                                                    }, children: TYPE_LABEL[h.entity_type] }) }), _jsx("td", { children: _jsx(Link, { to: detailPath(h.entity_type, h.entity_code), children: _jsx("strong", { children: h.entity_code }) }) }), _jsx("td", { children: h.entity_name ?? _jsx("span", { style: { color: "#dc2626" }, children: "\u26A0 \u672A\u627E\u5230" }) }), _jsx("td", { style: { fontSize: 11, color: "#6b7280" }, children: h.input_mode === "quantity" && qty != null
                                                    ? `${qty} × ¥${price?.toFixed(2) ?? "?"}`
                                                    : "金额" }), _jsx("td", { children: isEditing ? (_jsxs("div", { style: { display: "flex", gap: 4, alignItems: "center" }, children: [_jsxs("select", { value: editMode, onChange: (e) => setEditMode(e.target.value), style: { fontSize: 11, padding: "1px 4px" }, children: [_jsx("option", { value: "value", children: "\u00A5" }), _jsx("option", { value: "quantity", children: "\u6570\u91CF" })] }), _jsx("input", { type: "number", value: editAmount, onChange: (e) => setEditAmount(e.target.value), onKeyDown: (e) => {
                                                                if (e.key === "Enter")
                                                                    updMut.mutate();
                                                                if (e.key === "Escape")
                                                                    setEditingId(null);
                                                            }, style: { width: 80, padding: "2px 4px", fontSize: 12 }, autoFocus: true })] })) : (parseFloat(h.market_value).toLocaleString("zh-CN", { maximumFractionDigits: 0 })) }), _jsx("td", { children: h.weight_pct ? h.weight_pct + "%" : "—" }), _jsx("td", { children: temp != null ? (_jsxs(_Fragment, { children: [_jsx("span", { style: {
                                                                background: temperatureColor(temp.toString()),
                                                                color: "white", padding: "1px 8px",
                                                                borderRadius: 4, fontSize: 11,
                                                            }, children: temp.toFixed(1) }), pf && _jsx("span", { title: "\u4EF7\u683C\u81EA\u6BD4", style: { marginLeft: 4, color: "#d97706" }, children: "\u26A0" })] })) : "—" }), _jsx("td", { children: h.tier ? tierLabel(h.tier) : "—" }), _jsxs("td", { style: { fontSize: 12, color: "#6b7280" }, children: [h.pe_ttm ? parseFloat(h.pe_ttm).toFixed(1) : "—", " / ", h.pb ? parseFloat(h.pb).toFixed(2) : "—"] }), _jsx("td", { style: { fontSize: 11, color: pf ? "#d97706" : "#6b7280" }, children: h.temperature_source ?? "—" }), _jsx("td", { style: { fontSize: 12 }, children: h.note ?? "—" }), _jsx("td", { style: { whiteSpace: "nowrap" }, children: isEditing ? (_jsxs(_Fragment, { children: [_jsx("button", { className: "btn", style: { fontSize: 11, padding: "2px 6px", marginRight: 4 }, onClick: () => updMut.mutate(), children: "\u786E\u8BA4" }), _jsx("button", { className: "btn", style: { fontSize: 11, padding: "2px 6px" }, onClick: () => setEditingId(null), children: "\u53D6\u6D88" })] })) : (_jsxs(_Fragment, { children: [_jsx("button", { className: "btn", style: { fontSize: 11, padding: "2px 6px", marginRight: 4 }, onClick: () => {
                                                                setEditingId(h.id);
                                                                setEditMode(h.input_mode);
                                                                setEditAmount(h.input_mode === "quantity"
                                                                    ? (h.quantity ?? "")
                                                                    : h.market_value);
                                                            }, children: "\u6539" }), _jsx("button", { className: "btn", style: { fontSize: 11, padding: "2px 6px" }, onClick: () => {
                                                                if (confirm(`删除 ${h.entity_code} ${h.entity_name ?? ""}？`)) {
                                                                    delMut.mutate(h.id);
                                                                }
                                                            }, children: "\u5220" })] })) })] }, h.id));
                                }) })] }))] })] }));
}
