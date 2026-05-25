import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { useState } from "react";
import { fetchIndexDetail } from "@/api/indices";
import { addToWatchlist, fetchWatchlist, removeFromWatchlist } from "@/api/watchlist";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { formatPercent, formatTemperature } from "@/utils/decimal";
import {
  isPriceFallback,
  temperatureColor,
  temperatureSourceLabel,
  tierLabel,
} from "@/utils/temperature";
import PriceValuationChart from "./PriceValuationChart";
import PBChart from "./PBChart";
import ThresholdOverrideDialog from "./ThresholdOverrideDialog";
import DCAPlanEditor from "@/pages/DCA/DCAPlanEditor";
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
const directionColor = (d: string) => DIRECTION_COLOR[d] ?? "#9ca3af";

export default function IndexDetail() {
  const { code = "" } = useParams<{ code: string }>();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [dcaOpen, setDcaOpen] = useState(false);
  const qc = useQueryClient();
  const peSource = usePeSource();

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["index-detail", code, peSource],
    queryFn: () => fetchIndexDetail(code, peSource),
    enabled: !!code,
  });

  const { data: watchlist } = useQuery({
    queryKey: ["watchlist", peSource],
    queryFn: () => fetchWatchlist(peSource),
  });

  const inWatchlist = watchlist?.find((w) => w.index_code === code && !w.tag);

  const addMutation = useMutation({
    mutationFn: () => addToWatchlist(code),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["watchlist"] }),
  });
  const removeMutation = useMutation({
    mutationFn: () => removeFromWatchlist(inWatchlist!.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["watchlist"] }),
  });

  if (isLoading) return <div className="state">加载中…</div>;
  if (isError)
    return <div className="state error">加载失败：{(error as Error).message}</div>;
  if (!data) return null;

  const v = data.latest_valuation;
  const pf = isPriceFallback(v?.temperature_source);

  return (
    <div className="detail">
      <header className="detail-header">
        <div>
          <Link to="/" className="back-link">← 总览</Link>
          <h1>
            {data.name}
            <span className="code">{data.code}</span>
          </h1>
          <p className="meta">
            {data.market} · {data.currency} · {data.category}
            {data.industry_raw && <> · {data.industry_raw}</>}
            {data.data_window_note && (
              <span className="window-note"> · {data.data_window_note}</span>
            )}
          </p>
        </div>
        <div className="detail-actions">
          {inWatchlist ? (
            <button
              className="btn"
              onClick={() => removeMutation.mutate()}
              disabled={removeMutation.isPending}
            >
              从自选移除
            </button>
          ) : (
            <button
              className="btn btn-primary"
              onClick={() => addMutation.mutate()}
              disabled={addMutation.isPending}
            >
              加入自选
            </button>
          )}
          <button className="btn" onClick={() => setDcaOpen(true)}>
            加入定投
          </button>
          <button className="btn" onClick={() => setDialogOpen(true)}>
            设置个性化阈值
          </button>
          <a
            className="btn"
            href={`/api/v1/exports/index/${encodeURIComponent(code)}.csv?window=10y`}
            download
          >
            下载 CSV
          </a>
        </div>
      </header>

      {pf && (
        <div style={{
          background: "#fef3c7", color: "#92400e",
          padding: "10px 14px", borderRadius: 4, margin: "12px 0",
          fontSize: 13, border: "1px solid #fde68a",
        }}>
          ⚠ <strong>该指数温度基于价格历史百分位（{temperatureSourceLabel(v?.temperature_source)}）</strong>，
          非 PE-TTM 估值。原因：PE-TTM 历史数据点不足（&lt; 250 天）。
          含义：温度高 = 指数点位接近自身历史高位，<strong>不等于"估值贵"</strong>
          （盈利可能同步增长，分母变大反而更便宜）。与基金 NAV 自比同口径，请谨慎参考。
        </div>
      )}

      {(() => {
        // R7：temperature 为 null = 快照模式（港美股 PE 数据点 < 250）
        const isSnapshot = !v?.temperature;
        const latestQuote = data.quotes[data.quotes.length - 1];
        const latestPe = latestQuote?.pe_ttm;
        const latestPb = latestQuote?.pb;
        const latestDy = latestQuote?.dividend_yield;

        if (isSnapshot) {
          return (
            <section className="latest-card snapshot-card">
              <div className="snapshot-badge">📷 当日快照</div>
              <div className="stat">
                <div className="label">PE-TTM</div>
                <div className="value">{latestPe ? parseFloat(latestPe).toFixed(2) : "—"}</div>
              </div>
              <div className="stat">
                <div className="label">PB</div>
                <div className="value">{latestPb ? parseFloat(latestPb).toFixed(2) : "—"}</div>
              </div>
              <div className="stat">
                <div className="label">股息率</div>
                <div className="value">{formatPercent(latestDy, 2)}</div>
              </div>
              <div className="stat">
                <div className="label">实际行情历史</div>
                <div className="value">{data.actual_history_years.toFixed(1)} 年</div>
              </div>
            </section>
          );
        }
        const ls = data.latest_signal;
        return (
          <section className="latest-card">
            <div
              className="tier-pill"
              style={{ backgroundColor: temperatureColor(v!.temperature) }}
            >
              {tierLabel(v!.tier)}
            </div>
            <div className="stat">
              <div className="label">温度</div>
              <div className="value">{formatTemperature(v!.temperature)}</div>
            </div>
            <div className="stat">
              <div className="label">PE-TTM 10y 分位</div>
              <div className="value">{formatPercent(v!.pe_percentile)}</div>
            </div>
            <div className="stat">
              <div className="label">PB 10y 分位</div>
              <div className="value">{formatPercent(v!.pb_percentile)}</div>
            </div>
            <div className="stat">
              <div className="label">实际历史</div>
              <div className="value">{data.actual_history_years.toFixed(1)} 年</div>
            </div>
            {ls && (
              <div className="stat current-signal">
                <div className="label">当前信号 ({ls.date})</div>
                <div className="value">
                  <span
                    className="tier-badge"
                    style={{ backgroundColor: directionColor(ls.direction) }}
                  >
                    {DIRECTION_LABEL[ls.direction]}
                  </span>
                </div>
              </div>
            )}
          </section>
        );
      })()}

      <section className="chart-block">
        <PriceValuationChart
          quotes={data.quotes}
          valuations={data.valuation_series}
          title={v?.temperature ? "价格 + PE-TTM（含 10y 百分位带）" : "价格历史"}
        />
      </section>

      {/* 港美股快照模式下 PB 历史几乎全为空，隐藏 PB 子图 */}
      {v?.temperature && (
        <section className="chart-block">
          <PBChart quotes={data.quotes} />
        </section>
      )}

      <section className="funds-block">
        <h3>跟踪基金 / ETF</h3>
        {data.funds.length === 0 ? (
          <p className="empty">暂无跟踪基金</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>代码</th>
                <th>名称</th>
                <th>类型</th>
                <th>费率</th>
                <th>备注</th>
              </tr>
            </thead>
            <tbody>
              {data.funds.map((f) => (
                <tr key={f.code}>
                  <td>{f.code}</td>
                  <td>{f.name}</td>
                  <td>{f.type}</td>
                  <td>{formatPercent(f.fee_rate, 2)}</td>
                  <td>{f.tracking_error_note ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {data.signal_history.length > 0 && (
        <section className="signal-timeline">
          <h3>信号历史 ({data.signal_history.length})</h3>
          <ul>
            {data.signal_history.slice(0, 50).map((s, i) => (
              <li key={i}>
                <span className="date">{s.date}</span>
                <span
                  className="tier-badge"
                  style={{ backgroundColor: directionColor(s.direction) }}
                >
                  {DIRECTION_LABEL[s.direction]}
                </span>
                <span className="tier-text">{s.tier}</span>
                <span className="temp">温度 {parseFloat(s.temperature).toFixed(1)}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      <ThresholdOverrideDialog
        open={dialogOpen}
        indexCode={code}
        onClose={() => setDialogOpen(false)}
      />
      <DCAPlanEditor
        open={dcaOpen}
        presetIndexCode={code}
        onClose={() => setDcaOpen(false)}
      />
    </div>
  );
}
