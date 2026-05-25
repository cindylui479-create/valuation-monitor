import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useQuery } from "@tanstack/react-query";
import { useState, useMemo } from "react";
import { fetchOverview } from "@/api/overview";
import { usePeSource } from "@/hooks/usePeSource";
import MarketColumn from "./MarketColumn";
import TodayDigest from "./TodayDigest";
const FILTER_LABEL = {
    all: "全部",
    extreme_low: "极度低估",
    low: "低估",
    fair: "合理",
    high: "高估",
    extreme_high: "极度高估",
    snapshot: "仅快照",
};
const TIER_OF_FILTER = {
    extreme_low: "极度低估",
    low: "低估",
    fair: "合理",
    high: "高估",
    extreme_high: "极度高估",
};
export default function Overview() {
    const [view, setView] = useState("heatmap");
    const [filter, setFilter] = useState("all");
    const peSource = usePeSource();
    const { data, isLoading, isError, error, refetch, isFetching } = useQuery({
        queryKey: ["overview", peSource],
        queryFn: () => fetchOverview(peSource),
    });
    const filteredMarkets = useMemo(() => {
        if (!data)
            return [];
        if (filter === "all")
            return data.markets;
        return data.markets.map((m) => ({
            ...m,
            indices: m.indices.filter((i) => {
                if (filter === "snapshot")
                    return i.temperature == null;
                return i.tier === TIER_OF_FILTER[filter];
            }),
        }));
    }, [data, filter]);
    if (isLoading) {
        return _jsx("div", { className: "state", children: "\u52A0\u8F7D\u4E2D\u2026" });
    }
    if (isError) {
        return (_jsxs("div", { className: "state error", children: [_jsxs("p", { children: ["\u52A0\u8F7D\u5931\u8D25\uFF1A", error.message] }), _jsx("button", { onClick: () => refetch(), children: "\u91CD\u8BD5" })] }));
    }
    if (!data || data.markets.length === 0) {
        return (_jsxs("div", { className: "state", children: [_jsx("p", { children: "\u6682\u65E0\u6570\u636E\u3002\u8BF7\u5148\u521D\u59CB\u5316\u6307\u6570\u6C60\u4E0E\u5386\u53F2\u6570\u636E\uFF1A" }), _jsx("pre", { children: `cd backend
alembic upgrade head
python -m scripts.seed_universe
python -m scripts.init_history --market A --years 10` })] }));
    }
    return (_jsxs("div", { className: "overview", children: [_jsx(TodayDigest, {}), _jsxs("div", { className: "overview-header", children: [_jsxs("div", { className: "as-of", children: [data.as_of ? `数据日期：${data.as_of}` : "暂无数据", isFetching && _jsx("span", { className: "dot", children: " \u5237\u65B0\u4E2D\u2026" })] }), _jsxs("div", { className: "view-toggle", children: [_jsx("button", { className: view === "heatmap" ? "active" : "", onClick: () => setView("heatmap"), children: "\u70ED\u529B\u56FE" }), _jsx("button", { className: view === "table" ? "active" : "", onClick: () => setView("table"), children: "\u8868\u683C" })] })] }), _jsx("div", { className: "tier-filter", children: Object.keys(FILTER_LABEL).map((f) => (_jsx("button", { className: "chip" + (filter === f ? " active" : ""), onClick: () => setFilter(f), children: FILTER_LABEL[f] }, f))) }), _jsx("div", { className: "market-grid", children: filteredMarkets.map((m) => (_jsx(MarketColumn, { market: m, view: view }, m.market))) })] }));
}
