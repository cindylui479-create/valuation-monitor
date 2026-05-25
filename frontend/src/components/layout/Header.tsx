import { NavLink } from "react-router-dom";

const NAV = [
  { to: "/", label: "总览" },
  { to: "/watchlist", label: "自选" },
  { to: "/signals", label: "信号" },
  { to: "/dca", label: "定投" },
  { to: "/backtest", label: "回测" },
  { to: "/settings", label: "设置" },
];

export default function Header() {
  return (
    <header className="header">
      <div className="brand">估值监测</div>
      <nav className="nav">
        {NAV.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/"}
            className={({ isActive }) => "nav-link" + (isActive ? " active" : "")}
          >
            {item.label}
          </NavLink>
        ))}
      </nav>
    </header>
  );
}
