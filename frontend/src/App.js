import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { Navigate, Route, Routes } from "react-router-dom";
import Header from "./components/layout/Header";
import Overview from "./pages/Overview";
import IndexDetail from "./pages/IndexDetail";
import StockDetail from "./pages/StockDetail";
import FundDetail from "./pages/FundDetail";
import Watchlist from "./pages/Watchlist";
import Signals from "./pages/Signals";
import DCA from "./pages/DCA";
import Backtest from "./pages/Backtest";
import Settings from "./pages/Settings";
export default function App() {
    return (_jsxs("div", { className: "app", children: [_jsx(Header, {}), _jsx("main", { className: "main", children: _jsxs(Routes, { children: [_jsx(Route, { path: "/", element: _jsx(Overview, {}) }), _jsx(Route, { path: "/indices/:code", element: _jsx(IndexDetail, {}) }), _jsx(Route, { path: "/stocks/:code", element: _jsx(StockDetail, {}) }), _jsx(Route, { path: "/funds/:code", element: _jsx(FundDetail, {}) }), _jsx(Route, { path: "/watchlist", element: _jsx(Watchlist, {}) }), _jsx(Route, { path: "/signals", element: _jsx(Signals, {}) }), _jsx(Route, { path: "/dca", element: _jsx(DCA, {}) }), _jsx(Route, { path: "/backtest", element: _jsx(Backtest, {}) }), _jsx(Route, { path: "/settings", element: _jsx(Settings, {}) }), _jsx(Route, { path: "*", element: _jsx(Navigate, { to: "/", replace: true }) })] }) })] }));
}
