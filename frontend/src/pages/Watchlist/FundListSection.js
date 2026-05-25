import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { useState } from "react";
import { addActiveFund, listFunds, removeActiveFund } from "@/api/funds";
import { temperatureColor, tierLabel } from "@/utils/temperature";
const TYPE_LABEL = {
    ETF: "场内 ETF",
    INDEX_FUND: "场外指数",
    ACTIVE_FUND: "场外主动",
};
const TYPE_COLOR = {
    ETF: { bg: "#dcfce7", fg: "#166534" },
    INDEX_FUND: { bg: "#dbeafe", fg: "#1e40af" },
    ACTIVE_FUND: { bg: "#fef3c7", fg: "#92400e" },
};
export default function FundListSection() {
    const qc = useQueryClient();
    const [code, setCode] = useState("");
    const [err, setErr] = useState(null);
    const list = useQuery({ queryKey: ["funds"], queryFn: listFunds });
    const addMut = useMutation({
        mutationFn: (c) => addActiveFund(c),
        onSuccess: () => {
            setCode("");
            setErr(null);
            qc.invalidateQueries({ queryKey: ["funds"] });
        },
        onError: (e) => setErr(e.message),
    });
    const removeMut = useMutation({
        mutationFn: (c) => removeActiveFund(c),
        onSuccess: () => qc.invalidateQueries({ queryKey: ["funds"] }),
    });
    if (list.isLoading)
        return _jsx("p", { className: "empty", children: "\u52A0\u8F7D\u4E2D\u2026" });
    const items = list.data?.items ?? [];
    // 按 fund_type 分组（主动基金特别置顶，因为是用户自己加的）
    const active = items.filter((f) => f.fund_type === "ACTIVE_FUND");
    const passive = items.filter((f) => f.fund_type !== "ACTIVE_FUND");
    const byMarket = {};
    for (const f of passive) {
        (byMarket[f.market] = byMarket[f.market] ?? []).push(f);
    }
    return (_jsxs("div", { children: [_jsxs("section", { className: "settings-block", children: [_jsx("h3", { children: "\u6DFB\u52A0\u573A\u5916\u4E3B\u52A8\u57FA\u91D1\uFF08SRS R12 M7-B\uFF09" }), _jsxs("div", { style: { display: "flex", gap: 8, alignItems: "center" }, children: [_jsx("input", { placeholder: "\u57FA\u91D1\u4EE3\u7801\uFF08\u5982 005827 \u6613\u65B9\u8FBE\u84DD\u7B79\u7CBE\u9009\uFF09", value: code, onChange: (e) => setCode(e.target.value), style: { flex: 1, maxWidth: 320, padding: "4px 8px" }, disabled: addMut.isPending, onKeyDown: (e) => {
                                    if (e.key === "Enter" && code.trim() && !addMut.isPending) {
                                        addMut.mutate(code.trim());
                                    }
                                } }), _jsx("button", { className: "btn btn-primary", onClick: () => addMut.mutate(code.trim()), disabled: !code.trim() || addMut.isPending, children: addMut.isPending ? "拉取中…(约 5–10 秒)" : "添加" })] }), err && _jsx("p", { style: { color: "#b91c1c", fontSize: 12 }, children: err }), _jsxs("p", { className: "hint", children: ["\u6E29\u5EA6\u6309 ", _jsx("strong", { children: "NAV 5 \u5E74\u5386\u53F2\u767E\u5206\u4F4D" }), "\u8BA1\u7B97\uFF08\u9AD8\u767E\u5206\u4F4D = NAV \u5904\u4E8E\u81EA\u8EAB\u5386\u53F2\u9AD8\u4F4D\uFF09\u3002 \u26A0 ", _jsx("strong", { children: "\u4EC5\u53CD\u6620 NAV \u4E0E\u81EA\u8EAB\u6BD4\uFF0C\u4E0D\u53CD\u6620\u6301\u4ED3\u4F30\u503C\u6C34\u4F4D" }), "\uFF08\u5B63\u62A5\u62AB\u9732 70% \u6301\u4ED3\u4E14\u6EDE\u540E\uFF0C\u4E0D\u63A5\u5165\uFF09\u3002 ETF / \u573A\u5916\u6307\u6570\u57FA\u91D1\u6E29\u5EA6\u4ECD\u6302\u8DDF\u8E2A\u6307\u6570\u3002"] })] }), active.length > 0 && (_jsxs("section", { className: "settings-block", children: [_jsxs("h3", { children: ["\u573A\u5916\u4E3B\u52A8\u57FA\u91D1\uFF08", active.length, "\uFF09"] }), _jsxs("table", { className: "table", children: [_jsx("thead", { children: _jsxs("tr", { children: [_jsx("th", { children: "\u4EE3\u7801" }), _jsx("th", { children: "\u57FA\u91D1\u540D\u79F0" }), _jsx("th", { children: "\u57FA\u91D1\u7ECF\u7406" }), _jsx("th", { children: "\u6210\u7ACB\u65E5" }), _jsx("th", { children: "\u5386\u53F2" }), _jsx("th", { children: "\u6700\u65B0 NAV" }), _jsx("th", { children: "\u6E29\u5EA6" }), _jsx("th", { children: "\u6863\u4F4D" }), _jsx("th", { children: "\u8BF4\u660E" }), _jsx("th", {})] }) }), _jsx("tbody", { children: active.map((f) => {
                                    const temp = f.temperature ? parseFloat(f.temperature) : null;
                                    return (_jsxs("tr", { children: [_jsx("td", { children: _jsx(Link, { to: `/funds/${encodeURIComponent(f.code)}`, children: _jsx("strong", { children: f.code }) }) }), _jsx("td", { children: f.name }), _jsx("td", { children: f.fund_manager ?? "—" }), _jsx("td", { children: f.setup_date ?? "—" }), _jsx("td", { children: f.actual_history_years != null ? f.actual_history_years.toFixed(1) + "y" : "—" }), _jsx("td", { children: f.nav_latest ? parseFloat(f.nav_latest).toFixed(4) : "—" }), _jsx("td", { children: temp != null ? (_jsx("span", { style: {
                                                        background: temperatureColor(temp.toString()),
                                                        color: "white", padding: "1px 8px",
                                                        borderRadius: 4, fontSize: 11,
                                                    }, children: temp.toFixed(1) })) : "—" }), _jsx("td", { children: f.tier ? tierLabel(f.tier) : "—" }), _jsx("td", { style: { fontSize: 11, color: "#92400e" }, title: "NAV 5y \u767E\u5206\u4F4D\uFF0C\u4E0D\u53CD\u6620\u6301\u4ED3\u6C34\u4F4D", children: "\u26A0 NAV \u81EA\u6BD4" }), _jsx("td", { children: _jsx("button", { className: "btn", onClick: () => {
                                                        if (confirm(`确认移除 ${f.code} ${f.name}？NAV 历史会一并删除。`)) {
                                                            removeMut.mutate(f.code);
                                                        }
                                                    }, style: { fontSize: 11, padding: "2px 6px" }, children: "\u79FB\u9664" }) })] }, f.code));
                                }) })] })] })), _jsxs("p", { className: "hint", style: { marginTop: 16 }, children: ["\u4EE5\u4E0B\u4E3A\u5185\u7F6E ETF / \u573A\u5916\u6307\u6570\u57FA\u91D1\uFF08", passive.length, " \u53EA\uFF09\uFF0C\u6E29\u5EA6\u76F4\u63A5\u7EE7\u627F\u81EA", _jsx("strong", { children: "\u8DDF\u8E2A\u6307\u6570" }), "\u3002"] }), ["A", "HK", "US"].map((mkt) => {
                const arr = byMarket[mkt] ?? [];
                if (arr.length === 0)
                    return null;
                return (_jsxs("section", { className: "settings-block", children: [_jsxs("h3", { children: [mkt, " \u5E02\u573A\uFF08", arr.length, "\uFF09"] }), _jsxs("table", { className: "table", children: [_jsx("thead", { children: _jsxs("tr", { children: [_jsx("th", { children: "\u4EE3\u7801" }), _jsx("th", { children: "\u540D\u79F0" }), _jsx("th", { children: "\u7C7B\u578B" }), _jsx("th", { children: "\u8DDF\u8E2A\u6307\u6570" }), _jsx("th", { children: "\u6E29\u5EA6" }), _jsx("th", { children: "\u6863\u4F4D" }), _jsx("th", { children: "PE" }), _jsx("th", { children: "PB" }), _jsx("th", { children: "\u8D39\u7387" })] }) }), _jsx("tbody", { children: arr.map((f) => {
                                        const temp = f.temperature ? parseFloat(f.temperature) : null;
                                        const c = TYPE_COLOR[f.fund_type] ?? TYPE_COLOR.ETF;
                                        return (_jsxs("tr", { children: [_jsx("td", { children: _jsx("strong", { children: f.code }) }), _jsx("td", { children: f.name }), _jsx("td", { children: _jsx("span", { style: {
                                                            fontSize: 11, padding: "1px 6px",
                                                            background: c.bg, color: c.fg, borderRadius: 4,
                                                        }, children: TYPE_LABEL[f.fund_type] ?? f.fund_type }) }), _jsx("td", { children: f.tracks_index_code ? (_jsxs(Link, { to: `/indices/${encodeURIComponent(f.tracks_index_code)}`, children: [f.tracks_index_code, " ", f.tracks_index_name] })) : "—" }), _jsx("td", { children: temp != null ? (_jsx("span", { style: {
                                                            background: temperatureColor(temp.toString()),
                                                            color: "white", padding: "1px 8px",
                                                            borderRadius: 4, fontSize: 11,
                                                        }, children: temp.toFixed(1) })) : "—" }), _jsx("td", { children: f.tier ? tierLabel(f.tier) : "—" }), _jsx("td", { children: f.pe_ttm ? parseFloat(f.pe_ttm).toFixed(2) : "—" }), _jsx("td", { children: f.pb ? parseFloat(f.pb).toFixed(2) : "—" }), _jsx("td", { children: f.fee_rate ? (parseFloat(f.fee_rate) * 100).toFixed(2) + "%" : "—" })] }, f.code));
                                    }) })] })] }, mkt));
            })] }));
}
