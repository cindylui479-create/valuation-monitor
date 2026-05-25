import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { useState } from "react";
import { deleteDCAPlan, fetchDCAPlans, fetchDCAStats, fetchUpcoming, markDone, markSkipped, } from "@/api/dca";
import { formatNumber } from "@/utils/decimal";
import { temperatureColor } from "@/utils/temperature";
import DCAPlanEditor from "./DCAPlanEditor";
const FREQ_LABEL = {
    WEEKLY: "每周",
    BIWEEKLY: "每两周",
    MONTHLY: "每月",
};
export default function DCA() {
    const qc = useQueryClient();
    const [editorOpen, setEditorOpen] = useState(false);
    const [editing, setEditing] = useState(null);
    const upcoming = useQuery({
        queryKey: ["dca-upcoming"],
        queryFn: () => fetchUpcoming(7),
    });
    const plans = useQuery({ queryKey: ["dca-plans"], queryFn: fetchDCAPlans });
    const stats = useQuery({ queryKey: ["dca-stats"], queryFn: fetchDCAStats });
    const refreshAll = () => {
        qc.invalidateQueries({ queryKey: ["dca-upcoming"] });
        qc.invalidateQueries({ queryKey: ["dca-stats"] });
    };
    const doneMut = useMutation({
        mutationFn: (id) => markDone(id),
        onSuccess: refreshAll,
    });
    const skipMut = useMutation({
        mutationFn: (id) => markSkipped(id),
        onSuccess: refreshAll,
    });
    const delMut = useMutation({
        mutationFn: (id) => deleteDCAPlan(id),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ["dca-plans"] });
            refreshAll();
        },
    });
    return (_jsxs("div", { className: "dca-page", children: [_jsxs("div", { className: "page-header", children: [_jsx("h2", { children: "\u5B9A\u6295\u8BA1\u5212" }), _jsx("button", { className: "btn btn-primary", onClick: () => {
                            setEditing(null);
                            setEditorOpen(true);
                        }, children: "\u65B0\u5EFA\u5B9A\u6295" })] }), stats.data && stats.data.plans.length > 0 && (_jsxs("section", { className: "dca-stats", children: [_jsxs("div", { className: "kpi-row", children: [_jsxs("div", { className: "kpi", children: [_jsx("div", { className: "label", children: "\u7D2F\u8BA1\u5DF2\u6295\u5165" }), _jsxs("div", { className: "value", children: ["\u00A5", formatNumber(stats.data.total_done_amount, 2)] })] }), _jsxs("div", { className: "kpi", children: [_jsx("div", { className: "label", children: "\u7D2F\u8BA1\u8DF3\u8FC7" }), _jsxs("div", { className: "value", children: ["\u00A5", formatNumber(stats.data.total_skipped_amount, 2)] })] }), _jsxs("div", { className: "kpi", children: [_jsx("div", { className: "label", children: "\u6D3B\u8DC3\u8BA1\u5212" }), _jsx("div", { className: "value", children: stats.data.plans.length })] })] }), _jsxs("details", { children: [_jsx("summary", { children: "\u5404\u8BA1\u5212\u660E\u7EC6\uFF08\u70B9\u51FB\u5C55\u5F00\uFF09" }), _jsxs("table", { className: "table", children: [_jsx("thead", { children: _jsxs("tr", { children: [_jsx("th", { children: "\u6307\u6570" }), _jsx("th", { children: "\u5DF2\u6267\u884C / \u8DF3\u8FC7 / \u5F85\u6267\u884C" }), _jsx("th", { children: "\u7D2F\u8BA1\u6295\u5165" }), _jsx("th", { children: "\u56E0\u8C03\u6574\u7701\u4E0B" }), _jsx("th", { children: "\u8DF3\u8FC7\u7387" }), _jsx("th", { children: "\u5E73\u5747 multiplier" })] }) }), _jsx("tbody", { children: stats.data.plans.map((p) => {
                                            const saved = parseFloat(p.base_total_if_no_adjustment) -
                                                parseFloat(p.done_total_amount) -
                                                parseFloat(p.skipped_total_amount);
                                            return (_jsxs("tr", { children: [_jsx("td", { children: _jsx(Link, { to: `/indices/${encodeURIComponent(p.index_code)}`, children: p.index_name }) }), _jsxs("td", { children: [p.done_count, " / ", p.skipped_count, " / ", p.pending_count] }), _jsxs("td", { children: ["\u00A5", formatNumber(p.done_total_amount, 2)] }), _jsxs("td", { children: ["\u00A5", saved.toFixed(2)] }), _jsxs("td", { children: [(parseFloat(p.skip_ratio) * 100).toFixed(1), "%"] }), _jsxs("td", { children: ["\u00D7", formatNumber(p.average_multiplier, 2)] })] }, p.plan_id));
                                        }) })] })] })] })), _jsxs("section", { className: "upcoming-section", children: [_jsx("h3", { children: "\u672A\u6765 7 \u5929\u63D0\u9192" }), upcoming.data && upcoming.data.items.length === 0 ? (_jsx("p", { className: "empty", children: "\u6682\u65E0\u5F85\u6267\u884C\u63D0\u9192" })) : (_jsx("div", { className: "reminder-grid", children: (upcoming.data?.items ?? []).map((e) => (_jsxs("div", { className: "reminder-card", children: [_jsxs("div", { className: "card-head", children: [_jsx(Link, { to: `/indices/${encodeURIComponent(e.index_code)}`, children: _jsx("strong", { children: e.index_name }) }), _jsx("span", { className: "tier-badge", style: { backgroundColor: temperatureColor(e.temperature) }, children: e.tier_at_decision })] }), _jsxs("div", { className: "card-body", children: [_jsxs("div", { children: ["\u5B9A\u6295\u65E5 ", _jsx("strong", { children: e.actual_date }), e.scheduled_date !== e.actual_date && (_jsxs("span", { className: "hint", children: [" \uFF08\u987A\u5EF6\u81EA ", e.scheduled_date, "\uFF09"] }))] }), _jsxs("div", { className: "amount-line", children: [_jsx("span", { className: "label", children: "\u57FA\u7840" }), _jsxs("span", { children: ["\u00A5", formatNumber(e.base_amount, 2)] }), _jsxs("span", { className: "label", children: ["\u00D7", formatNumber(e.multiplier, 1), " \u21D2"] }), _jsxs("span", { className: "big", children: ["\u00A5", formatNumber(e.adjusted_amount, 2)] })] })] }), _jsxs("div", { className: "card-actions", children: [_jsx("button", { className: "btn btn-primary", onClick: () => doneMut.mutate(e.id), disabled: doneMut.isPending, children: "\u6807\u8BB0\u5DF2\u6267\u884C" }), _jsx("button", { className: "btn", onClick: () => skipMut.mutate(e.id), disabled: skipMut.isPending, children: "\u8DF3\u8FC7\u672C\u671F" })] })] }, e.id))) }))] }), _jsxs("section", { className: "plans-section", children: [_jsxs("h3", { children: ["\u6240\u6709\u8BA1\u5212 (", plans.data?.length ?? 0, ")"] }), plans.data && plans.data.length === 0 ? (_jsx("p", { className: "empty", children: "\u8FD8\u6CA1\u6709\u5B9A\u6295\u8BA1\u5212\u3002\u70B9\u51FB\u53F3\u4E0A\u89D2\"\u65B0\u5EFA\u5B9A\u6295\"\u5F00\u59CB\u3002" })) : (_jsxs("table", { className: "table", children: [_jsx("thead", { children: _jsxs("tr", { children: [_jsx("th", { children: "\u6307\u6570" }), _jsx("th", { children: "\u9891\u7387" }), _jsx("th", { children: "\u89E6\u53D1\u65E5" }), _jsx("th", { children: "\u91D1\u989D" }), _jsx("th", { children: "\u8D77\u59CB" }), _jsx("th", { children: "\u72B6\u6001" }), _jsx("th", {})] }) }), _jsx("tbody", { children: (plans.data ?? []).map((p) => (_jsxs("tr", { children: [_jsxs("td", { children: [_jsx(Link, { to: `/indices/${encodeURIComponent(p.index_code)}`, children: p.index_name }), _jsx("div", { className: "cell-code", children: p.index_code })] }), _jsx("td", { children: FREQ_LABEL[p.frequency] }), _jsx("td", { children: p.frequency === "MONTHLY"
                                                ? `每月 ${p.day_of_period} 日`
                                                : `周${"一二三四五六日".charAt(p.day_of_period - 1)}` }), _jsxs("td", { children: ["\u00A5", formatNumber(p.amount, 2)] }), _jsx("td", { children: p.start_date }), _jsx("td", { children: p.enabled ? "启用" : "停用" }), _jsxs("td", { children: [_jsx("button", { className: "btn", onClick: () => {
                                                        setEditing(p);
                                                        setEditorOpen(true);
                                                    }, children: "\u7F16\u8F91" }), _jsx("button", { className: "btn", onClick: () => {
                                                        if (confirm(`删除"${p.index_name}"定投计划？`)) {
                                                            delMut.mutate(p.id);
                                                        }
                                                    }, children: "\u5220\u9664" })] })] }, p.id))) })] }))] }), _jsx(DCAPlanEditor, { open: editorOpen, initial: editing, onClose: () => setEditorOpen(false) })] }));
}
