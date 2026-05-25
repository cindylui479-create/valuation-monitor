import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createDCAPlan, updateDCAPlan } from "@/api/dca";
import { fetchIndicesList } from "@/api/indicesList";
const FREQ_LABEL = {
    WEEKLY: "每周",
    BIWEEKLY: "每两周",
    MONTHLY: "每月",
};
export default function DCAPlanEditor({ open, initial, presetIndexCode, onClose }) {
    const qc = useQueryClient();
    const { data: indices } = useQuery({
        queryKey: ["indices-list"],
        queryFn: fetchIndicesList,
        enabled: open,
    });
    const [form, setForm] = useState({
        index_code: "",
        fund_code: null,
        amount: "2000",
        frequency: "MONTHLY",
        day_of_period: 10,
        start_date: new Date().toISOString().slice(0, 10),
        enabled: true,
    });
    const [error, setError] = useState(null);
    useEffect(() => {
        if (!open)
            return;
        if (initial) {
            setForm({
                index_code: initial.index_code,
                fund_code: initial.fund_code,
                amount: initial.amount,
                frequency: initial.frequency,
                day_of_period: initial.day_of_period,
                start_date: initial.start_date,
                enabled: initial.enabled,
            });
        }
        else if (presetIndexCode) {
            setForm((f) => ({ ...f, index_code: presetIndexCode }));
        }
    }, [open, initial, presetIndexCode]);
    const saveMut = useMutation({
        mutationFn: async () => {
            if (initial) {
                return updateDCAPlan(initial.id, {
                    amount: form.amount,
                    frequency: form.frequency,
                    day_of_period: form.day_of_period,
                    enabled: form.enabled,
                    fund_code: form.fund_code,
                });
            }
            return createDCAPlan(form);
        },
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ["dca-plans"] });
            qc.invalidateQueries({ queryKey: ["dca-upcoming"] });
            onClose();
        },
        onError: (e) => setError(e.message),
    });
    if (!open)
        return null;
    const isWeekly = form.frequency === "WEEKLY" || form.frequency === "BIWEEKLY";
    return (_jsx("div", { className: "dialog-backdrop", onClick: onClose, children: _jsxs("div", { className: "dialog", onClick: (e) => e.stopPropagation(), children: [_jsx("h3", { children: initial ? "编辑定投计划" : "新建定投计划" }), _jsxs("form", { onSubmit: (e) => {
                        e.preventDefault();
                        setError(null);
                        saveMut.mutate();
                    }, children: [_jsxs("label", { className: "field", children: [_jsx("span", { children: "\u6307\u6570" }), _jsxs("select", { value: form.index_code, disabled: !!initial, onChange: (e) => setForm({ ...form, index_code: e.target.value }), required: true, children: [_jsx("option", { value: "", children: "\u2014 \u9009\u62E9 \u2014" }), (indices ?? []).map((i) => (_jsxs("option", { value: i.code, children: ["[", i.market, "] ", i.name, " (", i.code, ")"] }, i.code)))] })] }), _jsxs("label", { className: "field", children: [_jsx("span", { children: "\u57FA\u7840\u91D1\u989D" }), _jsx("input", { type: "number", min: 1, step: "0.01", value: form.amount, onChange: (e) => setForm({ ...form, amount: e.target.value }), required: true })] }), _jsxs("label", { className: "field", children: [_jsx("span", { children: "\u9891\u7387" }), _jsx("select", { value: form.frequency, onChange: (e) => setForm({ ...form, frequency: e.target.value }), children: Object.entries(FREQ_LABEL).map(([k, v]) => (_jsx("option", { value: k, children: v }, k))) })] }), _jsxs("label", { className: "field", children: [_jsx("span", { children: isWeekly ? "周几（1-7=周一-周日）" : "每月日（1-28）" }), _jsx("input", { type: "number", min: 1, max: isWeekly ? 7 : 28, value: form.day_of_period, onChange: (e) => setForm({ ...form, day_of_period: Number(e.target.value) }), required: true })] }), _jsxs("label", { className: "field", children: [_jsx("span", { children: "\u8D77\u59CB\u65E5" }), _jsx("input", { type: "date", value: form.start_date, disabled: !!initial, onChange: (e) => setForm({ ...form, start_date: e.target.value }), required: true })] }), _jsxs("label", { className: "field", children: [_jsx("span", { children: "\u542F\u7528" }), _jsx("input", { type: "checkbox", checked: form.enabled, onChange: (e) => setForm({ ...form, enabled: e.target.checked }) })] }), error && _jsx("p", { className: "error-msg", children: error }), _jsxs("div", { className: "dialog-actions", children: [_jsx("button", { type: "button", className: "btn", onClick: onClose, children: "\u53D6\u6D88" }), _jsx("button", { type: "submit", className: "btn btn-primary", disabled: saveMut.isPending, children: saveMut.isPending ? "保存中…" : "保存" })] })] })] }) }));
}
