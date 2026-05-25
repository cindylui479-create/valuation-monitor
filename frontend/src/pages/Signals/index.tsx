import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { useState } from "react";
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

  return (
    <div className="signals-page">
      <div className="page-header">
        <h2>估值信号</h2>
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
            </tr>
          </thead>
          <tbody>
            {data.items.map((s) => (
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
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
