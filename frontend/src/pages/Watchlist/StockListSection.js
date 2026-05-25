import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { useState } from "react";
import { addStock, listStocks, removeStock } from "@/api/stocks";
import { temperatureColor, tierLabel } from "@/utils/temperature";
const ANCHOR_LABEL = {
    PE: "PE-TTM",
    PB: "市净率",
    PS: "市销率",
    PE_REVERSE: "PE 倒置",
    DIV_YIELD: "股息率倒置",
};
export default function StockListSection() {
    const qc = useQueryClient();
    const [code, setCode] = useState("");
    const [err, setErr] = useState(null);
    const list = useQuery({
        queryKey: ["stocks"],
        queryFn: listStocks,
    });
    const addMut = useMutation({
        mutationFn: (c) => addStock(c),
        onSuccess: () => {
            setCode("");
            setErr(null);
            qc.invalidateQueries({ queryKey: ["stocks"] });
        },
        onError: (e) => setErr(e.message),
    });
    const removeMut = useMutation({
        mutationFn: (c) => removeStock(c),
        onSuccess: () => qc.invalidateQueries({ queryKey: ["stocks"] }),
    });
    const items = list.data?.items ?? [];
    return (_jsxs("div", { children: [_jsxs("section", { className: "settings-block", children: [_jsx("h3", { children: "\u6DFB\u52A0\u4E2A\u80A1" }), _jsxs("div", { style: { display: "flex", gap: 8, alignItems: "center" }, children: [_jsx("input", { placeholder: "\u80A1\u7968\u4EE3\u7801\uFF08\u5982 600519.SH \u6216 000001\uFF09", value: code, onChange: (e) => setCode(e.target.value), style: { flex: 1, maxWidth: 280, padding: "4px 8px" }, disabled: addMut.isPending, onKeyDown: (e) => {
                                    if (e.key === "Enter" && code.trim() && !addMut.isPending) {
                                        addMut.mutate(code.trim());
                                    }
                                } }), _jsx("button", { className: "btn btn-primary", onClick: () => addMut.mutate(code.trim()), disabled: !code.trim() || addMut.isPending, children: addMut.isPending ? "拉取中…(约 5–15 秒)" : "添加" })] }), err && _jsxs("p", { style: { color: "#b91c1c", fontSize: 12 }, children: ["\u9519\u8BEF\uFF1A", err] }), _jsx("p", { className: "hint", children: "\u9996\u6B21\u6DFB\u52A0\u4F1A\u4ECE Tushare \u62C9\u4E0A\u5E02\u4EE5\u6765\u5168\u5386\u53F2 PE/PB/PS\uFF08\u7EA6 5\u201315 \u79D2\uFF09\u3002 \u884C\u4E1A\u81EA\u52A8\u4ECE Tushare \u53D6\uFF0C\u4F30\u503C\u951A\u6309\u884C\u4E1A\u81EA\u52A8\u9009\uFF08\u94F6\u884C/\u5730\u4EA7 \u2192 PB\uFF1B\u5468\u671F \u2192 PE \u5012\u7F6E\uFF1B\u8BA1\u7B97\u673A/\u4F20\u5A92 \u2192 PS\uFF1B\u5176\u4ED6 \u2192 PE\uFF09\u3002" })] }), _jsxs("section", { className: "settings-block", children: [_jsxs("h3", { children: ["\u81EA\u9009\u4E2A\u80A1\uFF08", items.length, "\uFF09"] }), list.isLoading ? (_jsx("p", { className: "empty", children: "\u52A0\u8F7D\u4E2D\u2026" })) : items.length === 0 ? (_jsx("p", { className: "empty", children: "\u8FD8\u6CA1\u6709\u81EA\u9009\u4E2A\u80A1\u3002\u5728\u4E0A\u65B9\u8F93\u5165\u4EE3\u7801\u6DFB\u52A0\u3002" })) : (_jsxs("table", { className: "table", children: [_jsx("thead", { children: _jsxs("tr", { children: [_jsx("th", { children: "\u4EE3\u7801" }), _jsx("th", { children: "\u540D\u79F0" }), _jsx("th", { children: "\u884C\u4E1A" }), _jsx("th", { children: "\u4F30\u503C\u951A" }), _jsx("th", { children: "\u6E29\u5EA6" }), _jsx("th", { children: "\u6863\u4F4D" }), _jsx("th", { children: "PE" }), _jsx("th", { children: "PB" }), _jsx("th", { children: "PS" }), _jsx("th", { children: "\u5386\u53F2" }), _jsx("th", {})] }) }), _jsx("tbody", { children: items.map((s) => {
                                    const temp = s.temperature ? parseFloat(s.temperature) : null;
                                    return (_jsxs("tr", { children: [_jsx("td", { children: _jsx(Link, { to: `/stocks/${encodeURIComponent(s.code)}`, children: _jsx("strong", { children: s.code }) }) }), _jsx("td", { children: s.name }), _jsx("td", { children: s.industry ?? "—" }), _jsx("td", { children: _jsx("span", { style: {
                                                        fontSize: 11, padding: "1px 6px",
                                                        background: "#e0f2fe", color: "#075985",
                                                        borderRadius: 4,
                                                    }, children: ANCHOR_LABEL[s.anchor] ?? s.anchor }) }), _jsx("td", { children: temp != null ? (_jsx("span", { style: {
                                                        background: temperatureColor(temp.toString()),
                                                        color: "white", padding: "1px 8px",
                                                        borderRadius: 4, fontSize: 11,
                                                    }, children: temp.toFixed(1) })) : "—" }), _jsx("td", { children: s.tier ? tierLabel(s.tier) : "—" }), _jsx("td", { children: s.pe_ttm ? parseFloat(s.pe_ttm).toFixed(2) : "—" }), _jsx("td", { children: s.pb ? parseFloat(s.pb).toFixed(2) : "—" }), _jsx("td", { children: s.ps_ttm ? parseFloat(s.ps_ttm).toFixed(2) : "—" }), _jsxs("td", { children: [s.actual_history_years.toFixed(1), "y"] }), _jsx("td", { children: _jsx("button", { className: "btn", onClick: () => {
                                                        if (confirm(`确认移除 ${s.code} ${s.name}？历史数据会一并删除。`)) {
                                                            removeMut.mutate(s.code);
                                                        }
                                                    }, disabled: removeMut.isPending, style: { fontSize: 11, padding: "2px 6px" }, children: "\u79FB\u9664" }) })] }, s.code));
                                }) })] }))] })] }));
}
