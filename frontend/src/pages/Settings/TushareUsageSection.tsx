import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import ReactECharts from "@/components/charts/ReactECharts";
import { fetchTushareUsage } from "@/api/tushareUsage";

export default function TushareUsageSection() {
  const { data, isLoading } = useQuery({
    queryKey: ["tushare-usage"],
    queryFn: fetchTushareUsage,
  });

  // 30 天逐日图：把 API 返回的稀疏点对齐到完整 30 天日历，缺失填 0
  // ⚠ Hook 必须在条件 return 之前调用（React Rules of Hooks）
  const dailyChartOption = useMemo(() => {
    if (!data) return null;
    const today = new Date();
    const days: { date: string; calls: number; failures: number }[] = [];
    const byDate = new Map(data.last_30_days.map((d) => [d.date, d]));
    for (let i = 29; i >= 0; i--) {
      const d = new Date(today);
      d.setDate(d.getDate() - i);
      const key = d.toISOString().slice(0, 10);
      const hit = byDate.get(key);
      days.push({
        date: key,
        calls: hit?.n_calls ?? 0,
        failures: hit?.n_failures ?? 0,
      });
    }
    return {
      grid: { left: 50, right: 60, top: 30, bottom: 40 },
      tooltip: {
        trigger: "axis",
        formatter: (params: any) => {
          const d = days[params[0].dataIndex];
          return `${d.date}<br/>调用 ${d.calls.toLocaleString()}<br/>` +
            (d.failures > 0 ? `<span style="color:#b91c1c">失败 ${d.failures}</span>` : "无失败");
        },
      },
      legend: {
        data: ["调用次数", "失败次数"],
        top: 0,
        textStyle: { fontSize: 11 },
      },
      xAxis: {
        type: "category",
        data: days.map((d) => d.date.slice(5)),
        axisLabel: { fontSize: 10, interval: 4 },
      },
      yAxis: [
        {
          type: "value",
          name: "调用",
          position: "left",
          nameTextStyle: { fontSize: 10 },
          axisLabel: { fontSize: 10 },
        },
        {
          type: "value",
          name: "失败",
          position: "right",
          nameTextStyle: { fontSize: 10 },
          axisLabel: { fontSize: 10 },
          splitLine: { show: false },
        },
      ],
      series: [
        {
          name: "调用次数",
          type: "bar",
          data: days.map((d) => d.calls),
          itemStyle: { color: "#2563eb" },
          barWidth: "60%",
        },
        {
          name: "失败次数",
          type: "line",
          yAxisIndex: 1,
          data: days.map((d) => d.failures),
          itemStyle: { color: "#dc2626" },
          lineStyle: { width: 2 },
          symbolSize: 6,
        },
      ],
    };
  }, [data]);

  if (isLoading) {
    return (
      <section className="settings-block">
        <h3>Tushare 配额监控（v1.3.0 E）</h3>
        <p className="empty">加载中…</p>
      </section>
    );
  }
  if (!data) return null;

  const todayFailureRate = data.today.total_calls > 0
    ? (data.today.total_failures / data.today.total_calls * 100).toFixed(1)
    : "0.0";
  const monthFailureRate = data.month.total_calls > 0
    ? (data.month.total_failures / data.month.total_calls * 100).toFixed(1)
    : "0.0";

  return (
    <section className="settings-block">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h3>Tushare 配额监控（v1.3.0 E）</h3>
        <span style={{ fontSize: 12, color: "var(--muted)" }}>
          2000 积分用户限制：200 调用/分；个别接口（成分股聚合占 80%+）月度积分有上限
        </span>
      </div>

      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
        gap: 12, margin: "12px 0",
      }}>
        <div style={{ background: "white", padding: 12, borderRadius: 4, border: "1px solid #e5e7eb" }}>
          <div style={{ fontSize: 11, color: "#6b7280" }}>今日调用</div>
          <div style={{ fontSize: 24, fontWeight: 600 }}>
            {data.today.total_calls.toLocaleString()}
          </div>
          <div style={{ fontSize: 11, color: data.today.total_failures > 0 ? "#b91c1c" : "#15803d" }}>
            失败 {data.today.total_failures}（{todayFailureRate}%）
          </div>
        </div>
        <div style={{ background: "white", padding: 12, borderRadius: 4, border: "1px solid #e5e7eb" }}>
          <div style={{ fontSize: 11, color: "#6b7280" }}>本月调用（自 {data.month.month_start}）</div>
          <div style={{ fontSize: 24, fontWeight: 600 }}>
            {data.month.total_calls.toLocaleString()}
          </div>
          <div style={{ fontSize: 11, color: data.month.total_failures > 0 ? "#b91c1c" : "#15803d" }}>
            失败 {data.month.total_failures}（{monthFailureRate}%）
          </div>
        </div>
      </div>

      {/* 30 天逐日图（蓝柱=调用次数，红线=失败次数；hover 看明细） */}
      {dailyChartOption && (
        <div style={{ marginBottom: 12 }}>
          <div style={{ fontSize: 12, color: "#6b7280", marginBottom: 4 }}>近 30 天逐日</div>
          <ReactECharts option={dailyChartOption} style={{ height: 200 }} />
        </div>
      )}

      {/* 接口分布 */}
      {data.by_interface_30d.length > 0 && (
        <div>
          <div style={{ fontSize: 12, color: "#6b7280", marginBottom: 4 }}>近 30 天按接口分布</div>
          <table className="table" style={{ fontSize: 12 }}>
            <thead>
              <tr>
                <th>接口</th>
                <th>调用次数</th>
                <th>失败次数</th>
                <th>失败率</th>
                <th>最近错误</th>
              </tr>
            </thead>
            <tbody>
              {data.by_interface_30d.map((it) => {
                const rate = it.n_calls > 0
                  ? (it.n_failures / it.n_calls * 100).toFixed(1)
                  : "0.0";
                return (
                  <tr key={it.interface}>
                    <td><strong>{it.interface}</strong></td>
                    <td>{it.n_calls.toLocaleString()}</td>
                    <td style={{ color: it.n_failures > 0 ? "#b91c1c" : undefined }}>
                      {it.n_failures}
                    </td>
                    <td>{rate}%</td>
                    <td style={{ color: "#6b7280", fontSize: 11 }}>
                      {it.last_error_message ?? "—"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      <p className="hint">
        若某接口失败率突然飙升，可能是配额耗尽 — 查看 Tushare 用户中心的积分余额。
        成分股聚合（daily_basic + index_weight）每日 A 调度跑一次约 250-300 次调用。
      </p>
    </section>
  );
}
