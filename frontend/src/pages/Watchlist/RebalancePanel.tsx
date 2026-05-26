/**
 * SRS v1.3.1 I-fix：再平衡建议（纯逆向模式）。
 *
 * 移除 target slider —— 之前实现"机械求解组合温度 = X"导致升温场景下
 * 推荐"加仓高估、减仓低估"，反直觉。
 *
 * 新逻辑（与"低买高卖"逆向投资直觉一致）：
 *   - 减仓所有温度 > 70 的高估持仓（按 reduce_pct）
 *   - 释放资金按现有 mv 比例加仓所有温度 < 30 的低估持仓
 *   - MID (30-70) 桶保持不变
 */
import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { rebalanceSuggest, type HoldingAdjustment } from "@/api/rebalance";

interface Props {
  currentTemp: number | null;
}

const REDUCE_OPTIONS = [
  { value: 0.10, label: "保守 10%" },
  { value: 0.20, label: "适中 20%" },
  { value: 0.30, label: "标准 30%" },
  { value: 0.50, label: "激进 50%" },
];

export default function RebalancePanel({ currentTemp }: Props) {
  const [reducePct, setReducePct] = useState<number>(0.30);
  const [result, setResult] = useState<HoldingAdjustment[] | null>(null);
  const [meta, setMeta] = useState<{
    feasible: boolean;
    current: string | null;
    projected: string | null;
    released: string;
    n_high: number;
    n_low: number;
    n_mid: number;
    notes: string[];
  } | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const mut = useMutation({
    mutationFn: () => rebalanceSuggest(reducePct),
    onSuccess: (data) => {
      setResult(data.adjustments);
      setMeta({
        feasible: data.feasible,
        current: data.current_temp,
        projected: data.projected_temp,
        released: data.total_released,
        n_high: data.n_high,
        n_low: data.n_low,
        n_mid: data.n_mid,
        notes: data.notes,
      });
      setErr(null);
    },
    onError: (e: Error) => setErr(e.message),
  });

  const directionColor = (d: string) =>
    d === "REDUCE" ? "#dc2626" : d === "ADD" ? "#15803d" : "#6b7280";

  return (
    <section className="settings-block">
      <h3>组合再平衡建议（纯逆向模式）</h3>
      <p className="hint">
        <strong>"低买高卖"逻辑</strong>：减仓所有温度 &gt; 70 的高估持仓，
        释放资金按比例加仓所有温度 &lt; 30 的低估持仓。
        30-70 合理区间持仓保持不变。<br/>
        若组合无高估/低估持仓，将提示"无需再平衡"或"建议保留现金"。
      </p>

      <div style={{ display: "flex", gap: 16, alignItems: "center", flexWrap: "wrap", marginTop: 8 }}>
        <span style={{ fontSize: 12, color: "#6b7280" }}>
          当前组合温度：<strong>{currentTemp != null ? currentTemp.toFixed(1) : "—"}</strong>
        </span>
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <span style={{ fontSize: 12 }}>减仓比例：</span>
          <div style={{ display: "flex", border: "1px solid #d1d5db", borderRadius: 4, overflow: "hidden" }}>
            {REDUCE_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                type="button"
                onClick={() => setReducePct(opt.value)}
                style={{
                  padding: "4px 10px", fontSize: 12,
                  background: reducePct === opt.value ? "#2563eb" : "white",
                  color: reducePct === opt.value ? "white" : "#374151",
                  border: "none", cursor: "pointer",
                  borderLeft: opt.value !== 0.10 ? "1px solid #d1d5db" : "none",
                }}
              >{opt.label}</button>
            ))}
          </div>
        </div>
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
            background: meta.feasible && parseFloat(meta.released) > 0 ? "#f0fdf4" : "#fef3c7",
            border: `1px solid ${meta.feasible && parseFloat(meta.released) > 0 ? "#86efac" : "#fde68a"}`,
            borderRadius: 4, fontSize: 13, flexWrap: "wrap",
          }}>
            <span>桶分布：<strong style={{ color: "#dc2626" }}>HIGH {meta.n_high}</strong> · <strong style={{ color: "#6b7280" }}>MID {meta.n_mid}</strong> · <strong style={{ color: "#15803d" }}>LOW {meta.n_low}</strong></span>
            {parseFloat(meta.released) > 0 && (
              <span>释放资金 <strong>¥{parseFloat(meta.released).toLocaleString("zh-CN", { maximumFractionDigits: 0 })}</strong></span>
            )}
            <span>
              组合温度 {meta.current ? parseFloat(meta.current).toFixed(1) : "—"} →
              <strong> {meta.projected ? parseFloat(meta.projected).toFixed(1) : "—"}</strong>
            </span>
          </div>
          {meta.notes.length > 0 && (
            <ul style={{ fontSize: 12, color: "#6b7280", marginTop: 6, paddingLeft: 20 }}>
              {meta.notes.map((n, i) => <li key={i}>{n}</li>)}
            </ul>
          )}
        </div>
      )}

      {result && result.length > 0 && (
        <table className="table" style={{ marginTop: 12, fontSize: 13 }}>
          <thead>
            <tr>
              <th>桶</th>
              <th>代码</th>
              <th>名称</th>
              <th>温度</th>
              <th>档位</th>
              <th>当前 ¥</th>
              <th>建议 ¥</th>
              <th>动作</th>
            </tr>
          </thead>
          <tbody>
            {result.map((a) => {
              const delta = parseFloat(a.delta_mv);
              const bucketColor =
                a.bucket === "HIGH" ? "#fee2e2" :
                a.bucket === "LOW" ? "#dcfce7" : "#f3f4f6";
              const bucketFg =
                a.bucket === "HIGH" ? "#b91c1c" :
                a.bucket === "LOW" ? "#166534" : "#6b7280";
              return (
                <tr key={`${a.entity_type}-${a.entity_code}`}>
                  <td>
                    <span style={{
                      fontSize: 11, padding: "1px 6px",
                      background: bucketColor, color: bucketFg, borderRadius: 3,
                    }}>{a.bucket}</span>
                  </td>
                  <td><strong>{a.entity_code}</strong></td>
                  <td>{a.entity_name}</td>
                  <td>{parseFloat(a.current_temp).toFixed(1)}</td>
                  <td style={{ fontSize: 11, color: "#6b7280" }}>{a.tier ?? "—"}</td>
                  <td>{parseFloat(a.current_mv).toLocaleString("zh-CN", { maximumFractionDigits: 0 })}</td>
                  <td>{parseFloat(a.suggested_mv).toLocaleString("zh-CN", { maximumFractionDigits: 0 })}</td>
                  <td style={{ color: directionColor(a.direction), fontWeight: 600 }}>
                    {a.direction === "REDUCE" && `- 减仓 ${Math.abs(delta).toLocaleString("zh-CN", { maximumFractionDigits: 0 })}`}
                    {a.direction === "ADD" && `+ 加仓 ${delta.toLocaleString("zh-CN", { maximumFractionDigits: 0 })}`}
                    {a.direction === "HOLD" && "持平"}
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
