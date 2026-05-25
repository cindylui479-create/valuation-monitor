import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Fragment, useState } from "react";
import {
  fetchDataQualityDetail,
  fetchDataQualitySummary,
  setAnomalyAck,
  type AnomalyItem,
  type IndexAnomalyCount,
} from "@/api/dataQuality";

const SEVERITY_COLOR: Record<string, string> = {
  HIGH: "#b91c1c",
  MEDIUM: "#d97706",
  LOW: "#2563eb",
  INFO: "#6b7280",
};

const TYPE_LABEL: Record<string, string> = {
  NEGATIVE: "负值",
  DAILY_JUMP: "单日跳变",
  MAD_OUTLIER: "MAD 离群",
  STALE: "数据冻结",
  CROSS_DIVERGE: "跨源分歧",
  CROSS_IDENTICAL: "跨源同源",
  LOW_VARIANCE: "方差过小",
};

function pill(severity: string) {
  return {
    display: "inline-block",
    padding: "1px 6px",
    borderRadius: 4,
    background: SEVERITY_COLOR[severity] ?? "#9ca3af",
    color: "white",
    fontSize: 11,
    minWidth: 32,
    textAlign: "center" as const,
  };
}

function AckButton({
  anomaly, onChanged,
}: {
  anomaly: AnomalyItem;
  onChanged: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const [note, setNote] = useState("");
  const isAcked = !!anomaly.acknowledged_at;

  const mut = useMutation({
    mutationFn: (vars: { ack: boolean; note?: string }) =>
      setAnomalyAck(anomaly.id, vars.ack, vars.note),
    onSuccess: () => {
      setEditing(false);
      setNote("");
      onChanged();
    },
  });

  if (isAcked) {
    return (
      <button
        className="btn"
        style={{ fontSize: 11, padding: "2px 6px", color: "#15803d" }}
        title={`${anomaly.acknowledged_at}\n${anomaly.acknowledged_note ?? ""}`}
        onClick={(e) => { e.stopPropagation(); mut.mutate({ ack: false }); }}
        disabled={mut.isPending}
      >
        ✓ 已核对
      </button>
    );
  }

  if (editing) {
    return (
      <span style={{ display: "inline-flex", gap: 4 }} onClick={(e) => e.stopPropagation()}>
        <input
          autoFocus
          value={note}
          placeholder="备注（可选）"
          onChange={(e) => setNote(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") mut.mutate({ ack: true, note: note || undefined });
            if (e.key === "Escape") setEditing(false);
          }}
          style={{ fontSize: 11, padding: "1px 4px", width: 120 }}
        />
        <button
          className="btn"
          style={{ fontSize: 11, padding: "2px 6px" }}
          onClick={() => mut.mutate({ ack: true, note: note || undefined })}
          disabled={mut.isPending}
        >确认</button>
        <button
          className="btn"
          style={{ fontSize: 11, padding: "2px 6px" }}
          onClick={() => setEditing(false)}
        >取消</button>
      </span>
    );
  }

  return (
    <button
      className="btn"
      style={{ fontSize: 11, padding: "2px 6px" }}
      onClick={(e) => { e.stopPropagation(); setEditing(true); }}
    >
      标记已核对
    </button>
  );
}

function AnomalyDetailRows({ code }: { code: string }) {
  const qc = useQueryClient();
  const detail = useQuery({
    queryKey: ["data-quality-detail", code],
    queryFn: () => fetchDataQualityDetail(code),
  });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["data-quality-detail", code] });
    qc.invalidateQueries({ queryKey: ["data-quality-summary"] });
  };

  if (detail.isLoading) return <tr><td colSpan={8} className="empty">加载中…</td></tr>;
  if (!detail.data) return null;

  if (detail.data.anomalies.length === 0) {
    return <tr><td colSpan={8} className="empty">无异常记录</td></tr>;
  }

  return (
    <>
      {detail.data.anomalies.slice(0, 200).map((a) => {
        const isAcked = !!a.acknowledged_at;
        return (
          <tr key={a.id} style={isAcked ? { opacity: 0.45 } : undefined}>
            <td>{a.date}</td>
            <td><span style={pill(a.severity)}>{a.severity}</span></td>
            <td>{TYPE_LABEL[a.anomaly_type] ?? a.anomaly_type}</td>
            <td>{a.field}/{a.source}</td>
            <td>{a.value ?? "—"}</td>
            <td>{a.baseline ?? "—"}</td>
            <td style={{ color: "#6b7280" }}>{a.note ?? ""}</td>
            <td><AckButton anomaly={a} onChanged={invalidate} /></td>
          </tr>
        );
      })}
      {detail.data.anomalies.length > 200 && (
        <tr><td colSpan={8} className="empty">
          仅展示前 200 条（共 {detail.data.anomalies.length}）
        </td></tr>
      )}
    </>
  );
}

