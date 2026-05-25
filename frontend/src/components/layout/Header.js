import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { NavLink } from "react-router-dom";
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
    const notifLabel = notif.permission === "denied" ? "🔕 通知已拒绝"
        : notif.enabled ? "🔔 通知开"
            : "🔕 通知关";
    const notifColor = notif.permission === "denied" ? "#9ca3af"
        : notif.enabled ? "#15803d" : "#6b7280";
    return (_jsxs("header", { className: "header", children: [_jsx("div", { className: "brand", children: "\u4F30\u503C\u76D1\u6D4B" }), _jsx("nav", { className: "nav", children: NAV.map((item) => (_jsx(NavLink, { to: item.to, end: item.to === "/", className: ({ isActive }) => "nav-link" + (isActive ? " active" : ""), children: item.label }, item.to))) }), _jsx("button", { onClick: notif.toggle, disabled: notif.permission === "denied", title: notif.permission === "denied"
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
