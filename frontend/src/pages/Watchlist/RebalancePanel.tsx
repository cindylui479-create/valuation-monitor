import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { rebalanceSuggest, type HoldingAdjustment } from "@/api/rebalance";

interface Props {
  currentTemp: number | null;
}

export default function RebalancePanel({ currentTemp }: Props) {
  const [target, setTarget] = useState<number>(50);
  const [result, setResult] = useState<HoldingAdjustment[] | null>(null);
  const [meta, setMeta] = useState<{
    feasible: boolean;
    current: string | null;
    projected: string | null;
    notes: string[];
  } | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const mut = useMutation({
    mutationFn: () => rebalanceSuggest(target),
    onSuccess: (data) => {
      setResult(data.adjustments);
      setMeta({
        feasible: data.feasible,
        current: data.current_temp,
        projected: data.projected_temp,
        notes: data.notes,
      });
      setErr(null);
    },
    onError: (e: Error) => setErr(e.message),
  });

  return (
    <section className="settings-block">
      <h3>组合再平衡建议（SRS I）</h3>
      <p className="hint">
        贪心算法：目标低温度时减仓"温度高于目标"的标的，加仓"温度低于目标"的标的（金额仅作建议参考）。
        受现有持仓温度限制——如所有持仓都在某一区间，可能不可达。
      </p>

      <div style={{ display: "flex", gap: 16, alignItems: "center", flexWrap: "wrap", marginTop: 8 }}>
        <label style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <span style={{ fontSize: 12, color: "#6b7280" }}>当前：</span>
          <strong>{currentTemp != null ? currentTemp.toFixed(1) : "—"}</strong>
        </label>
        <label style={{ display: "flex", alignItems: "center", gap: 6 }}>
          目标温度：
          <input
            type="range"
            min={0} max={100} step={1}
            value={target}
            onChange={(e) => setTarget(Number(e.target.value))}
            style={{ width: 200 }}
          />
          <strong style={{ minWidth: 32 }}>{target}</strong>
        </label>
        <button
          className="btn btn-primary"
          onClick={() => mut.mutate()}
          disabled={mut.isPending}
        >
          {mut.isPending ? "计算中…" : "生成建议"}
        </button>
      </div>
      {err && <p style={{ color: "#b91c1c", fontSize: 12, marginTop: 8 }}>{err}</p>}

      {meta && (
        <div style={{ marginTop: 12 }}>
          <div style={{
            display: "flex", gap: 16, padding: 10,
            background: meta.feasible ? "#f0fdf4" : "#fef3c7",
            border: `1px solid ${meta.feasible ? "#86efac" : "#fde68a"}`,
            borderRadius: 4, fontSize: 13,
          }}>
            <span>当前 {meta.current ? parseFloat(meta.current).toFixed(1) : "—"} →</span>
            <span>预期 <strong>{meta.projected ? parseFloat(meta.projected).toFixed(1) : "—"}</strong></span>
            <span>（目标 {target}）</span>
            {!meta.feasible && <span style={{ color: "#d97706" }}>⚠ 目标不可达</span>}
          </div>
          {meta.notes.length > 0 && (
            <ul style={{ fontSize: 12, color: "#6b7280", marginTop: 6 }}>
              {meta.notes.map((n, i) => <li key={i}>{n}</li>)}
            </ul>
          )}
        </div>
      )}

      {result && result.length > 0 && (
        <table className="table" style={{ marginTop: 12, fontSize: 13 }}>
          <thead>
            <tr>
              <th>代码</th>
              <th>名称</th>
              <th>温度</th>
              <th>当前 ¥</th>
              <th>建议 ¥</th>
              <th>动作</th>
            </tr>
          </thead>
          <tbody>
            {result.map((a) => {
              const delta = parseFloat(a.delta_mv);
              const color = a.direction === "ADD" ? "#15803d" : a.direction === "REDUCE" ? "#dc2626" : "#6b7280";
              return (
                <tr key={`${a.entity_type}-${a.entity_code}`}>
                  <td><strong>{a.entity_code}</strong></td>
                  <td>{a.entity_name}</td>
                  <td>{parseFloat(a.current_temp).toFixed(1)}</td>
                  <td>{parseFloat(a.current_mv).toLocaleString("zh-CN", { maximumFractionDigits: 0 })}</td>
                  <td>{parseFloat(a.suggested_mv).toLocaleString("zh-CN", { maximumFractionDigits: 0 })}</td>
                  <td style={{ color, fontWeight: 600 }}>
                    {a.direction === "ADD" ? "+加仓 " : a.direction === "REDUCE" ? "-减仓 " : "持平"}
                    {a.direction !== "HOLD" && (
                      Math.abs(delta).toLocaleString("zh-CN", { maximumFractionDigits: 0 })
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </section>
  );
}
