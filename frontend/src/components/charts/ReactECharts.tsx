import { useEffect, useRef } from "react";
import * as echarts from "echarts";

interface Props {
  // 用 CoreOption 接 + Record fallback，避免每个图表都写 `as EChartsOption`
  option: echarts.EChartsCoreOption | Record<string, unknown>;
  style?: React.CSSProperties;
}

export default function ReactECharts({ option, style }: Props) {
  const ref = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!ref.current) return;
    const chart = echarts.init(ref.current);
    chartRef.current = chart;
    const onResize = () => chart.resize();
    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("resize", onResize);
      chart.dispose();
    };
  }, []);

  useEffect(() => {
    chartRef.current?.setOption(option as echarts.EChartsCoreOption, true);
  }, [option]);

  return <div ref={ref} style={style ?? { height: 320, width: "100%" }} />;
}
