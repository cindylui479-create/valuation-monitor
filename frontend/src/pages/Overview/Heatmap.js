import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { Link } from "react-router-dom";
import { formatTemperature, formatPercent } from "@/utils/decimal";
import { isPriceFallback, temperatureColor, tierLabel } from "@/utils/temperature";
export default function Heatmap({ indices }) {
    return (_jsx("div", { className: "heatmap", children: indices.map((idx) => {
            const pf = isPriceFallback(idx.temperature_source);
            return (_jsxs(Link, { to: `/indices/${encodeURIComponent(idx.code)}`, className: "heat-cell", style: { backgroundColor: temperatureColor(idx.temperature) }, title: pf
                    ? `${idx.name} · ${tierLabel(idx.tier)} · 温度来自价格自比（PE 历史不足）`
                    : `${idx.name} · ${tierLabel(idx.tier)} · PE分位 ${formatPercent(idx.pe_percentile_10y)}`, children: [_jsxs("div", { className: "cell-name", children: [idx.name, pf && _jsx("span", { style: { marginLeft: 4 }, children: "\u26A0" })] }), _jsx("div", { className: "cell-temp", children: formatTemperature(idx.temperature) }), _jsx("div", { className: "cell-tier", children: tierLabel(idx.tier) }), idx.data_window_note && (_jsx("div", { className: "cell-note", children: idx.data_window_note }))] }, idx.code));
        }) }));
}
