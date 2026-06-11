import { jsxs as _jsxs } from "react/jsx-runtime";
export default function StalenessBanner({ asOf }) {
    if (!asOf)
        return null;
    const asOfDate = new Date(asOf + "T00:00:00");
    const staleDays = Math.floor((Date.now() - asOfDate.getTime()) / 86_400_000);
    if (staleDays < 4)
        return null;
    const severe = staleDays >= 7;
    return (_jsxs("div", { style: {
            background: severe ? "#fee2e2" : "#fef3c7",
            color: severe ? "#991b1b" : "#92400e",
            border: `1px solid ${severe ? "#fca5a5" : "#fde68a"}`,
            padding: "10px 14px", borderRadius: 4, marginBottom: 12,
            fontSize: 13,
        }, children: [severe ? "🛑" : "⚠", " ", _jsxs("strong", { children: ["\u6570\u636E\u5DF2 ", staleDays, " \u5929\u672A\u66F4\u65B0"] }), "\uFF08\u6700\u65B0\uFF1A", asOf, "\uFF09\u3002", severe
                ? "服务很可能已停摆。检查：systemctl --user status valuation-monitor；日志：journalctl --user -u valuation-monitor -n 50。"
                : "可能是长假休市；若非假期，请检查后台服务是否在运行（systemctl --user status valuation-monitor）。"] }));
}
