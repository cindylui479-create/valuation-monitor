import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { runBacktest } from "@/api/backtest";
import { fetchIndicesList } from "@/api/indicesList";
import { formatNumber, formatPercent } from "@/utils/decimal";
import type { BacktestResponse, StrategyResultDTO } from "@/types/api";
import NAVChart from "./NAVChart";

const STRATEGY_LABEL: Record<string, string> = {
  threshold: "阈值策略",
  dca: "定投策略",
  buy_hold: "买入持有（基准）",
  by_temperature: "按温度调仓",
};

function StrategyKPI({ s }: { s: StrategyResultDTO }) {
  return (
    <div className="strategy-kpi">
      <h4>{STRATEGY_LABEL[s.name]}</h4>
      <div className="kpi-row inline">
        <div className="kpi">
          <div className="label">年化</div>
          <div className="value">{formatPercent(s.annualized_return, 2)}</div>
        </div>
        <div className="kpi">
          <div className="label">最大回撤</div>
          <div className="value drawdown">{formatPercent(s.max_drawdown, 2)}</div>
        </div>
        <div className="kpi">
          <div className="label">最终 NAV</div>
          <div className="value">{formatNumber(s.final_nav, 3)}</div>
        </div>
        <div className="kpi">
          <div className="label">交易次数</div>
          <div className="value">{s.trade_count}</div>
        </div>
      </div>
    </div>
  );
}

