import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { useMemo, useState } from "react";
import { fetchEffectiveness } from "@/api/effectiveness";
import { fetchSignals, fetchTodaySignals } from "@/api/signals";
import { formatTemperature } from "@/utils/decimal";
import { temperatureColor } from "@/utils/temperature";
import { usePeSource } from "@/hooks/usePeSource";

const DIRECTION_LABEL: Record<string, string> = {
  STRONG_BUY: "强买入",
  BUY: "买入",
  SELL: "减持",
  STRONG_SELL: "强减持",
};

const DIRECTION_COLOR: Record<string, string> = {
  STRONG_BUY: "#15803d",
  BUY: "#22c55e",
  SELL: "#f87171",
  STRONG_SELL: "#b91c1c",
};

export default function Signals() {
  const [tab, setTab] = useState<"today" | "history">("today");
  const [onlySubscribed, setOnlySubscribed] = useState(false);
  const peSource = usePeSource();

  const todayQuery = useQuery({
    queryKey: ["signals", "today", onlySubscribed, peSource],
    queryFn: () => fetchTodaySignals(onlySubscribed, peSource),
    enabled: tab === "today",
  });

  const historyQuery = useQuery({
    queryKey: ["signals", "history", onlySubscribed, peSource],
    queryFn: () =>
      fetchSignals({
        only_subscribed: onlySubscribed,
        limit: 200,
        pe_source: peSource,
      }),
    enabled: tab === "history",
  });

  const data = tab === "today" ? todayQuery.data : historyQuery.data;

  // SIG-1：拉 365 天 horizon 的实证数据，给每条信号附"该档位 1 年历史参考"
  const effQuery = useQuery({
    queryKey: ["effectiveness", 365, 10, ""],
    queryFn: () => fetchEffectiveness(365, 10),
    staleTime: 60 * 60_000,  // 1 小时缓存，避免每次进页面重算 2.4 万样本
  });
  const tierStats = useMemo(() => {
    const map = new Map<string, { median: number; winRate: number; n: number }>();
    for (const b of effQuery.data?.coarse_buckets ?? []) {
      if (b.median_return_pct != null && b.win_rate != null) {
        map.set(b.tier, {
          median: parseFloat(b.median_return_pct),
          winRate: parseFloat(b.win_rate),
          n: b.n_samples,
        });
      }
    }
    return map;
  }, [effQuery.data]);

  return (
    <div className="signals-page">
      <div className="page-header">
        <h2>
          估值信号
          <Link
            to="/temperature/effectiveness"
            style={{
              fontSize: 13, marginLeft: 16,
              color: "#2563eb", textDecoration: "none",
            }}
          >📊 温度有效性 →</Link>
        </h2>
        <div className="controls">
          <div className="view-toggle">
            <button
              className={tab === "today" ? "active" : ""}
              onClick={() => setTab("today")}
            >
              今日
            </button>
            <button
              className={tab === "history" ? "active" : ""}
              onClick={() => setTab("history")}
            >
              历史
            </button>
          </div>
          <label className="check">
            <input
              type="checkbox"
              checked={onlySubscribed}
              onChange={(e) => setOnlySubscribed(e.target.checked)}
            />
            仅显示自选/定投相关
          </label>
        </div>
      </div>

      {/* SIG-1：信号语义校准（来自温度有效性实证，EFF-2） */}
      <div style={{
        background: "#eff6ff", border: "1px solid #bfdbfe", color: "#1e40af",
        padding: "10px 14px", borderRadius: 4, marginBottom: 12, fontSize: 13,
      }}>
        📐 <strong>信号是"约 1 年视角"的估值信号，不是短线择时。</strong>
        本工具 10 年实证（2.4 万样本）：90 天内市场动量主导，低估可以更低估、
        高估常继续上涨；温度的预测力在约 1 年 horizon 才显现
        （<Link to="/temperature/effectiveness" style={{ color: "#1e40af", fontWeight: 600 }}>查看完整实证 →</Link>）。
        表中"1 年历史参考"列 = 历史上处于该档位的所有样本，1 年后的中位收益与上涨占比。
      </div>

      {(todayQuery.isLoading || historyQuery.isLoading) && (
        <div className="state">加载中…</div>
      )}

      {data && data.items.length === 0 && (
        <div className="state">
          <p>{tab === "today" ? "今日无信号" : "暂无历史信号"}</p>
          {tab === "today" && (
            <p className="hint">
              信号在每日批处理后生成。A 股 16:30 / 港股 17:30 / 美股 次日 07:00。
            </p>
          )}
        </div>
      )}

      {data && data.items.length > 0 && (
        <table className="table">
          <thead>
            <tr>
              <th>日期</th>
              <th>市场</th>
              <th>指数</th>
              <th>方向</th>
              <th>档位</th>
              <th>温度</th>
              <th>1 年历史参考</th>
            </tr>
          </thead>
          <tbody>
            {data.items.map((s) => {
              const stat = tierStats.get(s.tier);
              return (
                <tr key={s.id}>
                  <td>{s.date}</td>
                  <td>{s.market}</td>
                  <td>
                    <Link to={`/indices/${encodeURIComponent(s.index_code)}`}>
                      <div className="cell-name">{s.index_name}</div>
                      <div className="cell-code">{s.index_code}</div>
                    </Link>
                  </td>
                  <td>
                    <span
                      className="tier-badge"
                      style={{ backgroundColor: DIRECTION_COLOR[s.direction] }}
                    >
                      {DIRECTION_LABEL[s.direction]}
                    </span>
                  </td>
                  <td>
                    <span
                      className="tier-badge"
                      style={{ backgroundColor: temperatureColor(s.temperature) }}
                    >
                      {s.tier}
                    </span>
                  </td>
                  <td>{formatTemperature(s.temperature)}</td>
                  <td style={{ fontSize: 12 }}>
                    {stat ? (
                      <span title={`基于 ${stat.n.toLocaleString()} 个历史样本（全指数 10 年）`}>
                        <span style={{
                          color: stat.median > 0 ? "#dc2626" : "#15803d",
                          fontWeight: 600,
                        }}>
                          {stat.median > 0 ? "+" : ""}{stat.median.toFixed(1)}%
                        </span>
                        <span style={{ color: "#6b7280", marginLeft: 6 }}>
                          上涨占比 {stat.winRate.toFixed(0)}%
                        </span>
                      </span>
                    ) : (
                      <span style={{ color: "#9ca3af" }}>
                        {effQuery.isLoading ? "计算中…" : "—"}
                      </span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}
