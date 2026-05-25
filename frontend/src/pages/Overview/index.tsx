import { useQuery } from "@tanstack/react-query";
import { useState, useMemo } from "react";
import { fetchOverview } from "@/api/overview";
import { usePeSource } from "@/hooks/usePeSource";
import MarketColumn from "./MarketColumn";
import type { OverviewMarket } from "@/types/api";

type ViewMode = "heatmap" | "table";
type TierFilter = "all" | "extreme_low" | "low" | "fair" | "high" | "extreme_high" | "snapshot";

const FILTER_LABEL: Record<TierFilter, string> = {
  all: "全部",
  extreme_low: "极度低估",
  low: "低估",
  fair: "合理",
  high: "高估",
  extreme_high: "极度高估",
  snapshot: "仅快照",
};

const TIER_OF_FILTER: Record<Exclude<TierFilter, "all" | "snapshot">, string> = {
  extreme_low: "极度低估",
  low: "低估",
  fair: "合理",
  high: "高估",
  extreme_high: "极度高估",
};

export default function Overview() {
  const [view, setView] = useState<ViewMode>("heatmap");
  const [filter, setFilter] = useState<TierFilter>("all");
  const peSource = usePeSource();

  const { data, isLoading, isError, error, refetch, isFetching } = useQuery({
    queryKey: ["overview", peSource],
    queryFn: () => fetchOverview(peSource),
  });

  const filteredMarkets: OverviewMarket[] = useMemo(() => {
    if (!data) return [];
    if (filter === "all") return data.markets;
    return data.markets.map((m) => ({
      ...m,
      indices: m.indices.filter((i) => {
        if (filter === "snapshot") return i.temperature == null;
        return i.tier === TIER_OF_FILTER[filter];
      }),
    }));
  }, [data, filter]);

  if (isLoading) {
    return <div className="state">加载中…</div>;
  }

  if (isError) {
    return (
      <div className="state error">
        <p>加载失败：{(error as Error).message}</p>
        <button onClick={() => refetch()}>重试</button>
      </div>
    );
  }

  if (!data || data.markets.length === 0) {
    return (
      <div className="state">
        <p>暂无数据。请先初始化指数池与历史数据：</p>
        <pre>
          {`cd backend
alembic upgrade head
python -m scripts.seed_universe
python -m scripts.init_history --market A --years 10`}
        </pre>
      </div>
    );
  }

  return (
    <div className="overview">
      <div className="overview-header">
        <div className="as-of">
          {data.as_of ? `数据日期：${data.as_of}` : "暂无数据"}
          {isFetching && <span className="dot"> 刷新中…</span>}
        </div>
        <div className="view-toggle">
          <button
            className={view === "heatmap" ? "active" : ""}
            onClick={() => setView("heatmap")}
          >
            热力图
          </button>
          <button
            className={view === "table" ? "active" : ""}
            onClick={() => setView("table")}
          >
            表格
          </button>
        </div>
      </div>

      <div className="tier-filter">
        {(Object.keys(FILTER_LABEL) as TierFilter[]).map((f) => (
          <button
            key={f}
            className={"chip" + (filter === f ? " active" : "")}
            onClick={() => setFilter(f)}
          >
            {FILTER_LABEL[f]}
          </button>
        ))}
      </div>

      <div className="market-grid">
        {filteredMarkets.map((m) => (
          <MarketColumn key={m.market} market={m} view={view} />
        ))}
      </div>
    </div>
  );
}
