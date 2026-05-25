import { jsxs as _jsxs, jsx as _jsx } from "react/jsx-runtime";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { deleteOverride, fetchOverride, putOverride, } from "@/api/overrides";
export default function ThresholdOverrideDialog({ open, indexCode, onClose }) {
    const qc = useQueryClient();
    const { data } = useQuery({
        queryKey: ["override", indexCode],
        queryFn: () => fetchOverride(indexCode),
        enabled: open && !!indexCode,
    });
    const [b, setB] = useState({
        extreme_low_upper: "0.10",
        low_upper: "0.30",
        high_lower: "0.70",
        extreme_high_lower: "0.90",
    });
    const [error, setError] = useState(null);
    useEffect(() => {
        if (data) {
            setB({
                extreme_low_upper: data.boundaries.extreme_low_upper,
                low_upper: data.boundaries.low_upper,
                high_lower: data.boundaries.high_lower,
                extreme_high_lower: data.boundaries.extreme_high_lower,
            });
        }
    }, [data]);
    const saveMut = useMutation({
        mutationFn: () => putOverride(indexCode, b),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ["override", indexCode] });
            qc.invalidateQueries({ queryKey: ["overview"] });
            qc.invalidateQueries({ queryKey: ["index-detail", indexCode] });
            onClose();
        },
        onError: (e) => setError(e.message),
    });
    const resetMut = useMutation({
        mutationFn: () => deleteOverride(indexCode),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ["override", indexCode] });
            qc.invalidateQueries({ queryKey: ["overview"] });
            onClose();
        },
        onError: (e) => setError(e.message),
    });
    if (!open)
        return null;
    const handleSubmit = (e) => {
        e.preventDefault();
        setError(null);
        saveMut.mutate();
    };
    return (_jsx("div", { className: "dialog-backdrop", onClick: onClose, children: _jsxs("div", { className: "dialog", onClick: (e) => e.stopPropagation(), children: [_jsxs("h3", { children: ["\u4E2A\u6027\u5316\u9608\u503C \u2014 ", indexCode] }), _jsxs("p", { className: "hint", children: ["\u8C03\u6574\u540E\uFF0C\u5B9A\u6295\u8054\u52A8\u89C4\u5219\u4E0E\u4FE1\u53F7\u5224\u5B9A\u5C06\u968F\u4E4B\u540C\u6B65\uFF08SRS D6 \u65B9\u6848 A\uFF09\u3002", data?.is_default ? "当前使用默认边界。" : "当前已有自定义边界。"] }), _jsxs("form", { onSubmit: handleSubmit, children: [[
                            ["extreme_low_upper", "极度低估上限"],
                            ["low_upper", "低估上限"],
                            ["high_lower", "高估下限"],
                            ["extreme_high_lower", "极度高估下限"],
                        ].map(([k, label]) => (_jsxs("label", { className: "field", children: [_jsx("span", { children: label }), _jsx("input", { type: "number", step: "0.01", min: 0, max: 1, value: b[k], onChange: (e) => setB({ ...b, [k]: e.target.value }), required: true })] }, k))), error && _jsx("p", { className: "error-msg", children: error }), _jsxs("div", { className: "dialog-actions", children: [_jsx("button", { type: "button", className: "btn", onClick: onClose, children: "\u53D6\u6D88" }), !data?.is_default && (_jsx("button", { type: "button", className: "btn", onClick: () => resetMut.mutate(), disabled: resetMut.isPending, children: "\u91CD\u7F6E\u4E3A\u9ED8\u8BA4" })), _jsx("button", { type: "submit", className: "btn btn-primary", disabled: saveMut.isPending, children: saveMut.isPending ? "保存中…" : "保存" })] })] })] }) }));
}
