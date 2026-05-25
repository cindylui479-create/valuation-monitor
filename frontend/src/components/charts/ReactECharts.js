import { jsx as _jsx } from "react/jsx-runtime";
import { useEffect, useRef } from "react";
import * as echarts from "echarts";
export default function ReactECharts({ option, style }) {
    const ref = useRef(null);
    const chartRef = useRef(null);
    useEffect(() => {
        if (!ref.current)
            return;
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
        chartRef.current?.setOption(option, true);
    }, [option]);
    return _jsx("div", { ref: ref, style: style ?? { height: 320, width: "100%" } });
}
