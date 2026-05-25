import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { useState } from "react";
import { addActiveFund, listFunds, removeActiveFund } from "@/api/funds";
import { temperatureColor, tierLabel } from "@/utils/temperature";

const TYPE_LABEL: Record<string, string> = {
  ETF: "场内 ETF",
  INDEX_FUND: "场外指数",
  ACTIVE_FUND: "场外主动",
};
const TYPE_COLOR: Record<string, { bg: string; fg: string }> = {
  ETF: { bg: "#dcfce7", fg: "#166534" },
  INDEX_FUND: { bg: "#dbeafe", fg: "#1e40af" },
  ACTIVE_FUND: { bg: "#fef3c7", fg: "#92400e" },
};

export default function FundListSection() {
  const qc = useQueryClient();
  const [code, setCode] = useState("");
  const [err, setErr] = useState<string | null>(null);

  const list = useQuery({ queryKey: ["funds"], queryFn: listFunds });

  const addMut = useMutation({
    mutationFn: (c: string) => addActiveFund(c),
    onSuccess: () => {
      setCode("");
      setErr(null);
      qc.invalidateQueries({ queryKey: ["funds"] });
    },
    onError: (e: Error) => setErr(e.message),
  });

  const removeMut = useMutation({
    mutationFn: (c: string) => removeActiveFund(c),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["funds"] }),
  });

  if (list.isLoading) return <p className="empty">加载中…</p>;
  const items = list.data?.items ?? [];

  // 按 fund_type 分组（主动基金特别置顶，因为是用户自己加的）
  const active = items.filter((f) => f.fund_type === "ACTIVE_FUND");
  const passive = items.filter((f) => f.fund_type !== "ACTIVE_FUND");
  const byMarket: Record<string, typeof passive> = {};
  for (const f of passive) {
    (byMarket[f.market] = byMarket[f.market] ?? []).push(f);
  }

  return (
    <div>
      <section className="settings-block">
        <h3>添加场外主动基金（SRS R12 M7-B）</h3>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <input
            placeholder="基金代码（如 005827 易方达蓝筹精选）"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            style={{ flex: 1, maxWidth: 320, padding: "4px 8px" }}
            disabled={addMut.isPending}
            onKeyDown={(e) => {
              if (e.key === "Enter" && code.trim() && !addMut.isPending) {
                addMut.mutate(code.trim());
              }
            }}
          />
          <button
            className="btn btn-primary"
            onClick={() => addMut.mutate(code.trim())}
            disabled={!code.trim() || addMut.isPending}
          >
            {addMut.isPending ? "拉取中…(约 5–10 秒)" : "添加"}
          </button>
        </div>
        {err && <p style={{ color: "#b91c1c", fontSize: 12 }}>{err}</p>}
        <p className="hint">
          温度按 <strong>NAV 5 年历史百分位</strong>计算（高百分位 = NAV 处于自身历史高位）。
          ⚠ <strong>仅反映 NAV 与自身比，不反映持仓估值水位</strong>（季报披露 70% 持仓且滞后，不接入）。
          ETF / 场外指数基金温度仍挂跟踪指数。
        </p>
      </section>

      {/* 主动基金 */}
      {active.length > 0 && (
        <section className="settings-block">
          <h3>场外主动基金（{active.length}）</h3>
          <table className="table">
            <thead>
              <tr>
                <th>代码</th>
                <th>基金名称</th>
                <th>基金经理</th>
                <th>成立日</th>
                <th>历史</th>
                <th>最新 NAV</th>
                <th>温度</th>
                <th>档位</th>
                <th>说明</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {active.map((f) => {
                const temp = f.temperature ? parseFloat(f.temperature) : null;
                return (
                  <tr key={f.code}>
                    <td>
                      <Link to={`/funds/${encodeURIComponent(f.code)}`}>
                        <strong>{f.code}</strong>
                      </Link>
                    </td>
                    <td>{f.name}</td>
                    <td>{f.fund_manager ?? "—"}</td>
                    <td>{f.setup_date ?? "—"}</td>
                    <td>{f.actual_history_years != null ? f.actual_history_years.toFixed(1) + "y" : "—"}</td>
                    <td>{f.nav_latest ? parseFloat(f.nav_latest).toFixed(4) : "—"}</td>
                    <td>
                      {temp != null ? (
                        <span style={{
                          background: temperatureColor(temp.toString()),
                          color: "white", padding: "1px 8px",
                          borderRadius: 4, fontSize: 11,
                        }}>{temp.toFixed(1)}</span>
                      ) : "—"}
                    </td>
                    <td>{f.tier ? tierLabel(f.tier) : "—"}</td>
                    <td style={{ fontSize: 11, color: "#92400e" }} title="NAV 5y 百分位，不反映持仓水位">
                      ⚠ NAV 自比
                    </td>
                    <td>
                      <button
                        className="btn"
                        onClick={() => {
                          if (confirm(`确认移除 ${f.code} ${f.name}？NAV 历史会一并删除。`)) {
                            removeMut.mutate(f.code);
                          }
                        }}
                        style={{ fontSize: 11, padding: "2px 6px" }}
                      >
                        移除
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </section>
      )}

      {/* 被动基金按市场分组 */}
      <p className="hint" style={{ marginTop: 16 }}>
        以下为内置 ETF / 场外指数基金（{passive.length} 只），温度直接继承自<strong>跟踪指数</strong>。
      </p>
      {["A", "HK", "US"].map((mkt) => {
        const arr = byMarket[mkt] ?? [];
        if (arr.length === 0) return null;
        return (
          <section key={mkt} className="settings-block">
            <h3>{mkt} 市场（{arr.length}）</h3>
            <table className="table">
              <thead>
                <tr>
                  <th>代码</th>
                  <th>名称</th>
                  <th>类型</th>
                  <th>跟踪指数</th>
                  <th>温度</th>
                  <th>档位</th>
                  <th>PE</th>
                  <th>PB</th>
                  <th>费率</th>
                </tr>
              </thead>
              <tbody>
                {arr.map((f) => {
                  const temp = f.temperature ? parseFloat(f.temperature) : null;
                  const c = TYPE_COLOR[f.fund_type] ?? TYPE_COLOR.ETF;
                  return (
                    <tr key={f.code}>
                      <td><strong>{f.code}</strong></td>
                      <td>{f.name}</td>
                      <td>
                        <span style={{
                          fontSize: 11, padding: "1px 6px",
                          background: c.bg, color: c.fg, borderRadius: 4,
                        }}>{TYPE_LABEL[f.fund_type] ?? f.fund_type}</span>
                      </td>
                      <td>
                        {f.tracks_index_code ? (
                          <Link to={`/indices/${encodeURIComponent(f.tracks_index_code)}`}>
                            {f.tracks_index_code} {f.tracks_index_name}
                          </Link>
                        ) : "—"}
                      </td>
                      <td>
                        {temp != null ? (
                          <span style={{
                            background: temperatureColor(temp.toString()),
                            color: "white", padding: "1px 8px",
                            borderRadius: 4, fontSize: 11,
                          }}>{temp.toFixed(1)}</span>
                        ) : "—"}
                      </td>
                      <td>{f.tier ? tierLabel(f.tier) : "—"}</td>
                      <td>{f.pe_ttm ? parseFloat(f.pe_ttm).toFixed(2) : "—"}</td>
                      <td>{f.pb ? parseFloat(f.pb).toFixed(2) : "—"}</td>
                      <td>{f.fee_rate ? (parseFloat(f.fee_rate) * 100).toFixed(2) + "%" : "—"}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </section>
        );
      })}
    </div>
  );
}
