/**
 * OPS-2：数据陈旧度横幅。
 *
 * 背景：调度器活在 uvicorn 进程里，服务停了就没人同步数据，
 * 而停摆只能靠用户偶然发现（2026-06 实际发生过 — 停了一周才察觉）。
 * 这个横幅让"打开页面"即等于"巡检"。
 *
 * 阈值（自然日，容忍周末/小长假）：
 *   ≥ 4 天 → 黄条提醒（可能是假期，也可能是停摆）
 *   ≥ 7 天 → 红条告警（基本可断定停摆）
 */
interface Props {
  asOf: string | null;
}

export default function StalenessBanner({ asOf }: Props) {
  if (!asOf) return null;
  const asOfDate = new Date(asOf + "T00:00:00");
  const staleDays = Math.floor((Date.now() - asOfDate.getTime()) / 86_400_000);
  if (staleDays < 4) return null;

  const severe = staleDays >= 7;
  return (
    <div style={{
      background: severe ? "#fee2e2" : "#fef3c7",
      color: severe ? "#991b1b" : "#92400e",
      border: `1px solid ${severe ? "#fca5a5" : "#fde68a"}`,
      padding: "10px 14px", borderRadius: 4, marginBottom: 12,
      fontSize: 13,
    }}>
      {severe ? "🛑" : "⚠"} <strong>数据已 {staleDays} 天未更新</strong>（最新：{asOf}）。
      {severe
        ? "服务很可能已停摆。检查：systemctl --user status valuation-monitor；日志：journalctl --user -u valuation-monitor -n 50。"
        : "可能是长假休市；若非假期，请检查后台服务是否在运行（systemctl --user status valuation-monitor）。"}
    </div>
  );
}
