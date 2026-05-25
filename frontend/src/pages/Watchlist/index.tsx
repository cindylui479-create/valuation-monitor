import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { useState } from "react";
import { fetchWatchlist, removeFromWatchlist } from "@/api/watchlist";
import { usePeSource } from "@/hooks/usePeSource";
import {
  isPriceFallback,
  temperatureColor,
  temperatureSourceLabel,
  tierLabel,
} from "@/utils/temperature";
import StockListSection from "./StockListSection";
import FundListSection from "./FundListSection";

type Tab = "INDEX" | "STOCK" | "FUND";

export default function Watchlist() {
  const [tab, setTab] = useState<Tab>("INDEX");

  return (
    <div className="watchlist-page">
      <h2>自选</h2>
      <div className="view-toggle" style={{ marginBottom: 16 }}>
        <button
          className={tab === "INDEX" ? "active" : ""}
          onClick={() => setTab("INDEX")}
        >
          指数
        </button>
        <button
          className={tab === "STOCK" ? "active" : ""}
          onClick={() => setTab("STOCK")}
        >
          A 股个股
        </button>
        <button
          className={tab === "FUND" ? "active" : ""}
          onClick={() => setTab("FUND")}
        >
          基金
        </button>
      </div>

      {tab === "INDEX" && <IndexList />}
      {tab === "STOCK" && <StockListSection />}
      {tab === "FUND" && <FundListSection />}
    </div>
  );
}

function IndexList() {
  const qc = useQueryClient();
  const peSource = usePeSource();

  const { data, isLoading } = useQuery({
    queryKey: ["watchlist", peSource],
    queryFn: () => fetchWatchlist(peSource),
  });

  const removeMut = useMutation({
    mutationFn: (id: number) => removeFromWatchlist(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["watchlist"] }),
  });

  if (isLoading) return <p className="empty">加载中…</p>;

  if (!data || data.length === 0) {
    return (
      <div className="state">
        <p>暂无自选指数。前往总览页点击"加入自选"，或在详情页底部添加。</p>
        <Link to="/">回到总览</Link>
      </div>
    );
  }

  // 按市场分组（与基金 Tab 视觉一致）
  const byMarket: Record<string, typeof data> = {};
  for (const w of data) {
    const mkt = w.market ?? "?";
    (byMarket[mkt] = byMarket[mkt] ?? []).push(w);
  }

  return (
    <div>
      <p className="hint" style={{ marginBottom: 12 }}>
        共 {data.length} 只自选指数，温度按当前 <code>pe_source={peSource}</code> 取（Settings 全局切换 LG/CSI）。
        点击代码进入详情页查看完整图表与历史信号。
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
                  <th>类别</th>
                  <th>标签</th>
                  <th>温度</th>
                  <th>档位</th>
                  <th>PE-TTM</th>
                  <th>PB</th>
                  <th>股息率</th>
                  <th>口径</th>
                  <th>历史</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {arr.map((w) => {
                  const temp = w.temperature ? parseFloat(w.temperature) : null;
                  const dy = w.dividend_yield ? parseFloat(w.dividend_yield) : null;
                  const pf = isPriceFallback(w.temperature_source);
                  return (
                    <tr key={w.id}>
                      <td>
                        <Link to={`/indices/${encodeURIComponent(w.index_code)}`}>
                          <strong>{w.index_code}</strong>
                        </Link>
                      </td>
                      <td>{w.index_name}</td>
                      <td>
                        {w.category && (
                          <span style={{
                            fontSize: 11, padding: "1px 6px",
                            background: "#e0f2fe", color: "#075985",
                            borderRadius: 4,
                          }}>{w.category}</span>
                        )}
                      </td>
                      <td>{w.tag ?? "—"}</td>
                      <td>
                        {temp != null ? (
                          <>
                            <span style={{
                              background: temperatureColor(temp.toString()),
                              color: "white", padding: "1px 8px",
                              borderRadius: 4, fontSize: 11,
                            }}>{temp.toFixed(1)}</span>
                            {pf && (
                              <span
                                title="价格自比（PE 历史不足时 fallback，与基金 NAV 自比同口径，不反映估值）"
                                style={{ marginLeft: 4, color: "#d97706", fontSize: 11, cursor: "help" }}
                              >⚠</span>
                            )}
                          </>
                        ) : "—"}
                      </td>
                      <td>{w.tier ? tierLabel(w.tier) : "—"}</td>
                      <td>{w.pe_ttm ? parseFloat(w.pe_ttm).toFixed(2) : "—"}</td>
                      <td>{w.pb ? parseFloat(w.pb).toFixed(2) : "—"}</td>
                      <td>{dy != null ? (dy * 100).toFixed(2) + "%" : "—"}</td>
                      <td style={{ fontSize: 11, color: pf ? "#d97706" : "#6b7280" }}>
                        {w.temperature_source
                          ? temperatureSourceLabel(w.temperature_source)
                          : (w.valuation_source ?? "—")}
                      </td>
                      <td style={{ whiteSpace: "nowrap" }}>
                        {w.actual_history_years != null ? w.actual_history_years.toFixed(1) + "y" : "—"}
                        {w.data_window_note && (
                          <span title={w.data_window_note} style={{ marginLeft: 4, color: "#d97706", fontSize: 11 }}>
                            ⓘ
                          </span>
                        )}
                      </td>
                      <td>
                        <button
                          className="btn"
                          onClick={() => {
                            if (confirm(`确认从自选移除 ${w.index_code} ${w.index_name}？`)) {
                              removeMut.mutate(w.id);
                            }
                          }}
                          disabled={removeMut.isPending}
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
        );
      })}
    </div>
  );
}
