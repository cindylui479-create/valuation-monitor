import { useEffect, useRef, useState } from "react";
import { search, type SearchHit } from "@/api/search";

interface Props {
  /** 受控选中实体（含 entity_type + code + name）。父组件控制。 */
  value: SearchHit | null;
  onChange: (hit: SearchHit | null) => void;
  /** 限制类型（不传则搜全部）。 */
  types?: ("INDEX" | "STOCK" | "FUND")[];
  placeholder?: string;
}

const TYPE_LABEL: Record<string, string> = {
  INDEX: "指数",
  STOCK: "个股",
  FUND: "基金",
};
const TYPE_COLOR: Record<string, { bg: string; fg: string }> = {
  INDEX: { bg: "#dbeafe", fg: "#1e40af" },
  STOCK: { bg: "#fce7f3", fg: "#9d174d" },
  FUND: { bg: "#fef3c7", fg: "#92400e" },
};

export default function EntityCombo({ value, onChange, types, placeholder }: Props) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<SearchHit[]>([]);
  const [loading, setLoading] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // 受控同步：value 变化时刷新输入框文字
  useEffect(() => {
    if (value) {
      setQuery(`${value.code} ${value.name}`);
    }
  }, [value]);

  // 关闭下拉：点击外部
  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (!containerRef.current?.contains(e.target as Node)) setOpen(false);
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

  return (
    <div ref={containerRef} style={{ position: "relative", flex: "1 1 280px" }}>
      <input
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          setOpen(true);
          if (value) onChange(null);
        }}
        onFocus={() => setOpen(true)}
        placeholder={placeholder ?? "输入代码或中文名称（如 茅台 / 000300 / 红利）"}
        style={{ width: "100%", padding: "4px 8px", boxSizing: "border-box" }}
      />
      {open && query.trim() && (
        <div style={{
          position: "absolute", top: "100%", left: 0, right: 0, zIndex: 100,
          background: "white", border: "1px solid #d1d5db", borderRadius: 4,
          marginTop: 2, maxHeight: 320, overflowY: "auto",
          boxShadow: "0 4px 12px rgba(0,0,0,0.08)",
        }}>
          {loading && (
            <div style={{ padding: "8px 10px", color: "#6b7280", fontSize: 12 }}>搜索中…</div>
          )}
          {!loading && hits.length === 0 && (
            <div style={{ padding: "8px 10px", color: "#9ca3af", fontSize: 12 }}>
              无匹配（你也可以直接输入完整代码后提交）
            </div>
          )}
          {!loading && hits.map((h) => {
            const c = TYPE_COLOR[h.entity_type];
            return (
              <div
                key={`${h.entity_type}-${h.code}`}
                onMouseDown={(e) => {
                  e.preventDefault();
                  onChange(h);
                  setQuery(`${h.code} ${h.name}`);
                  setOpen(false);
                }}
                style={{
                  display: "flex", alignItems: "center", gap: 8,
                  padding: "6px 10px", cursor: "pointer", fontSize: 13,
                  borderBottom: "1px solid #f3f4f6",
                }}
                onMouseEnter={(e) => (e.currentTarget.style.background = "#f9fafb")}
                onMouseLeave={(e) => (e.currentTarget.style.background = "white")}
              >
                <span style={{
                  fontSize: 10, padding: "1px 5px",
                  background: c.bg, color: c.fg, borderRadius: 3, minWidth: 28, textAlign: "center",
                }}>{TYPE_LABEL[h.entity_type]}</span>
                <strong style={{ minWidth: 100 }}>{h.code}</strong>
                <span style={{ flex: 1 }}>{h.name}</span>
                {h.extra && (
                  <span style={{ fontSize: 11, color: "#9ca3af" }}>{h.extra}</span>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
