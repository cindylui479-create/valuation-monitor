import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { useState } from "react";
import {
  addHolding,
  deleteHolding,
  fetchPortfolio,
  updateHolding,
  type EntityType,
} from "@/api/holdings";
import type { SearchHit } from "@/api/search";
import EntityCombo from "@/components/EntityCombo";
import {
  isPriceFallback,
  temperatureColor,
  tierLabel,
} from "@/utils/temperature";

const TYPE_LABEL: Record<EntityType, string> = {
  INDEX: "指数",
  STOCK: "个股",
  FUND: "基金",
};
const TYPE_COLOR: Record<EntityType, { bg: string; fg: string }> = {
  INDEX: { bg: "#dbeafe", fg: "#1e40af" },
  STOCK: { bg: "#fce7f3", fg: "#9d174d" },
  FUND: { bg: "#fef3c7", fg: "#92400e" },
};

const TIER_ORDER = ["极度低估", "低估", "合理", "高估", "极度高估"];

function detailPath(t: EntityType, code: string): string {
  if (t === "INDEX") return `/indices/${encodeURIComponent(code)}`;
  if (t === "STOCK") return `/stocks/${encodeURIComponent(code)}`;
  return `/funds/${encodeURIComponent(code)}`;
}

type Mode = "value" | "quantity";