export default function DataQualitySection() {
  const [expandedCode, setExpandedCode] = useState<string | null>(null);
  const [includeAcked, setIncludeAcked] = useState(false);

  const summary = useQuery({
    queryKey: ["data-quality-summary", includeAcked],
    queryFn: () => fetchDataQualitySummary(includeAcked),
  });

  if (summary.isLoading) {
    return (
      <section className="settings-block">
        <h3>数据质量（SRS R11）</h3>
        <p className="empty">加载中…</p>
      </section>
    );
  }

  const items = summary.data?.items ?? [];
  const withAnomalies = items.filter((i) => i.total > 0);
  const clean = items.filter((i) => i.total === 0 && i.acknowledged === 0);
  const fullyAcked = items.filter((i) => i.total === 0 && i.acknowledged > 0);

  return (
    <section className="settings-block">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h3>数据质量（SRS R11）</h3>
        <span style={{ fontSize: 12, color: "var(--muted)" }}>
          共 {summary.data?.total_anomalies ?? 0} 条{includeAcked ? "" : "未核对"}异常，覆盖 {withAnomalies.length}/{items.length} 只指数
        </span>
      </div>
      <p className="hint">
        每日批处理后自动检测 7 类异常：负值、单日跳变、MAD 离群、数据冻结、跨源分歧、跨源同源、方差过小。
        <strong>不修改温度/分位数字</strong>，仅用于告警。详细规则见 SRS R11 决策表。
      </p>
      <label style={{ display: "inline-flex", alignItems: "center", gap: 6, marginTop: 6, marginBottom: 6, fontSize: 12 }}>
        <input
          type="checkbox"
          checked={includeAcked}
          onChange={(e) => setIncludeAcked(e.target.checked)}
        />
        显示已核对的异常
      </label>

      {withAnomalies.length === 0 ? (
        <p className="empty">所有指数数据质量良好 ✓{includeAcked ? "" : "（或全部已核对）"}</p>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th>代码</th>
              <th>名称</th>
              <th>市场</th>
              <th>HIGH</th>
              <th>MEDIUM</th>
              <th>LOW</th>
              <th>INFO</th>
              <th>总计</th>
              <th>已核对</th>
              <th>最近</th>
            </tr>
          </thead>
          <tbody>
            {withAnomalies.map((it: IndexAnomalyCount) => {
              const isExpanded = expandedCode === it.code;
              return (
                <Fragment key={it.code}>
                  <tr
                    style={{ cursor: "pointer", background: isExpanded ? "#f9fafb" : undefined }}
                    onClick={() => setExpandedCode(isExpanded ? null : it.code)}
                  >
                    <td><strong>{it.code}</strong></td>
                    <td>{it.name}</td>
                    <td>{it.market}</td>
                    <td>{it.high > 0 ? <span style={pill("HIGH")}>{it.high}</span> : "—"}</td>
                    <td>{it.medium > 0 ? <span style={pill("MEDIUM")}>{it.medium}</span> : "—"}</td>
                    <td>{it.low > 0 ? <span style={pill("LOW")}>{it.low}</span> : "—"}</td>
                    <td>{it.info > 0 ? <span style={pill("INFO")}>{it.info}</span> : "—"}</td>
                    <td><strong>{it.total}</strong></td>
                    <td style={{ color: "#15803d" }}>{it.acknowledged > 0 ? `✓ ${it.acknowledged}` : "—"}</td>
                    <td>{it.latest_anomaly_date ?? "—"}</td>
                  </tr>
                  {isExpanded && (
                    <tr>
                      <td colSpan={10} style={{ background: "#f9fafb", padding: 0 }}>
                        <table className="table" style={{ margin: 0, fontSize: 12 }}>
                          <thead>
                            <tr>
                              <th>日期</th>
                              <th>级别</th>
                              <th>类型</th>
                              <th>字段/源</th>
                              <th>值</th>
                              <th>基线</th>
                              <th>说明</th>
                              <th style={{ width: 200 }}>操作</th>
                            </tr>
                          </thead>
                          <tbody>
                            <AnomalyDetailRows code={it.code} />
                          </tbody>
                        </table>
                      </td>
                    </tr>
                  )}
                </Fragment>
              );
            })}
          </tbody>
        </table>
      )}

      {(clean.length > 0 || fullyAcked.length > 0) && (
        <p className="hint" style={{ marginTop: 12 }}>
          {clean.length > 0 && <>✓ 无异常：{clean.map((c) => c.code).join("、")}</>}
          {clean.length > 0 && fullyAcked.length > 0 && " ｜ "}
          {fullyAcked.length > 0 && <>✓ 全部已核对：{fullyAcked.map((c) => c.code).join("、")}</>}
        </p>
      )}
    </section>
  );
}
