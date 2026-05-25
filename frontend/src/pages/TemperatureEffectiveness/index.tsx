/**
 * SRS v1.3.0 EFF：温度有效性分析。
 *
 * 不再回顾"信号事件"（样本太少），改为回顾"温度档位 → 未来收益"的统计关系。
 * 每只指数每个交易日都是一个数据点（10 年 × 24 指数 ≈ 5 万样本）。
 */
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import ReactECharts from "@/components/charts/ReactECharts";
import { fetchEffectiveness } from "@/api/effectiveness";

const TIER_COLOR: Record<string, string> = {
  极度低估: "#15803d",
  低估: "#22c55e",
  合理: "#9ca3af",
  高估: "#f87171",
  极度高估: "#b91c1c",
};

export default function TemperatureEffectiveness() {
  const [horizon, setHorizon] = useState(90);
  const [years, setYears] = useState(10);
  const [indexCode, setIndexCode] = useState<string>("");

  const { data, isLoading } = useQuery({
    queryKey: ["effectiveness", horizon, years, indexCode],
    queryFn: () => fetchEffectiveness(horizon, years, indexCode || undefined),
  });

  // 主图：5 档位柱状图 + P25/P75 误差棒
  const coarseOption = useMemo(() => {
    if (!data) return null;
    const buckets = data.coarse_buckets;
    return {
      grid: { left: 60, right: 30, top: 40, bottom: 60 },
      tooltip: {
        trigger: "axis",
        formatter: (params: any) => {
          const i = params[0].dataIndex;
          const b = buckets[i];
          if (b.n_samples === 0) return `${b.tier}：无样本`;
          return `<strong>${b.tier}</strong> (温度 ${b.temp_range}, n=${b.n_samples})<br/>
            中位收益 ${b.median_return_pct}%<br/>
            均值 ${b.mean_return_pct}%<br/>
            P25/P75 ${b.p25}% / ${b.p75}%<br/>
            P10/P90 ${b.p10}% / ${b.p90}%<br/>
            胜率 ${b.win_rate}%`;
        },
      },
      xAxis: {
        type: "category",
        data: buckets.map((b) => `${b.tier}\n${b.temp_range}`),
        axisLabel: { interval: 0 },
      },
      yAxis: {
        type: "value",
        name: `${horizon} 天后中位收益 %`,
        axisLine: { onZero: true },
      },
      series: [
        {
          type: "bar",
          name: "中位收益",
          data: buckets.map((b) => ({
            value: b.median_return_pct ? parseFloat(b.median_return_pct) : 0,
            itemStyle: { color: TIER_COLOR[b.tier] ?? "#9ca3af" },
          })),
          barWidth: "45%",
          markLine: {
            silent: true,
            symbol: "none",
            data: [{ yAxis: 0, lineStyle: { color: "#000", type: "solid", width: 1 } }],
          },
        },
        {
          type: "custom",
          name: "P25–P75 区间",
          renderItem: (params: any, api: any) => {
            const b = buckets[params.dataIndex];
            if (!b.p25 || !b.p75) return null;
            const x = api.coord([params.dataIndex, 0])[0];
            const yTop = api.coord([params.dataIndex, parseFloat(b.p75)])[1];
            const yBot = api.coord([params.dataIndex, parseFloat(b.p25)])[1];
            return {
              type: "group",
              children: [
                {
                  type: "line",
                  shape: { x1: x, y1: yTop, x2: x, y2: yBot },
                  style: { stroke: "#374151", lineWidth: 1.5 },
                },
                {
                  type: "line",
                  shape: { x1: x - 10, y1: yTop, x2: x + 10, y2: yTop },
                  style: { stroke: "#374151", lineWidth: 1.5 },
                },
                {
                  type: "line",
                  shape: { x1: x - 10, y1: yBot, x2: x + 10, y2: yBot },
                  style: { stroke: "#374151", lineWidth: 1.5 },
                },
              ],
            };
          },
          data: buckets.map(() => 0),
        },
      ],
    };
  }, [data, horizon]);

  // 散点图：10 度细分
  const fineOption = useMemo(() => {
    if (!data) return null;
    const points = data.fine_buckets.filter((p) => p.n_samples > 0);
    return {
      grid: { left: 60, right: 30, top: 40, bottom: 60 },
      tooltip: {
        trigger: "axis",
        formatter: (params: any) => {
          const p = points[params[0].dataIndex];
          return `温度 ${p.temp_center} (±5)，n=${p.n_samples}<br/>中位收益 ${p.median_return_pct}%`;
        },
      },
      xAxis: {
        type: "value",
        name: "温度档位（10 度细分）",
        min: 0, max: 100,
        splitLine: { show: true },
      },
      yAxis: {
        type: "value",
        name: `${horizon} 天后中位收益 %`,
        axisLine: { onZero: true },
      },
      series: [
        {
          type: "line",
          smooth: true,
          symbolSize: 12,
          data: points.map((p) => [
            p.temp_center,
            p.median_return_pct ? parseFloat(p.median_return_pct) : null,
          ]),
          lineStyle: { width: 2, color: "#2563eb" },
          itemStyle: { color: "#2563eb" },
          markLine: {
            silent: true,
            symbol: "none",
            data: [{ yAxis: 0, lineStyle: { color: "#000", type: "solid", width: 1 } }],
          },
        },
      ],
    };
  }, [data, horizon]);

  if (isLoading) return <div className="state">加载中…</div>;
  if (!data) return null;

  return (
    <div className="watchlist-page">
      <h2>温度有效性分析</h2>
      <p className="hint">
        把每只指数的每个交易日当一个数据点，看不同温度档位的<strong>未来 N 天收益</strong>分布。
        若"低估买入"假设成立，应该看到温度 &lt; 30 的中位收益显著高于温度 &gt; 70 的（单调左高右低）。
        实证可能反直觉 — 让你诚实面对当前温度阈值是否真有预测力。
      </p>

      <div style={{ display: "flex", gap: 16, alignItems: "center", marginBottom: 16, flexWrap: "wrap" }}>
        <label style={{ display: "flex", alignItems: "center", gap: 6 }}>
          Horizon：
          <select value={horizon} onChange={(e) => setHorizon(Number(e.target.value))}>
            <option value={30}>30 天</option>
            <option value={90}>90 天</option>
            <option value={180}>180 天</option>
            <option value={365}>365 天</option>
            <option value={730}>730 天（2 年）</option>
          </select>
        </label>
        <label style={{ display: "flex", alignItems: "center", gap: 6 }}>
          历史范围：
          <select value={years} onChange={(e) => setYears(Number(e.target.value))}>
            <option value={3}>3 年</option>
            <option value={5}>5 年</option>
            <option value={10}>10 年</option>
            <option value={15}>15 年</option>
          </select>
        </label>
        <label style={{ display: "flex", alignItems: "center", gap: 6 }}>
          范围：
          <select value={indexCode} onChange={(e) => setIndexCode(e.target.value)}>
            <option value="">全部指数</option>
            {data.indices_coverage.map((c) => (
              <option key={c.code} value={c.code}>
                {c.code} {c.name} ({c.n_samples})
              </option>
            ))}
          </select>
        </label>
        <span style={{ marginLeft: "auto", fontSize: 12, color: "#6b7280" }}>
          样本量：{data.total_samples.toLocaleString()}
        </span>
      </div>

      {/* SRS v1.3.0 C：全局 IC 顶端卡 */}
      {data.spearman_ic != null && (
        <section className="settings-block">
          <h3>Spearman IC（温度 ↔ 未来 {horizon} 天收益的秩相关）</h3>
          <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
            <div style={{
              fontSize: 36, fontWeight: 700,
              color: (() => {
                const ic = parseFloat(data.spearman_ic);
                return ic <= -0.05 ? "#15803d" : ic >= 0.05 ? "#dc2626" : "#6b7280";
              })(),
            }}>
              {parseFloat(data.spearman_ic).toFixed(4)}
            </div>
            <div style={{ fontSize: 12, color: "#6b7280" }}>
              <div>负值（接近 -1）= 温度越高，未来收益越低，<strong>逆温度策略有效</strong>。</div>
              <div>0 附近 = 温度无预测力。</div>
              <div>正值 = 反向（高温度反而后续涨）— 与逆向投资假设相悖。</div>
              <div style={{ marginTop: 4, fontSize: 11 }}>
                |IC| &lt; 0.05 通常视为"无显著信号"；|IC| ≥ 0.05 算"弱信号"；≥ 0.10 算"中等信号"。
              </div>
            </div>
          </div>
        </section>
      )}

      <section className="settings-block">
        <h3>5 档位 vs 未来 {horizon} 天收益</h3>
        {coarseOption && (
          <ReactECharts option={coarseOption} style={{ height: 360 }} />
        )}
        <p className="hint">
          柱高 = 该档位历史样本的未来收益<strong>中位数</strong>；竖线 = P25–P75 区间（中间 50% 样本的收益）。
          理想假设：左侧（低估）柱高 &gt; 0，右侧（高估）柱高 &lt; 0。
        </p>
      </section>

      <section className="settings-block">
        <h3>温度精细分桶（10 度一档）</h3>
        {fineOption && (
          <ReactECharts option={fineOption} style={{ height: 320 }} />
        )}
        <p className="hint">
          每 10 度一个数据点。理想假设：折线从左上往右下走（温度越高未来收益越低）。
        </p>
      </section>

      <section className="settings-block">
        <h3>明细数据</h3>
        <table className="table">
          <thead>
            <tr>
              <th>档位</th>
              <th>温度</th>
              <th>样本</th>
              <th>中位收益</th>
              <th>均值</th>
              <th>P10</th>
              <th>P25</th>
              <th>P75</th>
              <th>P90</th>
              <th>胜率</th>
            </tr>
          </thead>
          <tbody>
            {data.coarse_buckets.map((b) => (
              <tr key={b.tier}>
                <td>
                  <span style={{
                    background: TIER_COLOR[b.tier] ?? "#9ca3af",
                    color: "white", padding: "1px 8px",
                    borderRadius: 4, fontSize: 11,
                  }}>{b.tier}</span>
                </td>
                <td>{b.temp_range}</td>
                <td>{b.n_samples.toLocaleString()}</td>
                <td><strong>{b.median_return_pct ?? "—"}%</strong></td>
                <td>{b.mean_return_pct ?? "—"}%</td>
                <td>{b.p10 ?? "—"}%</td>
                <td>{b.p25 ?? "—"}%</td>
                <td>{b.p75 ?? "—"}%</td>
                <td>{b.p90 ?? "—"}%</td>
                <td>{b.win_rate ?? "—"}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {/* SRS v1.3.0 C：按指数对比 */}
      {data.by_index_effectiveness.length > 0 && (
        <section className="settings-block">
          <h3>按指数对比（{data.by_index_effectiveness.length} 只 ≥ 50 样本）</h3>
          <p className="hint">
            按 |IC| 降序 — 哪些指数的温度信号最有效。
            <strong>edge = 高温度桶中位收益 − 低温度桶中位收益</strong>，理想为负
            （低估时未来涨得比高估时多）。
          </p>
          <table className="table">
            <thead>
              <tr>
                <th>代码</th>
                <th>名称</th>
                <th>样本数</th>
                <th>Spearman IC</th>
                <th>低估桶<br/>中位收益</th>
                <th>高估桶<br/>中位收益</th>
                <th>edge<br/>（高−低）</th>
              </tr>
            </thead>
            <tbody>
              {data.by_index_effectiveness.map((b) => {
                const ic = b.spearman_ic ? parseFloat(b.spearman_ic) : null;
                const edge = b.edge_pct ? parseFloat(b.edge_pct) : null;
                const icColor = ic == null ? "#6b7280"
                  : ic <= -0.05 ? "#15803d"
                  : ic >= 0.05 ? "#dc2626"
                  : "#6b7280";
                const edgeColor = edge == null ? "#6b7280"
                  : edge < -2 ? "#15803d"
                  : edge > 2 ? "#dc2626"
                  : "#6b7280";
                return (
                  <tr key={b.code}>
                    <td><strong>{b.code}</strong></td>
                    <td>{b.name}</td>
                    <td>{b.n_samples.toLocaleString()}</td>
                    <td style={{ color: icColor, fontWeight: 600 }}>
                      {ic != null ? ic.toFixed(4) : "—"}
                    </td>
                    <td>{b.low_temp_median_return ?? "—"}%</td>
                    <td>{b.high_temp_median_return ?? "—"}%</td>
                    <td style={{ color: edgeColor, fontWeight: 600 }}>
                      {edge != null ? `${edge > 0 ? "+" : ""}${edge.toFixed(2)}%` : "—"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </section>
      )}
    </div>
  );
}