export default function Backtest() {
  const { data: indices } = useQuery({
    queryKey: ["indices-list"],
    queryFn: fetchIndicesList,
  });

  const [form, setForm] = useState({
    index_code: "",
    buy_percentile_below: "0.20",
    sell_percentile_above: "0.80",
    start_date: "",
    end_date: "",
    window: "10y" as "5y" | "10y" | "all",
    fee_rate: "0",
    slippage_rate: "0",
    reinvest_dividend: false,
    include_dca: true,
  });
  const [result, setResult] = useState<BacktestResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const runMut = useMutation({
    mutationFn: () => runBacktest({
      index_code: form.index_code,
      buy_percentile_below: form.buy_percentile_below,
      sell_percentile_above: form.sell_percentile_above,
      start_date: form.start_date || undefined,
      end_date: form.end_date || undefined,
      window: form.window,
      fee_rate: form.fee_rate || "0",
      slippage_rate: form.slippage_rate || "0",
      reinvest_dividend: form.reinvest_dividend,
      include_dca: form.include_dca,
    }),
    onSuccess: (r) => { setResult(r); setError(null); },
    onError: (e: Error) => { setError(e.message); setResult(null); },
  });

  return (
    <div className="backtest-page">
      <div className="page-header"><h2>回测</h2></div>
      <p className="hint">
        三策略并行：<strong>阈值策略</strong>（PE 分位 &lt; 买入 / &gt; 卖出）+ <strong>定投策略</strong>（每月按 multiplier 加仓）+ <strong>买入持有</strong>（基准）。
        <br />可选手续费 / 滑点 / 分红再投资；定投策略的 multiplier 自动遵循该指数当前个性化阈值（SRS D6）。
      </p>

      <form className="bt-form" onSubmit={(e) => { e.preventDefault(); runMut.mutate(); }}>
        <label className="field"><span>指数</span>
          <select value={form.index_code} onChange={(e) => setForm({ ...form, index_code: e.target.value })} required>
            <option value="">— 选择 —</option>
            {(indices ?? []).map((i) => (
              <option key={i.code} value={i.code}>[{i.market}] {i.name} ({i.code})</option>
            ))}
          </select>
        </label>
        <label className="field"><span>买入阈值（PE &lt;）</span>
          <input type="number" step="0.01" min={0} max={1}
            value={form.buy_percentile_below}
            onChange={(e) => setForm({ ...form, buy_percentile_below: e.target.value })} required />
        </label>
        <label className="field"><span>卖出阈值（PE &gt;）</span>
          <input type="number" step="0.01" min={0} max={1}
            value={form.sell_percentile_above}
            onChange={(e) => setForm({ ...form, sell_percentile_above: e.target.value })} required />
        </label>
        <label className="field"><span>起始日</span>
          <input type="date" value={form.start_date}
            onChange={(e) => setForm({ ...form, start_date: e.target.value })} />
        </label>
        <label className="field"><span>结束日</span>
          <input type="date" value={form.end_date}
            onChange={(e) => setForm({ ...form, end_date: e.target.value })} />
        </label>
        <label className="field"><span>窗口</span>
          <select value={form.window}
            onChange={(e) => setForm({ ...form, window: e.target.value as typeof form.window })}>
            <option value="5y">近 5 年</option>
            <option value="10y">近 10 年</option>
            <option value="all">全历史</option>
          </select>
        </label>
        <label className="field"><span>手续费率 (双向)</span>
          <input type="number" step="0.0001" min={0} max={0.05}
            value={form.fee_rate}
            onChange={(e) => setForm({ ...form, fee_rate: e.target.value })}
            placeholder="0.0003" />
        </label>
        <label className="field"><span>滑点率</span>
          <input type="number" step="0.0001" min={0} max={0.05}
            value={form.slippage_rate}
            onChange={(e) => setForm({ ...form, slippage_rate: e.target.value })}
            placeholder="0.0005" />
        </label>
        <label className="field horizontal">
          <input type="checkbox" checked={form.reinvest_dividend}
            onChange={(e) => setForm({ ...form, reinvest_dividend: e.target.checked })} />
          <span>分红再投资<br /><small style={{ color: "#9ca3af" }}>A 股股息率历史仅最近 20 天</small></span>
        </label>
        <label className="field horizontal">
          <input type="checkbox" checked={form.include_dca}
            onChange={(e) => setForm({ ...form, include_dca: e.target.checked })} />
          <span>包含定投策略</span>
        </label>

        <button type="submit" className="btn btn-primary" disabled={runMut.isPending}>
          {runMut.isPending ? "回测中…" : "运行"}
        </button>
      </form>

      {error && <div className="state error">{error}</div>}

      {result && (
        <section className="bt-result">
          <h3>结果 — {result.index_name} ({result.index_code})</h3>
          <p className="hint" style={{ background: "transparent", border: "none", padding: 0 }}>
            区间：{result.start_date} → {result.end_date}
            {result.fee_rate !== "0" && ` · 手续费 ${(parseFloat(result.fee_rate) * 100).toFixed(2)}%`}
            {result.slippage_rate !== "0" && ` · 滑点 ${(parseFloat(result.slippage_rate) * 100).toFixed(2)}%`}
            {result.reinvest_dividend && " · 分红再投资"}
          </p>

          <NAVChart strategies={[result.threshold, result.dca, result.buy_hold, result.by_temperature]} />

          <div className="strategy-grid">
            <StrategyKPI s={result.threshold} />
            {result.dca && <StrategyKPI s={result.dca} />}
            <StrategyKPI s={result.buy_hold} />
            {result.by_temperature && <StrategyKPI s={result.by_temperature} />}
          </div>

          <h4>阈值策略交易明细 ({result.threshold.trade_count})</h4>
          {result.threshold.trades.length === 0 ? (
            <p className="empty">无交易（策略阈值未触发）</p>
          ) : (
            <table className="table">
              <thead>
                <tr><th>日期</th><th>动作</th><th>价格</th><th>PE 分位</th></tr>
              </thead>
              <tbody>
                {result.threshold.trades.map((t, i) => (
                  <tr key={i}>
                    <td>{t.date}</td>
                    <td>
                      <span
                        className="tier-badge"
                        style={{ backgroundColor: t.action === "BUY" ? "#22c55e" : "#f87171" }}
                      >
                        {t.action === "BUY" ? "买入" : "卖出"}
                      </span>
                    </td>
                    <td>{formatNumber(t.price, 2)}</td>
                    <td>{t.pe_percentile ? formatPercent(t.pe_percentile, 1) : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          {result.dca && result.dca.trades.length > 0 && (
            <>
              <h4>定投策略交易明细 ({result.dca.trade_count})</h4>
              <details>
                <summary>展开（共 {result.dca.trades.length} 笔）</summary>
                <table className="table">
                  <thead>
                    <tr><th>日期</th><th>×multiplier</th><th>价格</th><th>金额</th><th>PE 分位</th></tr>
                  </thead>
                  <tbody>
                    {result.dca.trades.map((t, i) => (
                      <tr key={i}>
                        <td>{t.date}</td>
                        <td>×{formatNumber(t.multiplier ?? "1", 2)}</td>
                        <td>{formatNumber(t.price, 2)}</td>
                        <td>{formatNumber(t.amount, 4)}</td>
                        <td>{t.pe_percentile ? formatPercent(t.pe_percentile, 1) : "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </details>
            </>
          )}
        </section>
      )}
    </div>
  );
}
