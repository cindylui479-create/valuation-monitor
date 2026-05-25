import type { OverviewMarket } from "@/types/api";
import Heatmap from "./Heatmap";
import TableView from "./TableView";

const MARKET_LABEL: Record<string, string> = {
  A: "A 股",
  HK: "港股",
  US: "美股",
};

interface Props {
  market: OverviewMarket;
  view: "heatmap" | "table";
}

export default function MarketColumn({ market, view }: Props) {
  // M3 R7：若该市场所有指数都无 temperature，则该市场处于"快照"模式
  const snapshotOnly =
    market.indices.length > 0 && market.indices.every((i) => i.temperature == null);

  return (
    <section className="market-col">
      <header>
        <h2>{MARKET_LABEL[market.market] ?? market.market}</h2>
        <span className="currency">({market.currency})</span>
        {snapshotOnly && (
          <span
            className="snapshot-tag"
            title="该市场目前仅有当日 PE 快照，无历史分位/温度（M3 yfinance；M4 后接 Tushare 补全）"
          >
            📷 快照
          </span>
        )}
      </header>
      {market.indices.length === 0 ? (
        <p className="empty">暂无指数</p>
      ) : view === "heatmap" ? (
        <Heatmap indices={market.indices} />
      ) : (
        <TableView indices={market.indices} />
      )}
    </section>
  );
}
