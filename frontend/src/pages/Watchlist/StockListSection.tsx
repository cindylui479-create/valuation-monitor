import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { useState } from "react";
import { addStock, listStocks, removeStock } from "@/api/stocks";
import { temperatureColor, tierLabel } from "@/utils/temperature";

const ANCHOR_LABEL: Record<string, string> = {
  PE: "PE-TTM",
  PB: "市净率",
  PS: "市销率",
  PE_REVERSE: "PE 倒置",
  DIV_YIELD: "股息率倒置",
};

export default function StockListSection() {
  const qc = useQueryClient();
  const [code, setCode] = useState("");
  const [err, setErr] = useState<string | null>(null);

  const list = useQuery({
    queryKey: ["stocks"],
    queryFn: listStocks,
  });

  const addMut = useMutation({
    mutationFn: (c: string) => addStock(c),
    onSuccess: () => {
      setCode("");
      setErr(null);
      qc.invalidateQueries({ queryKey: ["stocks"] });
    },
    onError: (e: Error) => setErr(e.message),
  });

  const removeMut = useMutation({
    mutationFn: (c: string) => removeStock(c),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["stocks"] }),
  });

  const items = list.data?.items ?? [];

  return (
    <div>
      <section className="settings-block">
        <h3>添加个股</h3>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <input
            placeholder="股票代码（如 600519.SH 或 000001）"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            style={{ flex: 1, maxWidth: 280, padding: "4px 8px" }}
            disabled={addMut.isPending}
            onKeyDown={(e) => {
              if (e.key === "Enter" && code.trim() && !addMut.isPending) {
                addMut.mutate(code.trim());
              }
            }}
          />
          <button
            className="btn btn-primary"
            onClick={() => addMut.mutate(code.trim())}
            disabled={!code.trim() || addMut.isPending}
          >
            {addMut.isPending ? "拉取中…(约 5–15 秒)" : "添加"}
          </button>
        </div>
        {err && <p style={{ color: "#b91c1c", fontSize: 12 }}>错误：{err}</p>}
        <p className="hint">
          首次添加会从 Tushare 拉上市以来全历史 PE/PB/PS（约 5–15 秒）。
          行业自动从 Tushare 取，估值锚按行业自动选（银行/地产 → PB；周期 → PE 倒置；计算机/传媒 → PS；其他 → PE）。
        </p>
      </section>

      <section className="settings-block">
        <h3>自选个股（{items.length}）</h3>
        {list.isLoading ? (
          <p className="empty">加载中…</p>
        ) : items.length === 0 ? (
          <p className="empty">还没有自选个股。在上方输入代码添加。</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>代码</th>
                <th>名称</th>
                <th>行业</th>
                <th>估值锚</th>
                <th>温度</th>
                <th>档位</th>
                <th>PE</th>
                <th>PB</th>
                <th>PS</th>
                <th>历史</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {items.map((s) => {
                const temp = s.temperature ? parseFloat(s.temperature) : null;
                return (
                  <tr key={s.code}>
                    <td>
                      <Link to={`/stocks/${encodeURIComponent(s.code)}`}>
                        <strong>{s.code}</strong>
                      </Link>
                    </td>
                    <td>{s.name}</td>
                    <td>{s.industry ?? "—"}</td>
                    <td>
                      <span style={{
                        fontSize: 11, padding: "1px 6px",
                        background: "#e0f2fe", color: "#075985",
                        borderRadius: 4,
                      }}>{ANCHOR_LABEL[s.anchor] ?? s.anchor}</span>
                    </td>
                    <td>
                      {temp != null ? (
                        <span style={{
                          background: temperatureColor(temp.toString()),
                          color: "white", padding: "1px 8px",
                          borderRadius: 4, fontSize: 11,
                        }}>
                          {temp.toFixed(1)}
                        </span>
                      ) : "—"}
                    </td>
                    <td>{s.tier ? tierLabel(s.tier) : "—"}</td>
                    <td>{s.pe_ttm ? parseFloat(s.pe_ttm).toFixed(2) : "—"}</td>
                    <td>{s.pb ? parseFloat(s.pb).toFixed(2) : "—"}</td>
                    <td>{s.ps_ttm ? parseFloat(s.ps_ttm).toFixed(2) : "—"}</td>
                    <td>{s.actual_history_years.toFixed(1)}y</td>
                    <td>
                      <button
                        className="btn"
                        onClick={() => {
                          if (confirm(`确认移除 ${s.code} ${s.name}？历史数据会一并删除。`)) {
                            removeMut.mutate(s.code);
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
        )}
      </section>
    </div>
  );
}
