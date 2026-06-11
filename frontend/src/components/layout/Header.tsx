import { NavLink } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { fetchHealth } from "@/api/health";
import { useNotifications } from "@/hooks/useNotifications";

const NAV = [
  { to: "/", label: "总览" },
  { to: "/watchlist", label: "我的" },
  { to: "/signals", label: "信号" },
  { to: "/dca", label: "定投" },
  { to: "/backtest", label: "回测" },
  { to: "/settings", label: "设置" },
];

export default function Header() {
  const notif = useNotifications();
  // OPS-3：pipeline 失败时在「设置」上挂红点
  const health = useQuery({
    queryKey: ["health-nav"],
    queryFn: fetchHealth,
    refetchInterval: 5 * 60_000,
    staleTime: 60_000,
  });
  const hasPipelineFailure = (health.data?.pipeline ?? []).some(
    (p) => p.status === "FAILED" || p.status === "PARTIAL",
  );
  const notifLabel =
    notif.permission === "denied" ? "🔕 通知已拒绝"
    : notif.enabled ? "🔔 通知开"
    : "🔕 通知关";
  const notifColor =
    notif.permission === "denied" ? "#9ca3af"
    : notif.enabled ? "#15803d" : "#6b7280";

  return (
    <header className="header">
      <div className="brand">估值监测</div>
      <nav className="nav">
        {NAV.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/"}
            className={({ isActive }) => "nav-link" + (isActive ? " active" : "")}
            style={{ position: "relative" }}
          >
            {item.label}
            {item.to === "/settings" && hasPipelineFailure && (
              <span
                title="数据同步出现失败，查看 设置 → 运行历史"
                style={{
                  position: "absolute", top: 0, right: -8,
                  width: 8, height: 8, borderRadius: "50%",
                  background: "#dc2626",
                }}
              />
            )}
          </NavLink>
        ))}
      </nav>
      <button
        onClick={notif.toggle}
        disabled={notif.permission === "denied"}
        title={
          notif.permission === "denied"
            ? "已拒绝。要打开请到浏览器设置 → 网站权限 → 通知 重置。"
            : notif.enabled
            ? "点击关闭浏览器通知"
            : "点击启用浏览器通知（跨档位 / 极度低估时弹提示）"
        }
        style={{
          marginLeft: "auto",
          background: "transparent", border: "1px solid #e5e7eb",
          color: notifColor, padding: "4px 10px",
          borderRadius: 4, fontSize: 12, cursor: notif.permission === "denied" ? "default" : "pointer",
        }}
      >
        {notifLabel}
      </button>
    </header>
  );
}
