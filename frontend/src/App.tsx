import { Navigate, Route, Routes } from "react-router-dom";
import Header from "./components/layout/Header";
import Overview from "./pages/Overview";
import IndexDetail from "./pages/IndexDetail";
import StockDetail from "./pages/StockDetail";
import FundDetail from "./pages/FundDetail";
import Watchlist from "./pages/Watchlist";
import Signals from "./pages/Signals";
import TemperatureEffectiveness from "./pages/TemperatureEffectiveness";
import DCA from "./pages/DCA";
import Backtest from "./pages/Backtest";
import Settings from "./pages/Settings";

export default function App() {
  return (
    <div className="app">
      <Header />
      <main className="main">
        <Routes>
          <Route path="/" element={<Overview />} />
          <Route path="/indices/:code" element={<IndexDetail />} />
          <Route path="/stocks/:code" element={<StockDetail />} />
          <Route path="/funds/:code" element={<FundDetail />} />
          <Route path="/watchlist" element={<Watchlist />} />
          <Route path="/signals" element={<Signals />} />
          <Route path="/temperature/effectiveness" element={<TemperatureEffectiveness />} />
          <Route path="/dca" element={<DCA />} />
          <Route path="/backtest" element={<Backtest />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}
