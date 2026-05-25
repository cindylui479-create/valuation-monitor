import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { useState } from "react";
import {
  deleteDCAPlan,
  fetchDCAPlans,
  fetchDCAStats,
  fetchUpcoming,
  markDone,
  markSkipped,
} from "@/api/dca";
import { formatNumber } from "@/utils/decimal";
import { temperatureColor } from "@/utils/temperature";
import type { DCAPlanDTO } from "@/types/api";
import DCAPlanEditor from "./DCAPlanEditor";

const FREQ_LABEL: Record<string, string> = {
  WEEKLY: "每周",
  BIWEEKLY: "每两周",
  MONTHLY: "每月",
};

export default function DCA() {
  const qc = useQueryClient();
  const [editorOpen, setEditorOpen] = useState(false);
  const [editing, setEditing] = useState<DCAPlanDTO | null>(null);

  const upcoming = useQuery({
    queryKey: ["dca-upcoming"],
    queryFn: () => fetchUpcoming(7),
  });
  const plans = useQuery({ queryKey: ["dca-plans"], queryFn: fetchDCAPlans });
  const stats = useQuery({ queryKey: ["dca-stats"], queryFn: fetchDCAStats });

  const refreshAll = () => {
    qc.invalidateQueries({ queryKey: ["dca-upcoming"] });
    qc.invalidateQueries({ queryKey: ["dca-stats"] });
  };

  const doneMut = useMutation({
    mutationFn: (id: number) => markDone(id),
    onSuccess: refreshAll,
  });
  const skipMut = useMutation({
    mutationFn: (id: number) => markSkipped(id),
    onSuccess: refreshAll,
  });
  const delMut = useMutation({
    mutationFn: (id: number) => deleteDCAPlan(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["dca-plans"] });
      refreshAll();
    },
  });

  return (
    <div className="dca-page">
      <div className="page-header">
        <h2>定投计划</h2>
        <button
          className="btn btn-primary"
          onClick={() => {
            setEditing(null);
            setEditorOpen(true);
          }}
        >
          新建定投
        </button>
      </div>

      {/* 累计统计 */}
      {stats.data && stats.data.plans.length > 0 && (
        <section className="dca-stats">
          <div className="kpi-row">
            <div className="kpi">
              <div className="label">累计已投入</div>
              <div className="value">¥{formatNumber(stats.data.total_done_amount, 2)}</div>
            </div>
            <div className="kpi">
              <div className="label">累计跳过</div>
              <div className="value">¥{formatNumber(stats.data.total_skipped_amount, 2)}</div>
            </div>
            <div className="kpi">
              <div className="label">活跃计划</div>
              <div className="value">{stats.data.plans.length}</div>
            </div>
          </div>
          <details>
            <summary>各计划明细（点击展开）</summary>
            <table className="table">
              <thead>
                <tr>
                  <th>指数</th>
                  <th>已执行 / 跳过 / 待执行</th>
                  <th>累计投入</th>
                  <th>因调整省下</th>
                  <th>跳过率</th>
                  <th>平均 multiplier</th>
                </tr>
              </thead>
              <tbody>
                {stats.data.plans.map((p) => {
                  const saved = parseFloat(p.base_total_if_no_adjustment) -
                                parseFloat(p.done_total_amount) -
                                parseFloat(p.skipped_total_amount);
                  return (
                    <tr key={p.plan_id}>
                      <td>
                        <Link to={`/indices/${encodeURIComponent(p.index_code)}`}>
                          {p.index_name}
                        </Link>
                      </td>
                      <td>{p.done_count} / {p.skipped_count} / {p.pending_count}</td>
                      <td>¥{formatNumber(p.done_total_amount, 2)}</td>
                      <td>¥{saved.toFixed(2)}</td>
                      <td>{(parseFloat(p.skip_ratio) * 100).toFixed(1)}%</td>
                      <td>×{formatNumber(p.average_multiplier, 2)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </details>
        </section>
      )}

      {/* 未来 7 天提醒 */}
      <section className="upcoming-section">
        <h3>未来 7 天提醒</h3>
        {upcoming.data && upcoming.data.items.length === 0 ? (
          <p className="empty">暂无待执行提醒</p>
        ) : (
          <div className="reminder-grid">
            {(upcoming.data?.items ?? []).map((e) => (
              <div key={e.id} className="reminder-card">
                <div className="card-head">
                  <Link to={`/indices/${encodeURIComponent(e.index_code)}`}>
                    <strong>{e.index_name}</strong>
                  </Link>
                  <span
                    className="tier-badge"
                    style={{ backgroundColor: temperatureColor(e.temperature) }}
                  >
                    {e.tier_at_decision}
                  </span>
                </div>
                <div className="card-body">
                  <div>
                    定投日 <strong>{e.actual_date}</strong>
                    {e.scheduled_date !== e.actual_date && (
                      <span className="hint"> （顺延自 {e.scheduled_date}）</span>
                    )}
                  </div>
                  <div className="amount-line">
                    <span className="label">基础</span>
                    <span>¥{formatNumber(e.base_amount, 2)}</span>
                    <span className="label">×{formatNumber(e.multiplier, 1)} ⇒</span>
                    <span className="big">¥{formatNumber(e.adjusted_amount, 2)}</span>
                  </div>
                </div>
                <div className="card-actions">
                  <button
                    className="btn btn-primary"
                    onClick={() => doneMut.mutate(e.id)}
                    disabled={doneMut.isPending}
                  >
                    标记已执行
                  </button>
                  <button
                    className="btn"
                    onClick={() => skipMut.mutate(e.id)}
                    disabled={skipMut.isPending}
                  >
                    跳过本期
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* 所有计划 */}
      <section className="plans-section">
        <h3>所有计划 ({plans.data?.length ?? 0})</h3>
        {plans.data && plans.data.length === 0 ? (
          <p className="empty">还没有定投计划。点击右上角"新建定投"开始。</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>指数</th>
                <th>频率</th>
                <th>触发日</th>
                <th>金额</th>
                <th>起始</th>
                <th>状态</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {(plans.data ?? []).map((p) => (
                <tr key={p.id}>
                  <td>
                    <Link to={`/indices/${encodeURIComponent(p.index_code)}`}>
                      {p.index_name}
                    </Link>
                    <div className="cell-code">{p.index_code}</div>
                  </td>
                  <td>{FREQ_LABEL[p.frequency]}</td>
                  <td>
                    {p.frequency === "MONTHLY"
                      ? `每月 ${p.day_of_period} 日`
                      : `周${"一二三四五六日".charAt(p.day_of_period - 1)}`}
                  </td>
                  <td>¥{formatNumber(p.amount, 2)}</td>
                  <td>{p.start_date}</td>
                  <td>{p.enabled ? "启用" : "停用"}</td>
                  <td>
                    <button
                      className="btn"
                      onClick={() => {
                        setEditing(p);
                        setEditorOpen(true);
                      }}
                    >
                      编辑
                    </button>
                    <button
                      className="btn"
                      onClick={() => {
                        if (confirm(`删除"${p.index_name}"定投计划？`)) {
                          delMut.mutate(p.id);
                        }
                      }}
                    >
                      删除
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <DCAPlanEditor
        open={editorOpen}
        initial={editing}
        onClose={() => setEditorOpen(false)}
      />
    </div>
  );
}
