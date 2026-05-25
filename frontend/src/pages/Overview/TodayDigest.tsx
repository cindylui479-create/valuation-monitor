import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  fetchOpportunities,
  fetchTierTransitions,
  type Opportunity,
  type TierTransition,
} from "@/api/opportunities";
import { temperatureColor } from "@/utils/temperature";

const TYPE_COLOR: Record<string, { bg: string; fg: string }> = {
  INDEX: { bg: "#dbeafe", fg: "#1e40af" },
  STOCK: { bg: "#fce7f3", fg: "#9d174d" },
  FUND: { bg: "#fef3c7", fg: "#92400e" },
};

function entityPath(t: string, code: string): string {
  if (t === "INDEX") return `/indices/${encodeURIComponent(code)}`;
  if (t === "STOCK") return `/stocks/${encodeURIComponent(code)}`;
  return `/funds/${encodeURIComponent(code)}`;
}

function OppPill({ o }: { o: Opportunity }) {
  const c = TYPE_COLOR[o.entity_type];
  const t = parseFloat(o.temperature);
  return (
    <Link
      to={entityPath(o.entity_type, o.entity_code)}
      style={{
        display: "inline-flex", alignItems: "center", gap: 6,
        padding: "4px 10px", borderRadius: 999,
        background: "white", border: "1px solid #e5e7eb",
        textDecoration: "none", color: "inherit",
        fontSize: 12,
      }}
    >
      <span style={{
        fontSize: 10, padding: "1px 5px",
        background: c.bg, color: c.fg, borderRadius: 3,
      }}>{o.entity_type}</span>
      <strong>{o.entity_name}</strong>
      <span style={{ color: "#9ca3af" }}>{o.entity_code}</span>
      <span style={{
        background: temperatureColor(o.temperature),
        color: "white", padding: "1px 6px",
        borderRadius: 3, fontSize: 10,
      }}>{t.toFixed(1)}</span>
    </Link>
  );
}

function TransitionRow({ t }: { t: TierTransition }) {
  const c = TYPE_COLOR[t.entity_type];
  const delta = parseFloat(t.temperature_delta);
  const sevColor =
    t.severity === "HIGH" ? "#b91c1c" :
    t.severity === "MEDIUM" ? "#d97706" : "#6b7280";
  return (
    <Link
      to={entityPath(t.entity_type, t.entity_code)}
      style={{
        display: "flex", alignItems: "center", gap: 8,
        padding: "6px 10px", textDecoration: "none", color: "inherit",
        fontSize: 12, borderBottom: "1px solid #f3f4f6",
      }}
    >
      <span style={{
        fontSize: 10, padding: "1px 5px",
        background: sevColor, color: "white",
        borderRadius: 3, minWidth: 50, textAlign: "center",
      }}>{t.severity}</span>
      <span style={{ color: "#6b7280", minWidth: 80 }}>{t.date}</span>
      <span style={{
        fontSize: 10, padding: "1px 5px",
        background: c.bg, color: c.fg, borderRadius: 3,
      }}>{t.entity_type}</span>
      <strong>{t.entity_name}</strong>
      <span style={{ color: "#9ca3af" }}>{t.entity_code}</span>
      <span style={{ marginLeft: "auto" }}>
        <span style={{ color: "#9ca3af" }}>{t.from_tier ?? "—"}</span>
        {" → "}
        <strong>{t.to_tier}</strong>
        <span style={{
          marginLeft: 8,
          color: delta > 0 ? "#dc2626" : "#15803d",
        }}>
          {delta > 0 ? "↑" : "↓"} {Math.abs(delta).toFixed(1)}°
        </span>
      </span>
    </Link>
  );
}

export default function TodayDigest() {
  const opps = useQuery({
    queryKey: ["opportunities"],
    queryFn: fetchOpportunities,
  });
  const transitions = useQuery({
    queryKey: ["tier-transitions", 7],
    queryFn: () => fetchTierTransitions(7),
  });

  const low = opps.data?.low_valuations ?? [];
  const high = opps.data?.high_valuations ?? [];
  const trans = transitions.data?.items ?? [];

  if (opps.isLoading || transitions.isLoading) {
    return null;
  }

  if (low.length === 0 && high.length === 0 && trans.length === 0) {
    return null;
  }

  return (
    <section className="settings-block" style={{ marginBottom: 16 }}>
      <h3>🔔 今日动态</h3>

      {low.length > 0 && (
        <div style={{ marginBottom: 12 }}>
          <div style={{ fontSize: 12, color: "#15803d", marginBottom: 6, fontWeight: 600 }}>
            ✨ 低估机会（{low.length}）
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            {low.slice(0, 12).map((o) => (
              <OppPill key={`${o.entity_type}-${o.entity_code}`} o={o} />
            ))}
          </div>
        </div>
      )}

      {high.length > 0 && (
        <div style={{ marginBottom: 12 }}>
          <div style={{ fontSize: 12, color: "#b91c1c", marginBottom: 6, fontWeight: 600 }}>
            ⚠ 极度高估（{high.length}）
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            {high.slice(0, 12).map((o) => (
              <OppPill key={`${o.entity_type}-${o.entity_code}`} o={o} />
            ))}
          </div>
        </div>
      )}

      {trans.length > 0 && (
        <div>
          <div style={{ fontSize: 12, color: "#374151", marginBottom: 6, fontWeight: 600 }}>
            📊 7 天内档位跳变（{trans.length}）
          </div>
          <div style={{ border: "1px solid #e5e7eb", borderRadius: 4 }}>
            {trans.slice(0, 8).map((t, i) => (
              <TransitionRow key={`${t.entity_type}-${t.entity_code}-${t.date}-${i}`} t={t} />
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
