import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import Heatmap from "./Heatmap";
import TableView from "./TableView";
const MARKET_LABEL = {
    A: "A 股",
    HK: "港股",
    US: "美股",
};
export default function MarketColumn({ market, view }) {
    // M3 R7：若该市场所有指数都无 temperature，则该市场处于"快照"模式
    const snapshotOnly = market.indices.length > 0 && market.indices.every((i) => i.temperature == null);
    return (_jsxs("section", { className: "market-col", children: [_jsxs("header", { children: [_jsx("h2", { children: MARKET_LABEL[market.market] ?? market.market }), _jsxs("span", { className: "currency", children: ["(", market.currency, ")"] }), snapshotOnly && (_jsx("span", { className: "snapshot-tag", title: "\u8BE5\u5E02\u573A\u76EE\u524D\u4EC5\u6709\u5F53\u65E5 PE \u5FEB\u7167\uFF0C\u65E0\u5386\u53F2\u5206\u4F4D/\u6E29\u5EA6\uFF08M3 yfinance\uFF1BM4 \u540E\u63A5 Tushare \u8865\u5168\uFF09", children: "\uD83D\uDCF7 \u5FEB\u7167" }))] }), market.indices.length === 0 ? (_jsx("p", { className: "empty", children: "\u6682\u65E0\u6307\u6570" })) : view === "heatmap" ? (_jsx(Heatmap, { indices: market.indices })) : (_jsx(TableView, { indices: market.indices }))] }));
}
