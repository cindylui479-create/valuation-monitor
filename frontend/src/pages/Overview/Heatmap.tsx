import { Link } from "react-router-dom";
import type { OverviewIndex } from "@/types/api";
import { formatTemperature, formatPercent } from "@/utils/decimal";
import { isPriceFallback, temperatureColor, tierLabel } from "@/utils/temperature";

interface Props {
  indices: OverviewIndex[];
}

export default function Heatmap({ indices }: Props) {
  return (
    <div className="heatmap">
      {indices.map((idx) => {
        const pf = isPriceFallback(idx.temperature_source);
        return (
          <Link
            key={idx.code}
            to={`/indices/${encodeURIComponent(idx.code)}`}
            className="heat-cell"
            style={{ backgroundColor: temperatureColor(idx.temperature) }}
            title={pf
              ? `${idx.name} · ${tierLabel(idx.tier)} · 温度来自价格自比（PE 历史不足）`
              : `${idx.name} · ${tierLabel(idx.tier)} · PE分位 ${formatPercent(idx.pe_percentile_10y)}`}
          >
            <div className="cell-name">
              {idx.name}
              {pf && <span style={{ marginLeft: 4 }}>⚠</span>}
            </div>
            <div className="cell-temp">{formatTemperature(idx.temperature)}</div>
            <div className="cell-tier">{tierLabel(idx.tier)}</div>
            {idx.data_window_note && (
              <div className="cell-note">{idx.data_window_note}</div>
            )}
          </Link>
        );
      })}
    </div>
  );
}
