import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { NavLink } from "react-router-dom";
const NAV = [
    { to: "/", label: "总览" },
    { to: "/watchlist", label: "自选" },
    { to: "/signals", label: "信号" },
    { to: "/dca", label: "定投" },
    { to: "/backtest", label: "回测" },
    { to: "/settings", label: "设置" },
];
export default function Header() {
    return (_jsxs("header", { className: "header", children: [_jsx("div", { className: "brand", children: "\u4F30\u503C\u76D1\u6D4B" }), _jsx("nav", { className: "nav", children: NAV.map((item) => (_jsx(NavLink, { to: item.to, end: item.to === "/", className: ({ isActive }) => "nav-link" + (isActive ? " active" : ""), children: item.label }, item.to))) })] }));
}
