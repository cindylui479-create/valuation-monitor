import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import {
  deleteOverride,
  fetchOverride,
  putOverride,
} from "@/api/overrides";

interface Props {
  open: boolean;
  indexCode: string;
  onClose: () => void;
}

export default function ThresholdOverrideDialog({ open, indexCode, onClose }: Props) {
  const qc = useQueryClient();
  const { data } = useQuery({
    queryKey: ["override", indexCode],
    queryFn: () => fetchOverride(indexCode),
    enabled: open && !!indexCode,
  });

  const [b, setB] = useState({
    extreme_low_upper: "0.10",
    low_upper: "0.30",
    high_lower: "0.70",
    extreme_high_lower: "0.90",
  });
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (data) {
      setB({
        extreme_low_upper: data.boundaries.extreme_low_upper,
        low_upper: data.boundaries.low_upper,
        high_lower: data.boundaries.high_lower,
        extreme_high_lower: data.boundaries.extreme_high_lower,
      });
    }
  }, [data]);

  const saveMut = useMutation({
    mutationFn: () => putOverride(indexCode, b),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["override", indexCode] });
      qc.invalidateQueries({ queryKey: ["overview"] });
      qc.invalidateQueries({ queryKey: ["index-detail", indexCode] });
      onClose();
    },
    onError: (e: Error) => setError(e.message),
  });

  const resetMut = useMutation({
    mutationFn: () => deleteOverride(indexCode),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["override", indexCode] });
      qc.invalidateQueries({ queryKey: ["overview"] });
      onClose();
    },
    onError: (e: Error) => setError(e.message),
  });

  if (!open) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    saveMut.mutate();
  };

  return (
    <div className="dialog-backdrop" onClick={onClose}>
      <div className="dialog" onClick={(e) => e.stopPropagation()}>
        <h3>个性化阈值 — {indexCode}</h3>
        <p className="hint">
          调整后，定投联动规则与信号判定将随之同步（SRS D6 方案 A）。
          {data?.is_default ? "当前使用默认边界。" : "当前已有自定义边界。"}
        </p>
        <form onSubmit={handleSubmit}>
          {([
            ["extreme_low_upper", "极度低估上限"],
            ["low_upper", "低估上限"],
            ["high_lower", "高估下限"],
            ["extreme_high_lower", "极度高估下限"],
          ] as const).map(([k, label]) => (
            <label key={k} className="field">
              <span>{label}</span>
              <input
                type="number"
                step="0.01"
                min={0}
                max={1}
                value={b[k]}
                onChange={(e) => setB({ ...b, [k]: e.target.value })}
                required
              />
            </label>
          ))}
          {error && <p className="error-msg">{error}</p>}
          <div className="dialog-actions">
            <button type="button" className="btn" onClick={onClose}>
              取消
            </button>
            {!data?.is_default && (
              <button
                type="button"
                className="btn"
                onClick={() => resetMut.mutate()}
                disabled={resetMut.isPending}
              >
                重置为默认
              </button>
            )}
            <button
              type="submit"
              className="btn btn-primary"
              disabled={saveMut.isPending}
            >
              {saveMut.isPending ? "保存中…" : "保存"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
