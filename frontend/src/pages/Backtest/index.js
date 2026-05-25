import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { runBacktest } from "@/api/backtest";
import { fetchIndicesList } from "@/api/indicesList";
import { formatNumber, formatPercent } from "@/utils/decimal";
import NAVChart from "./NAVChart";
const STRATEGY_LABEL = {
    threshold: "阈值策略",
    dca: "定投策略",
    buy_hold: "买入持有（基准）",
};
function StrategyKPI({ s }) {
    return (_jsxs("div", { className: "strategy-kpi", children: [_jsx("h4", { children: STRATEGY_LABEL[s.name] }), _jsxs("div", { className: "kpi-row inline", children: [_jsxs("div", { className: "kpi", children: [_jsx("div", { className: "label", children: "\u5E74\u5316" }), _jsx("div", { className: "value", children: formatPercent(s.annualized_return, 2) })] }), _jsxs("div", { className: "kpi", children: [_jsx("div", { className: "label", children: "\u6700\u5927\u56DE\u64A4" }), _jsx("div", { className: "value drawdown", children: formatPercent(s.max_drawdown, 2) })] }), _jsxs("div", { className: "kpi", children: [_jsx("div", { className: "label", children: "\u6700\u7EC8 NAV" }), _jsx("div", { className: "value", children: formatNumber(s.final_nav, 3) })] }), _jsxs("div", { className: "kpi", children: [_jsx("div", { className: "label", children: "\u4EA4\u6613\u6B21\u6570" }), _jsx("div", { className: "value", children: s.trade_count })] })] })] }));
}
export default function Backtest() {
    const { data: indices } = useQuery({
        queryKey: ["indices-list"],
        queryFn: fetchIndicesList,
    });
    const [form, setForm] = useState({
        index_code: "",
        buy_percentile_below: "0.20",
        sell_percentile_above: "0.80",
        start_date: "",
        end_date: "",
        window: "10y",
        fee_rate: "0",
        slippage_rate: "0",
        reinvest_dividend: false,
        include_dca: true,
    });
    const [result, setResult] = useState(null);
    const [error, setError] = useState(null);
    const runMut = useMutation({
        mutationFn: () => runBacktest({
            index_code: form.index_code,
            buy_percentile_below: form.buy_percentile_below,
            sell_percentile_above: form.sell_percentile_above,
            start_date: form.start_date || undefined,
            end_date: form.end_date || undefined,
            window: form.window,
            fee_rate: form.fee_rate || "0",
            slippage_rate: form.slippage_rate || "0",
            reinvest_dividend: form.reinvest_dividend,
            include_dca: form.include_dca,
        }),
        onSuccess: (r) => { setResult(r); setError(null); },
        onError: (e) => { setError(e.message); setResult(null); },
    });
    return (_jsxs("div", { className: "backtest-page", children: [_jsx("div", { className: "page-header", children: _jsx("h2", { children: "\u56DE\u6D4B" }) }), _jsxs("p", { className: "hint", children: ["\u4E09\u7B56\u7565\u5E76\u884C\uFF1A", _jsx("strong", { children: "\u9608\u503C\u7B56\u7565" }), "\uFF08PE \u5206\u4F4D < \u4E70\u5165 / > \u5356\u51FA\uFF09+ ", _jsx("strong", { children: "\u5B9A\u6295\u7B56\u7565" }), "\uFF08\u6BCF\u6708\u6309 multiplier \u52A0\u4ED3\uFF09+ ", _jsx("strong", { children: "\u4E70\u5165\u6301\u6709" }), "\uFF08\u57FA\u51C6\uFF09\u3002", _jsx("br", {}), "\u53EF\u9009\u624B\u7EED\u8D39 / \u6ED1\u70B9 / \u5206\u7EA2\u518D\u6295\u8D44\uFF1B\u5B9A\u6295\u7B56\u7565\u7684 multiplier \u81EA\u52A8\u9075\u5FAA\u8BE5\u6307\u6570\u5F53\u524D\u4E2A\u6027\u5316\u9608\u503C\uFF08SRS D6\uFF09\u3002"] }), _jsxs("form", { className: "bt-form", onSubmit: (e) => { e.preventDefault(); runMut.mutate(); }, children: [_jsxs("label", { className: "field", children: [_jsx("span", { children: "\u6307\u6570" }), _jsxs("select", { value: form.index_code, onChange: (e) => setForm({ ...form, index_code: e.target.value }), required: true, children: [_jsx("option", { value: "", children: "\u2014 \u9009\u62E9 \u2014" }), (indices ?? []).map((i) => (_jsxs("option", { value: i.code, children: ["[", i.market, "] ", i.name, " (", i.code, ")"] }, i.code)))] })] }), _jsxs("label", { className: "field", children: [_jsx("span", { children: "\u4E70\u5165\u9608\u503C\uFF08PE <\uFF09" }), _jsx("input", { type: "number", step: "0.01", min: 0, max: 1, value: form.buy_percentile_below, onChange: (e) => setForm({ ...form, buy_percentile_below: e.target.value }), required: true })] }), _jsxs("label", { className: "field", children: [_jsx("span", { children: "\u5356\u51FA\u9608\u503C\uFF08PE >\uFF09" }), _jsx("input", { type: "number", step: "0.01", min: 0, max: 1, value: form.sell_percentile_above, onChange: (e) => setForm({ ...form, sell_percentile_above: e.target.value }), required: true })] }), _jsxs("label", { className: "field", children: [_jsx("span", { children: "\u8D77\u59CB\u65E5" }), _jsx("input", { type: "date", value: form.start_date, onChange: (e) => setForm({ ...form, start_date: e.target.value }) })] }), _jsxs("label", { className: "field", children: [_jsx("span", { children: "\u7ED3\u675F\u65E5" }), _jsx("input", { type: "date", value: form.end_date, onChange: (e) => setForm({ ...form, end_date: e.target.value }) })] }), _jsxs("label", { className: "field", children: [_jsx("span", { children: "\u7A97\u53E3" }), _jsxs("select", { value: form.window, onChange: (e) => setForm({ ...form, window: e.target.value }), children: [_jsx("option", { value: "5y", children: "\u8FD1 5 \u5E74" }), _jsx("option", { value: "10y", children: "\u8FD1 10 \u5E74" }), _jsx("option", { value: "all", children: "\u5168\u5386\u53F2" })] })] }), _jsxs("label", { className: "field", children: [_jsx("span", { children: "\u624B\u7EED\u8D39\u7387 (\u53CC\u5411)" }), _jsx("input", { type: "number", step: "0.0001", min: 0, max: 0.05, value: form.fee_rate, onChange: (e) => setForm({ ...form, fee_rate: e.target.value }), placeholder: "0.0003" })] }), _jsxs("label", { className: "field", children: [_jsx("span", { children: "\u6ED1\u70B9\u7387" }), _jsx("input", { type: "number", step: "0.0001", min: 0, max: 0.05, value: form.slippage_rate, onChange: (e) => setForm({ ...form, slippage_rate: e.target.value }), placeholder: "0.0005" })] }), _jsxs("label", { className: "field horizontal", children: [_jsx("input", { type: "checkbox", checked: form.reinvest_dividend, onChange: (e) => setForm({ ...form, reinvest_dividend: e.target.checked }) }), _jsxs("span", { children: ["\u5206\u7EA2\u518D\u6295\u8D44", _jsx("br", {}), _jsx("small", { style: { color: "#9ca3af" }, children: "A \u80A1\u80A1\u606F\u7387\u5386\u53F2\u4EC5\u6700\u8FD1 20 \u5929" })] })] }), _jsxs("label", { className: "field horizontal", children: [_jsx("input", { type: "checkbox", checked: form.include_dca, onChange: (e) => setForm({ ...form, include_dca: e.target.checked }) }), _jsx("span", { children: "\u5305\u542B\u5B9A\u6295\u7B56\u7565" })] }), _jsx("button", { type: "submit", className: "btn btn-primary", disabled: runMut.isPending, children: runMut.isPending ? "回测中…" : "运行" })] }), error && _jsx("div", { className: "state error", children: error }), result && (_jsxs("section", { className: "bt-result", children: [_jsxs("h3", { children: ["\u7ED3\u679C \u2014 ", result.index_name, " (", result.index_code, ")"] }), _jsxs("p", { className: "hint", style: { background: "transparent", border: "none", padding: 0 }, children: ["\u533A\u95F4\uFF1A", result.start_date, " \u2192 ", result.end_date, result.fee_rate !== "0" && ` · 手续费 ${(parseFloat(result.fee_rate) * 100).toFixed(2)}%`, result.slippage_rate !== "0" && ` · 滑点 ${(parseFloat(result.slippage_rate) * 100).toFixed(2)}%`, result.reinvest_dividend && " · 分红再投资"] }), _jsx(NAVChart, { strategies: [result.threshold, result.dca, result.buy_hold] }), _jsxs("div", { className: "strategy-grid", children: [_jsx(StrategyKPI, { s: result.threshold }), result.dca && _jsx(StrategyKPI, { s: result.dca }), _jsx(StrategyKPI, { s: result.buy_hold })] }), _jsxs("h4", { children: ["\u9608\u503C\u7B56\u7565\u4EA4\u6613\u660E\u7EC6 (", result.threshold.trade_count, ")"] }), result.threshold.trades.length === 0 ? (_jsx("p", { className: "empty", children: "\u65E0\u4EA4\u6613\uFF08\u7B56\u7565\u9608\u503C\u672A\u89E6\u53D1\uFF09" })) : (_jsxs("table", { className: "table", children: [_jsx("thead", { children: _jsxs("tr", { children: [_jsx("th", { children: "\u65E5\u671F" }), _jsx("th", { children: "\u52A8\u4F5C" }), _jsx("th", { children: "\u4EF7\u683C" }), _jsx("th", { children: "PE \u5206\u4F4D" })] }) }), _jsx("tbody", { children: result.threshold.trades.map((t, i) => (_jsxs("tr", { children: [_jsx("td", { children: t.date }), _jsx("td", { children: _jsx("span", { className: "tier-badge", style: { backgroundColor: t.action === "BUY" ? "#22c55e" : "#f87171" }, children: t.action === "BUY" ? "买入" : "卖出" }) }), _jsx("td", { children: formatNumber(t.price, 2) }), _jsx("td", { children: t.pe_percentile ? formatPercent(t.pe_percentile, 1) : "—" })] }, i))) })] })), result.dca && result.dca.trades.length > 0 && (_jsxs(_Fragment, { children: [_jsxs("h4", { children: ["\u5B9A\u6295\u7B56\u7565\u4EA4\u6613\u660E\u7EC6 (", result.dca.trade_count, ")"] }), _jsxs("details", { children: [_jsxs("summary", { children: ["\u5C55\u5F00\uFF08\u5171 ", result.dca.trades.length, " \u7B14\uFF09"] }), _jsxs("table", { className: "table", children: [_jsx("thead", { children: _jsxs("tr", { children: [_jsx("th", { children: "\u65E5\u671F" }), _jsx("th", { children: "\u00D7multiplier" }), _jsx("th", { children: "\u4EF7\u683C" }), _jsx("th", { children: "\u91D1\u989D" }), _jsx("th", { children: "PE \u5206\u4F4D" })] }) }), _jsx("tbody", { children: result.dca.trades.map((t, i) => (_jsxs("tr", { children: [_jsx("td", { children: t.date }), _jsxs("td", { children: ["\u00D7", formatNumber(t.multiplier ?? "1", 2)] }), _jsx("td", { children: formatNumber(t.price, 2) }), _jsx("td", { children: formatNumber(t.amount, 4) }), _jsx("td", { children: t.pe_percentile ? formatPercent(t.pe_percentile, 1) : "—" })] }, i))) })] })] })] }))] }))] }));
}