export default function HoldingListSection() {
  const qc = useQueryClient();
  const [selected, setSelected] = useState<SearchHit | null>(null);
  const [mode, setMode] = useState<Mode>("value");
  const [amount, setAmount] = useState("");          // 数字（金额或数量）
  const [note, setNote] = useState("");
  const [err, setErr] = useState<string | null>(null);

  const [editingId, setEditingId] = useState<number | null>(null);
  const [editMode, setEditMode] = useState<Mode>("value");
  const [editAmount, setEditAmount] = useState("");

  const portfolio = useQuery({
    queryKey: ["portfolio"],
    queryFn: fetchPortfolio,
    refetchInterval: 30_000,  // 30s 自动刷新一次，让数量模式持仓的市值跟随单价
  });

  const addMut = useMutation({
    mutationFn: () => {
      if (!selected) throw new Error("请先选择标的");
      const n = parseFloat(amount);
      if (!Number.isFinite(n) || n <= 0) throw new Error("数值必须 > 0");
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
    onError: (e: Error) => setErr(e.message),
  });

  const delMut = useMutation({
    mutationFn: (id: number) => deleteHolding(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["portfolio"] }),
  });

  const updMut = useMutation({
    mutationFn: () => {
      if (editingId == null) throw new Error("no id");
      const n = parseFloat(editAmount);
      if (!Number.isFinite(n) || n <= 0) throw new Error("数值必须 > 0");
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

  if (portfolio.isLoading) return <p className="empty">加载中…</p>;
  const data = portfolio.data;
  if (!data) return null;

  const total = parseFloat(data.total_value);
  const weightedTemp = data.weighted_temperature ? parseFloat(data.weighted_temperature) : null;
  const coverage = parseFloat(data.coverage_pct);

  return (
    <div>
      {/* 顶部加权卡片 */}
      <section className="latest-card" style={{ marginBottom: 16 }}>
        {weightedTemp != null && (
          <div
            className="tier-pill"
            style={{ backgroundColor: temperatureColor(weightedTemp.toString()) }}
          >
            组合温度
          </div>
        )}
        <div className="stat">
          <div className="label">总市值</div>
          <div className="value">¥{total.toLocaleString("zh-CN", { maximumFractionDigits: 0 })}</div>
        </div>
        <div className="stat">
          <div className="label">加权温度（按市值）</div>
          <div className="value">{weightedTemp != null ? weightedTemp.toFixed(1) : "—"}</div>
        </div>
        <div className="stat">
          <div className="label">温度覆盖率</div>
          <div className="value">{coverage.toFixed(0)}%</div>
        </div>
        <div className="stat">
          <div className="label">持仓项</div>
          <div className="value">{data.items.length}</div>
        </div>
      </section>

      {/* 档位分布 */}
      {Object.keys(data.tier_distribution).length > 0 && (
        <section className="settings-block">
          <h3>档位分布（按市值占比）</h3>
          <div style={{ display: "flex", height: 32, borderRadius: 4, overflow: "hidden", border: "1px solid #e5e7eb" }}>
            {TIER_ORDER.map((tier) => {
              const pct = parseFloat(data.tier_distribution[tier] ?? "0");
              if (pct === 0) return null;
              return (
                <div
                  key={tier}
                  title={`${tier} ${pct.toFixed(1)}%`}
                  style={{
                    width: `${pct}%`,
                    background: temperatureColor(
                      tier === "极度低估" ? "5" : tier === "低估" ? "20" :
                      tier === "合理" ? "50" : tier === "高估" ? "80" : "95"
                    ),
                    color: "white", fontSize: 11,
                    display: "flex", alignItems: "center", justifyContent: "center",
                  }}
                >
                  {pct >= 8 ? `${tier} ${pct.toFixed(0)}%` : ""}
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* 添加持仓 */}
      <section className="settings-block">
        <h3>添加持仓</h3>
        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          <EntityCombo value={selected} onChange={setSelected} />

          <div style={{ display: "flex", border: "1px solid #d1d5db", borderRadius: 4, overflow: "hidden" }}>
            <button
              type="button"
              onClick={() => setMode("value")}
              style={{
                padding: "4px 10px", fontSize: 12,
                background: mode === "value" ? "#2563eb" : "white",
                color: mode === "value" ? "white" : "#374151",
                border: "none", cursor: "pointer",
              }}
            >按金额</button>
            <button
              type="button"
              onClick={() => setMode("quantity")}
              style={{
                padding: "4px 10px", fontSize: 12,
                background: mode === "quantity" ? "#2563eb" : "white",
                color: mode === "quantity" ? "white" : "#374151",
                border: "none", cursor: "pointer",
                borderLeft: "1px solid #d1d5db",
              }}
            >按数量</button>
          </div>

          <input
            placeholder={mode === "value" ? "市值（¥）" : "股数 / 份数"}
            type="number"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            style={{ width: 140, padding: "4px 8px" }}
          />

          <input
            placeholder="备注（可选）"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            style={{ width: 160, padding: "4px 8px" }}
          />
          <button
            className="btn btn-primary"
            disabled={!selected || !amount || addMut.isPending}
            onClick={() => addMut.mutate()}
          >
            {addMut.isPending ? "..." : "加入"}
          </button>
        </div>
        {err && <p style={{ color: "#b91c1c", fontSize: 12, marginTop: 8 }}>{err}</p>}
        <p className="hint">
          {mode === "value"
            ? "按金额：直接录入当前市值（人民币）。"
            : "按数量：录入股数/份数，系统自动按最新价 × 数量算市值，并每 30 秒刷新一次。"}
        </p>
      </section>

      {/* 持仓列表 */}
      <section className="settings-block">
        <h3>持仓明细（{data.items.length}）</h3>
        {data.items.length === 0 ? (
          <p className="empty">还没有持仓。在上方录入。</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>类型</th>
                <th>代码</th>
                <th>名称</th>
                <th>录入</th>
                <th>市值（¥）</th>
                <th>权重</th>
                <th>温度</th>
                <th>档位</th>
                <th>PE / PB</th>
                <th>口径</th>
                <th>备注</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((h) => {
                const temp = h.temperature ? parseFloat(h.temperature) : null;
                const c = TYPE_COLOR[h.entity_type];
                const pf = isPriceFallback(h.temperature_source);
                const isEditing = editingId === h.id;
                const qty = h.quantity ? parseFloat(h.quantity) : null;
                const price = h.latest_price ? parseFloat(h.latest_price) : null;
                return (
                  <tr key={h.id}>
                    <td>
                      <span style={{
                        fontSize: 11, padding: "1px 6px",
                        background: c.bg, color: c.fg, borderRadius: 4,
                      }}>{TYPE_LABEL[h.entity_type]}</span>
                    </td>
                    <td>
                      <Link to={detailPath(h.entity_type, h.entity_code)}>
                        <strong>{h.entity_code}</strong>
                      </Link>
                    </td>
                    <td>{h.entity_name ?? <span style={{ color: "#dc2626" }}>⚠ 未找到</span>}</td>
                    <td style={{ fontSize: 11, color: "#6b7280" }}>
                      {h.input_mode === "quantity" && qty != null
                        ? `${qty} × ¥${price?.toFixed(2) ?? "?"}`
                        : "金额"}
                    </td>
                    <td>
                      {isEditing ? (
                        <div style={{ display: "flex", gap: 4, alignItems: "center" }}>
                          <select
                            value={editMode}
                            onChange={(e) => setEditMode(e.target.value as Mode)}
                            style={{ fontSize: 11, padding: "1px 4px" }}
                          >
                            <option value="value">¥</option>
                            <option value="quantity">数量</option>
                          </select>
                          <input
                            type="number"
                            value={editAmount}
                            onChange={(e) => setEditAmount(e.target.value)}
                            onKeyDown={(e) => {
                              if (e.key === "Enter") updMut.mutate();
                              if (e.key === "Escape") setEditingId(null);
                            }}
                            style={{ width: 80, padding: "2px 4px", fontSize: 12 }}
                            autoFocus
                          />
                        </div>
                      ) : (
                        parseFloat(h.market_value).toLocaleString("zh-CN", { maximumFractionDigits: 0 })
                      )}
                    </td>
                    <td>{h.weight_pct ? h.weight_pct + "%" : "—"}</td>
                    <td>
                      {temp != null ? (
                        <>
                          <span style={{
                            background: temperatureColor(temp.toString()),
                            color: "white", padding: "1px 8px",
                            borderRadius: 4, fontSize: 11,
                          }}>{temp.toFixed(1)}</span>
                          {pf && <span title="价格自比" style={{ marginLeft: 4, color: "#d97706" }}>⚠</span>}
                        </>
                      ) : "—"}
                    </td>
                    <td>{h.tier ? tierLabel(h.tier) : "—"}</td>
                    <td style={{ fontSize: 12, color: "#6b7280" }}>
                      {h.pe_ttm ? parseFloat(h.pe_ttm).toFixed(1) : "—"}
                      {" / "}
                      {h.pb ? parseFloat(h.pb).toFixed(2) : "—"}
                    </td>
                    <td style={{ fontSize: 11, color: pf ? "#d97706" : "#6b7280" }}>
                      {h.temperature_source ?? "—"}
                    </td>
                    <td style={{ fontSize: 12 }}>{h.note ?? "—"}</td>
                    <td style={{ whiteSpace: "nowrap" }}>
                      {isEditing ? (
                        <>
                          <button className="btn"
                            style={{ fontSize: 11, padding: "2px 6px", marginRight: 4 }}
                            onClick={() => updMut.mutate()}>确认</button>
                          <button className="btn"
                            style={{ fontSize: 11, padding: "2px 6px" }}
                            onClick={() => setEditingId(null)}>取消</button>
                        </>
                      ) : (
                        <>
                          <button className="btn"
                            style={{ fontSize: 11, padding: "2px 6px", marginRight: 4 }}
                            onClick={() => {
                              setEditingId(h.id);
                              setEditMode(h.input_mode);
                              setEditAmount(
                                h.input_mode === "quantity"
                                  ? (h.quantity ?? "")
                                  : h.market_value
                              );
                            }}>改</button>
                          <button className="btn"
                            style={{ fontSize: 11, padding: "2px 6px" }}
                            onClick={() => {
                              if (confirm(`删除 ${h.entity_code} ${h.entity_name ?? ""}？`)) {
                                delMut.mutate(h.id);
                              }
                            }}>删</button>
                        </>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
