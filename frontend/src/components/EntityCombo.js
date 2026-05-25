import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect, useRef, useState } from "react";
import { search } from "@/api/search";
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
export default function EntityCombo({ value, onChange, types, placeholder }) {
    const [open, setOpen] = useState(false);
    const [query, setQuery] = useState("");
    const [hits, setHits] = useState([]);
    const [loading, setLoading] = useState(false);
    const containerRef = useRef(null);
    // 受控同步：value 变化时刷新输入框文字
    useEffect(() => {
        if (value) {
            setQuery(`${value.code} ${value.name}`);
        }
    }, [value]);
    // 关闭下拉：点击外部
    useEffect(() => {
        const onClick = (e) => {
            if (!containerRef.current?.contains(e.target))
                setOpen(false);
        };
        document.addEventListener("mousedown", onClick);
        return () => document.removeEventListener("mousedown", onClick);
    }, []);
    // 输入防抖搜索
    useEffect(() => {
        const q = query.trim();
        if (!q || (value && `${value.code} ${value.name}` === query)) {
            // 没输入或文本与已选完全一致 → 不搜索
            return;
        }
        setLoading(true);
        const t = setTimeout(() => {
            search(q, types, 12)
                .then((r) => setHits(r.items))
                .catch(() => setHits([]))
                .finally(() => setLoading(false));
        }, 200);
        return () => clearTimeout(t);
    }, [query, types, value]);
    return (_jsxs("div", { ref: containerRef, style: { position: "relative", flex: "1 1 280px" }, children: [_jsx("input", { value: query, onChange: (e) => {
                    setQuery(e.target.value);
                    setOpen(true);
                    if (value)
                        onChange(null);
                }, onFocus: () => setOpen(true), placeholder: placeholder ?? "输入代码或中文名称（如 茅台 / 000300 / 红利）", style: { width: "100%", padding: "4px 8px", boxSizing: "border-box" } }), open && query.trim() && (_jsxs("div", { style: {
                    position: "absolute", top: "100%", left: 0, right: 0, zIndex: 100,
                    background: "white", border: "1px solid #d1d5db", borderRadius: 4,
                    marginTop: 2, maxHeight: 320, overflowY: "auto",
                    boxShadow: "0 4px 12px rgba(0,0,0,0.08)",
                }, children: [loading && (_jsx("div", { style: { padding: "8px 10px", color: "#6b7280", fontSize: 12 }, children: "\u641C\u7D22\u4E2D\u2026" })), !loading && hits.length === 0 && (_jsx("div", { style: { padding: "8px 10px", color: "#9ca3af", fontSize: 12 }, children: "\u65E0\u5339\u914D\uFF08\u4F60\u4E5F\u53EF\u4EE5\u76F4\u63A5\u8F93\u5165\u5B8C\u6574\u4EE3\u7801\u540E\u63D0\u4EA4\uFF09" })), !loading && hits.map((h) => {
                        const c = TYPE_COLOR[h.entity_type];
                        return (_jsxs("div", { onMouseDown: (e) => {
                                e.preventDefault();
                                onChange(h);
                                setQuery(`${h.code} ${h.name}`);
                                setOpen(false);
                            }, style: {
                                display: "flex", alignItems: "center", gap: 8,
                                padding: "6px 10px", cursor: "pointer", fontSize: 13,
                                borderBottom: "1px solid #f3f4f6",
                            }, onMouseEnter: (e) => (e.currentTarget.style.background = "#f9fafb"), onMouseLeave: (e) => (e.currentTarget.style.background = "white"), children: [_jsx("span", { style: {
                                        fontSize: 10, padding: "1px 5px",
                                        background: c.bg, color: c.fg, borderRadius: 3, minWidth: 28, textAlign: "center",
                                    }, children: TYPE_LABEL[h.entity_type] }), _jsx("strong", { style: { minWidth: 100 }, children: h.code }), _jsx("span", { style: { flex: 1 }, children: h.name }), h.in_local && (_jsx("span", { title: "\u5DF2\u5728\u672C\u5730\u8DDF\u8E2A\u5E93", style: {
                                        fontSize: 9, padding: "1px 4px",
                                        background: "#dcfce7", color: "#166534",
                                        borderRadius: 2,
                                    }, children: "\u2713 \u5DF2\u8DDF\u8E2A" })), h.extra && (_jsx("span", { style: { fontSize: 11, color: "#9ca3af" }, children: h.extra }))] }, `${h.entity_type}-${h.code}`));
                    })] }))] }));
}
