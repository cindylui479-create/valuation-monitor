import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { fetchPreferences, updatePreferences } from "@/api/preferences";
import { fetchHealth } from "@/api/health";
import { fetchPipelineRuns } from "@/api/pipelineRuns";
import DataQualitySection from "./DataQualitySection";
import TushareUsageSection from "./TushareUsageSection";

const SCHEDULE_TABLE = [
  { market: "A", time: "16:30 (UTC+8)", note: "A 股收盘后 30 分钟" },
  { market: "HK", time: "17:30 (UTC+8)", note: "港股收盘后 90 分钟" },
  { market: "US", time: "次日 07:00 (UTC+8)", note: "美东 19:00 左右" },
];

export default function Settings() {
  const qc = useQueryClient();
  const [runDays, setRunDays] = useState(30);
  const prefs = useQuery({ queryKey: ["preferences"], queryFn: fetchPreferences });
  const health = useQuery({ queryKey: ["health"], queryFn: fetchHealth });
  const runs = useQuery({
    queryKey: ["pipeline-runs", runDays],
    queryFn: () => fetchPipelineRuns(runDays),
  });

  const updateMut = useMutation({
    mutationFn: (p: Record<string, unknown>) => updatePreferences(p),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["preferences"] }),
  });

  return (
    <div className="settings-page">
      <h2>设置</h2>

      <section className="settings-block">
        <h3>偏好</h3>
        <label className="field horizontal">
          <span>PE 口径（SRS R10）</span>
          <select
            value={prefs.data?.pe_source ?? "lg"}
            onChange={(e) => updateMut.mutate({ pe_source: e.target.value })}
          >
            <option value="lg">LG（乐咕乐股，散户社区主流）</option>
            <option value="csi">CSI（中证指数公司官方，同花顺/东方财富等）</option>
          </select>
        </label>
        <p className="hint">
          切换后全站立即按新口径展示温度、分位与信号。
          CSI 仅完整覆盖 6 只指数（沪深300/中证500/上证50/上证综指/深证成指/创业板指），
          其余指数自动 fallback 到 LG，标签栏会标注 <code>(LG fallback)</code>。
        </p>

        <label className="field horizontal" style={{ marginTop: 12 }}>
          <span>详情页默认百分位窗口</span>
          <select
            value={prefs.data?.default_window ?? "10y"}
            onChange={(e) => updateMut.mutate({ default_window: e.target.value })}
          >
            <option value="5y">近 5 年</option>
            <option value="10y">近 10 年</option>
            <option value="all">全历史</option>
          </select>
        </label>
        <p className="hint">仅用于浏览；信号与温度仍固定锚定近 10 年（SRS D1）。</p>
      </section>

      <section className="settings-block">
        <h3>每日批处理调度</h3>
        <table className="table">
          <thead>
            <tr><th>市场</th><th>时刻</th><th>说明</th><th>最近一次</th><th>状态</th></tr>
          </thead>
          <tbody>
            {SCHEDULE_TABLE.map((s) => {
              const ps = (health.data?.pipeline ?? []).find((p) => p.market === s.market);
              return (
                <tr key={s.market}>
                  <td><strong>{s.market}</strong></td>
                  <td>{s.time}</td>
                  <td>{s.note}</td>
                  <td>{ps?.last_run_at ? ps.last_run_at.slice(0, 19).replace("T", " ") : "—"}</td>
                  <td>
                    {ps ? (
                      <span className={"badge status-" + ps.status.toLowerCase()}>{ps.status}</span>
                    ) : "—"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        <p className="hint">
          系统启动后自动跑；只要 uvicorn 进程在运行，每天会按此时刻自动拉取数据 + 计算分位 + 生成信号 + 刷新定投提醒。
        </p>
      </section>

      <TushareUsageSection />

      <DataQualitySection />

      <section className="settings-block">
        <h3>数据源健康</h3>
        {(health.data?.sources ?? []).length === 0 ? (
          <p className="empty">尚未运行过批处理。</p>
        ) : (
          <table className="table">
            <thead>
              <tr><th>数据源</th><th>最近成功</th><th>最近失败</th></tr>
            </thead>
            <tbody>
              {(health.data?.sources ?? []).map((s) => (
                <tr key={s.name}>
                  <td><strong>{s.name}</strong></td>
                  <td>{s.last_success_at ? s.last_success_at.slice(0, 19).replace("T", " ") : "—"}</td>
                  <td>
                    {s.last_error_at ? (
                      <span title={s.last_error_message ?? ""}>
                        {s.last_error_at.slice(0, 19).replace("T", " ")}
                      </span>
                    ) : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section className="settings-block">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h3>批处理运行历史</h3>
          <select value={runDays} onChange={(e) => setRunDays(Number(e.target.value))}>
            <option value={7}>近 7 天</option>
            <option value={30}>近 30 天</option>
            <option value={90}>近 90 天</option>
            <option value={365}>近 1 年</option>
          </select>
        </div>
        <p className="hint">
          按 (日期, 市场) 聚合 4 张事件表：行情入库、字段变更、信号生成、定投提醒。
          大行数（如数千行）多半是 <code>init_history</code> 手动初始化；小行数为日常增量。
        </p>
        {runs.data && runs.data.items.length === 0 ? (
          <p className="empty">该时间段内无运行记录</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>日期</th>
                <th>市场</th>
                <th>入库</th>
                <th>字段变更</th>
                <th>新信号</th>
                <th>定投提醒</th>
                <th>首事件</th>
                <th>末事件</th>
              </tr>
            </thead>
            <tbody>
              {(runs.data?.items ?? []).map((r, i) => (
                <tr key={`${r.date}-${r.market}-${i}`}>
                  <td>{r.date}</td>
                  <td><strong>{r.market}</strong></td>
                  <td>{r.quotes_upserted}</td>
                  <td>{r.audits_logged}</td>
                  <td>{r.signals_generated > 0 ? <strong style={{ color: "#2563eb" }}>{r.signals_generated}</strong> : 0}</td>
                  <td>{r.dca_executions_generated}</td>
                  <td>{r.first_event_at ? r.first_event_at.slice(11, 19) : "—"}</td>
                  <td>{r.last_event_at ? r.last_event_at.slice(11, 19) : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
