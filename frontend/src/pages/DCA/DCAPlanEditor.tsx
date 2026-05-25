import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createDCAPlan, updateDCAPlan, type DCAPlanCreate } from "@/api/dca";
import { fetchIndicesList } from "@/api/indicesList";
import type { DCAPlanDTO } from "@/types/api";

interface Props {
  open: boolean;
  initial?: DCAPlanDTO | null;
  presetIndexCode?: string;
  onClose: () => void;
}

const FREQ_LABEL = {
  WEEKLY: "每周",
  BIWEEKLY: "每两周",
  MONTHLY: "每月",
} as const;

export default function DCAPlanEditor({ open, initial, presetIndexCode, onClose }: Props) {
  const qc = useQueryClient();
  const { data: indices } = useQuery({
    queryKey: ["indices-list"],
    queryFn: fetchIndicesList,
    enabled: open,
  });

  const [form, setForm] = useState<DCAPlanCreate>({
    index_code: "",
    fund_code: null,
    amount: "2000",
    frequency: "MONTHLY",
    day_of_period: 10,
    start_date: new Date().toISOString().slice(0, 10),
    enabled: true,
  });
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    if (initial) {
      setForm({
        index_code: initial.index_code,
        fund_code: initial.fund_code,
        amount: initial.amount,
        frequency: initial.frequency,
        day_of_period: initial.day_of_period,
        start_date: initial.start_date,
        enabled: initial.enabled,
      });
    } else if (presetIndexCode) {
      setForm((f) => ({ ...f, index_code: presetIndexCode }));
    }
  }, [open, initial, presetIndexCode]);

  const saveMut = useMutation({
    mutationFn: async () => {
      if (initial) {
        return updateDCAPlan(initial.id, {
          amount: form.amount,
          frequency: form.frequency,
          day_of_period: form.day_of_period,
          enabled: form.enabled,
          fund_code: form.fund_code,
        });
      }
      return createDCAPlan(form);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["dca-plans"] });
      qc.invalidateQueries({ queryKey: ["dca-upcoming"] });
      onClose();
    },
    onError: (e: Error) => setError(e.message),
  });

  if (!open) return null;

  const isWeekly = form.frequency === "WEEKLY" || form.frequency === "BIWEEKLY";

  return (
    <div className="dialog-backdrop" onClick={onClose}>
      <div className="dialog" onClick={(e) => e.stopPropagation()}>
        <h3>{initial ? "编辑定投计划" : "新建定投计划"}</h3>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            setError(null);
            saveMut.mutate();
          }}
        >
          <label className="field">
            <span>指数</span>
            <select
              value={form.index_code}
              disabled={!!initial}
              onChange={(e) => setForm({ ...form, index_code: e.target.value })}
              required
            >
              <option value="">— 选择 —</option>
              {(indices ?? []).map((i) => (
                <option key={i.code} value={i.code}>
                  [{i.market}] {i.name} ({i.code})
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>基础金额</span>
            <input
              type="number"
              min={1}
              step="0.01"
              value={form.amount}
              onChange={(e) => setForm({ ...form, amount: e.target.value })}
              required
            />
          </label>
          <label className="field">
            <span>频率</span>
            <select
              value={form.frequency}
              onChange={(e) =>
                setForm({ ...form, frequency: e.target.value as DCAPlanCreate["frequency"] })
              }
            >
              {Object.entries(FREQ_LABEL).map(([k, v]) => (
                <option key={k} value={k}>{v}</option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>{isWeekly ? "周几（1-7=周一-周日）" : "每月日（1-28）"}</span>
            <input
              type="number"
              min={1}
              max={isWeekly ? 7 : 28}
              value={form.day_of_period}
              onChange={(e) => setForm({ ...form, day_of_period: Number(e.target.value) })}
              required
            />
          </label>
          <label className="field">
            <span>起始日</span>
            <input
              type="date"
              value={form.start_date}
              disabled={!!initial}
              onChange={(e) => setForm({ ...form, start_date: e.target.value })}
              required
            />
          </label>
          <label className="field">
            <span>启用</span>
            <input
              type="checkbox"
              checked={form.enabled}
              onChange={(e) => setForm({ ...form, enabled: e.target.checked })}
            />
          </label>

          {error && <p className="error-msg">{error}</p>}

          <div className="dialog-actions">
            <button type="button" className="btn" onClick={onClose}>取消</button>
            <button type="submit" className="btn btn-primary" disabled={saveMut.isPending}>
              {saveMut.isPending ? "保存中…" : "保存"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
