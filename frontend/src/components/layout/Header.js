import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
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
    const hasPipelineFailure = (health.data?.pipeline ?? []).some((p) => p.status === "FAILED" || p.status === "PARTIAL");
    const notifLabel = notif.permission === "denied" ? "🔕 通知已拒绝"
        : notif.enabled ? "🔔 通知开"
            : "🔕 通知关";
    const notifColor = notif.permission === "denied" ? "#9ca3af"
        : notif.enabled ? "#15803d" : "#6b7280";
    return (_jsxs("header", { className: "header", children: [_jsx("div", { className: "brand", children: "\u4F30\u503C\u76D1\u6D4B" }), _jsx("nav", { className: "nav", children: NAV.map((item) => (_jsxs(NavLink, { to: item.to, end: item.to === "/", className: ({ isActive }) => "nav-link" + (isActive ? " active" : ""), style: { position: "relative" }, children: [item.label, item.to === "/settings" && hasPipelineFailure && (_jsx("span", { title: "\u6570\u636E\u540C\u6B65\u51FA\u73B0\u5931\u8D25\uFF0C\u67E5\u770B \u8BBE\u7F6E \u2192 \u8FD0\u884C\u5386\u53F2", style: {
                                position: "absolute", top: 0, right: -8,
                                width: 8, height: 8, borderRadius: "50%",
                                background: "#dc2626",
                            } }))] }, item.to))) }), _jsx("button", { onClick: notif.toggle, disabled: notif.permission === "denied", title: notif.permission === "denied"
                    ? "已拒绝。要打开请到浏览器设置 → 网站权限 → 通知 重置。"
                    : notif.enabled
                        ? "点击关闭浏览器通知"
                        : "点击启用浏览器通知（跨档位 / 极度低估时弹提示）", style: {
                    marginLeft: "auto",
                    background: "transparent", border: "1px solid #e5e7eb",
                    color: notifColor, padding: "4px 10px",
                    borderRadius: 4, fontSize: 12, cursor: notif.permission === "denied" ? "default" : "pointer",
                }, children: notifLabel })] }));
}
