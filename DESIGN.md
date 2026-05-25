# 估值监测工具 系统设计文档（DESIGN）

| 项目 | 估值监测工具（ValuationMonitor） |
|---|---|
| 版本 | v1.0（草案） |
| 日期 | 2026-05-12 |
| 作者 | Cindy |
| 关联文档 | `SRS.md`（需求基线，本文档严格落地之） |
| 状态 | 待评审 |

---

## 0. 阅读指南

本文档为 SRS 之后的**系统设计基线**，覆盖：

1. 架构关键决策（A1–A10）
2. 系统架构与时序
3. REST API 详细设计（端点 / 请求 / 响应 / 错误码）
4. 数据模型 DDL（SQL + SQLAlchemy 2.x 双重呈现）
5. 数据源适配层与核心算法
6. 前端架构
7. 目录骨架（树 + 文件职责）
8. 测试策略
9. 部署与运维
10. 验收清单

凡 SRS 已锁定的业务规则（D1–D10）不再重复，仅在落地处引用。

---

## 1. 架构关键决策（A1–A10）

| 编号 | 决策 | 选择 | 理由 |
|---|---|---|---|
| A0 | Python 版本 | ≥ 3.10（**M1 验证后从 3.11 放宽**） | 测试环境 Python 3.10，仅 `StrEnum` / `datetime.UTC` 两处不兼容，可平凡降级；保留 3.11+ 不会带来显著收益 |
| A1 | 后端框架 | FastAPI + Uvicorn（单进程） | 异步 IO、文档自动生成、与 SQLAlchemy/Pydantic 协同好 |
| A2 | ORM | SQLAlchemy 2.x（Mapped 风格） | 类型友好、声明式、便于未来 SQLite→PG 迁移 |
| A3 | 调度 | APScheduler（嵌入 FastAPI 进程） | 单用户场景免去 Celery/Redis，可重启自恢复 |
| A4 | DB | SQLite（WAL 模式） | 零运维；WAL 解决读写并发，调度写 + Web 读不冲突 |
| A5 | 数据源适配 | Adapter 抽象基类 + 三方实现 | 三种数据源接口差异大，统一接口便于回退/替换 |
| A6 | 数值类型 | SQLite `NUMERIC`（绑定 Python `Decimal`） | 分位计算对浮点漂移敏感，避免 `0.30000000000004` 越界 |
| A7 | API 风格 | RESTful + JSON；查询/创建/更新分离；分页用 `limit/offset` | 简单，单用户不必上 GraphQL |
| A8 | 前端构建 | Vite + React 18 + TypeScript | 启动快、生态成熟 |
| A9 | 前端状态 | TanStack Query（服务端状态）+ Zustand（UI 局部状态） | Redux 对单用户太重；TanStack Query 自带缓存/失效 |
| A10 | 迁移工具 | Alembic | 与 SQLAlchemy 原生集成；版本化建表 |

> 决策树留痕：与 SRS D7（SQLite）、D8（localhost）、D10（历史/增量分离）保持一致。

---

## 2. 系统架构

### 2.1 物理部署视图

```
┌────────────────────────────────────────────────────────────────┐
│                  本机（127.0.0.1:8000）                          │
│                                                                │
│  ┌──────────────────────────────────────────────────────┐      │
│  │ FastAPI Process (Uvicorn, single worker)             │      │
│  │                                                      │      │
│  │  ┌────────┐  ┌──────────┐  ┌────────────────────┐    │      │
│  │  │ API    │  │ Static   │  │ APScheduler        │    │      │
│  │  │ Routes │  │ (React)  │  │ ┌──────────────┐   │    │      │
│  │  │        │  │ build/   │  │ │ A股 16:30    │   │    │      │
│  │  │        │  │          │  │ │ 港股 17:30   │   │    │      │
│  │  │        │  │          │  │ │ 美股 07:00   │   │    │      │
│  │  └────────┘  └──────────┘  │ └──────────────┘   │    │      │
│  │                            └────────────────────┘    │      │
│  │                                                      │      │
│  │  ┌────────────────────────────────────────────┐      │      │
│  │  │  Service Layer (Valuation / Signal / DCA)  │      │      │
│  │  └────────────────────────────────────────────┘      │      │
│  │                                                      │      │
│  │  ┌────────────────────────────────────────────┐      │      │
│  │  │  Data Source Adapters                      │      │      │
│  │  │  Akshare | yfinance | Tushare              │──┐   │      │
│  │  └────────────────────────────────────────────┘  │   │      │
│  │  ┌────────────────────────────────────────────┐  │   │      │
│  │  │  SQLAlchemy / Repositories                 │  │   │      │
│  │  └─────────────────────┬──────────────────────┘  │   │      │
│  └────────────────────────┼─────────────────────────┼───┘      │
│                           │                         │          │
│                  ┌────────▼─────────┐               │          │
│                  │ SQLite (WAL)     │               │          │
│                  │ data/valuation.db│               │          │
│                  └──────────────────┘               │          │
└─────────────────────────────────────────────────────┼──────────┘
                                                      │
                                          (出站 HTTPS)│
                                                      ▼
                                  AkShare / yfinance / Tushare API
```

### 2.2 逻辑分层

```
┌─────────────────────────────────────────────────────────────┐
│  Presentation (React SPA + FastAPI Routers)                 │
├─────────────────────────────────────────────────────────────┤
│  Application Services                                       │
│  ┌──────────────┬──────────────┬──────────────┬───────────┐ │
│  │ UniverseSvc  │ ValuationSvc │ SignalEngine │ DCAPlanner│ │
│  ├──────────────┴──────────────┴──────────────┴───────────┤ │
│  │ BacktestRunner    DataPipeline (orchestration)         │ │
│  └────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  Domain Models（Pydantic schemas + dataclasses）            │
├─────────────────────────────────────────────────────────────┤
│  Infrastructure                                             │
│  ┌──────────────────────┬──────────────────────┐            │
│  │ Repositories (ORM)   │ DataSourceAdapter    │            │
│  └──────────────────────┴──────────────────────┘            │
├─────────────────────────────────────────────────────────────┤
│  SQLite                                                     │
└─────────────────────────────────────────────────────────────┘
```

### 2.3 关键时序：每日批处理（以 A 股为例）

```
APScheduler             DataPipeline        AkshareAdapter         ValuationSvc       SignalEngine   DCAPlanner
    │                       │                     │                      │                  │              │
    │ trigger(market=A,     │                     │                      │                  │              │
    │  时间=16:30)          │                     │                      │                  │              │
    │──────────────────────▶│                     │                      │                  │              │
    │                       │  check_calendar(A)  │                      │                  │              │
    │                       │─────────────────────┼─▶ TradingCalendar    │                  │              │
    │                       │                     │                      │                  │              │
    │                       │  fetch_quotes(A, last_30d)                 │                  │              │
    │                       │────────────────────▶│                      │                  │              │
    │                       │  ◀── DataFrame ─────│                      │                  │              │
    │                       │  upsert_quotes()    │                      │                  │              │
    │                       │  + audit log        │                      │                  │              │
    │                       │                     │                      │                  │              │
    │                       │  recompute(last_30d)│                      │                  │              │
    │                       │─────────────────────┼─────────────────────▶│                  │              │
    │                       │                     │                      │ percentile/      │              │
    │                       │                     │                      │ temperature/tier │              │
    │                       │                     │                      │  upsert          │              │
    │                       │                     │                      │                  │              │
    │                       │  generate_signals(today, A)                │                  │              │
    │                       │────────────────────────────────────────────┼─────────────────▶│              │
    │                       │                     │                      │                  │ check tier   │
    │                       │                     │                      │                  │ insert       │
    │                       │                     │                      │                  │ Signal       │
    │                       │                     │                      │                  │              │
    │                       │  refresh_dca_executions(today)             │                  │              │
    │                       │────────────────────────────────────────────┼──────────────────┼─────────────▶│
    │                       │                     │                      │                  │              │ for each plan
    │                       │                     │                      │                  │              │ within 1 day
    │                       │                     │                      │                  │              │ apply tier
    │                       │                     │                      │                  │              │ insert DCAExecution
    │  ◀──── done ──────────│                     │                      │                  │              │
```

### 2.4 关键时序：用户加载总览页

```
Browser           FastAPI                ValuationSvc         Repo                SQLite
   │                  │                       │                  │                   │
   │ GET /api/overview│                       │                  │                   │
   │─────────────────▶│                       │                  │                   │
   │                  │ get_overview()        │                  │                   │
   │                  │──────────────────────▶│                  │                   │
   │                  │                       │ latest_valuations(grouped by market) │
   │                  │                       │─────────────────▶│ SELECT...         │
   │                  │                       │                  │──────────────────▶│
   │                  │                       │  ◀── rows ───────│ ◀────────────────│
   │                  │  ◀── DTOs ────────────│                  │                   │
   │ ◀── JSON ────────│                       │                  │                   │
```

---

## 3. REST API 详细设计

### 3.1 通用约定

- Base URL：`/api/v1`
- 内容类型：`application/json; charset=utf-8`
- 时间：ISO 8601（`2026-05-12T08:30:00Z`）
- 数值：金额 / 百分位用 `string` 承载 Decimal（避免 JS Number 精度丢失，前端用 `decimal.js` 解析）
- 错误响应统一结构：
  ```json
  { "error": { "code": "VALIDATION_ERROR", "message": "…", "details": {…} } }
  ```
- 错误码：

| code | HTTP | 含义 |
|---|---|---|
| `VALIDATION_ERROR` | 422 | 入参校验失败 |
| `NOT_FOUND` | 404 | 资源不存在 |
| `CONFLICT` | 409 | 资源冲突（如重复创建定投） |
| `BUSINESS_RULE_VIOLATION` | 400 | 违反业务规则（如绑定历史不足 5 年的指数到定投） |
| `DATA_SOURCE_UNAVAILABLE` | 503 | 数据源失败 |
| `INTERNAL_ERROR` | 500 | 未预期异常 |

### 3.2 端点清单

| 资源 | 方法 | 路径 | 说明 |
|---|---|---|---|
| 总览 | GET | `/api/v1/overview` | 三地估值总览（已聚合的最新分位+温度） |
| 指数 | GET | `/api/v1/indices` | 内置指数池列表，可按 market/category 过滤 |
| 指数 | GET | `/api/v1/indices/{code}` | 单指数元数据 + 对应基金 |
| 行情 | GET | `/api/v1/indices/{code}/quotes` | 历史行情，参数 `start`/`end`/`window` |
| 估值 | GET | `/api/v1/indices/{code}/valuation` | 历史估值分位序列 |
| 估值 | GET | `/api/v1/indices/{code}/valuation/latest` | 最新估值快照 |
| 自选 | GET | `/api/v1/watchlist` | 自选清单 |
| 自选 | POST | `/api/v1/watchlist` | 添加自选（body: `{index_code, tag}`） |
| 自选 | DELETE | `/api/v1/watchlist/{id}` | 移除自选 |
| 阈值覆盖 | GET | `/api/v1/threshold-overrides/{index_code}` | 取个性化阈值 |
| 阈值覆盖 | PUT | `/api/v1/threshold-overrides/{index_code}` | 设置/更新（部分字段即可） |
| 阈值覆盖 | DELETE | `/api/v1/threshold-overrides/{index_code}` | 删除（回退默认） |
| 信号 | GET | `/api/v1/signals` | 信号列表，参数 `date_from`/`date_to`/`market`/`tier` |
| 信号 | GET | `/api/v1/signals/today` | 今日信号 |
| 定投计划 | GET | `/api/v1/dca-plans` | 列表 |
| 定投计划 | POST | `/api/v1/dca-plans` | 创建 |
| 定投计划 | PUT | `/api/v1/dca-plans/{id}` | 更新 |
| 定投计划 | DELETE | `/api/v1/dca-plans/{id}` | 删除 |
| 定投执行 | GET | `/api/v1/dca-plans/{id}/executions` | 执行历史 |
| 定投执行 | POST | `/api/v1/dca-executions/{id}/mark-done` | 标记已执行 |
| 定投执行 | POST | `/api/v1/dca-executions/{id}/skip` | 跳过本期 |
| 定投提醒 | GET | `/api/v1/dca-reminders/upcoming` | 未来 7 天内待执行的定投 |
| 回测 | POST | `/api/v1/backtest/run` | 运行单次回测，不持久化 |
| 导出 | GET | `/api/v1/exports/index/{code}.csv` | CSV 下载 |
| 偏好 | GET | `/api/v1/preferences` | 用户偏好 |
| 偏好 | PUT | `/api/v1/preferences` | 更新偏好（覆盖式） |
| 健康 | GET | `/api/v1/health` | 数据源健康面板 |
| 健康 | GET | `/api/v1/health/pipeline` | 最近一次批处理状态 |

### 3.3 关键端点示例

#### GET `/api/v1/overview`

**响应**：
```json
{
  "as_of": "2026-05-12",
  "markets": [
    {
      "market": "A",
      "currency": "CNY",
      "indices": [
        {
          "code": "000300.SH",
          "name": "沪深300",
          "category": "宽基",
          "tier": "低估",
          "temperature": "23.5",
          "pe_ttm": "12.88",
          "pe_percentile_10y": "0.235",
          "pb_percentile_10y": "0.184",
          "dividend_yield": "0.0292",
          "ma50_deviation": "-0.012",
          "ma200_deviation": "0.034",
          "data_window_note": null,
          "funds_count": 3
        }
      ]
    },
    { "market": "HK", "currency": "HKD", "indices": [...] },
    { "market": "US", "currency": "USD", "indices": [...] }
  ]
}
```

#### GET `/api/v1/indices/{code}/valuation`

参数：
- `start`（可选，默认 10 年前）
- `end`（可选，默认昨日）
- `window`：`5y` / `10y` / `all`（默认 `10y`）

**响应**：
```json
{
  "code": "000300.SH",
  "window": "10y",
  "series": [
    { "date": "2026-05-08", "pe_ttm": "12.85", "pe_percentile": "0.235", "temperature": "23.5", "tier": "低估" },
    { "date": "2026-05-09", "pe_ttm": "12.78", "pe_percentile": "0.227", "temperature": "22.7", "tier": "低估" }
  ]
}
```

#### POST `/api/v1/dca-plans`

**请求**：
```json
{
  "index_code": "000922.CSI",
  "fund_code": "100032",
  "amount": "2000",
  "frequency": "MONTHLY",
  "day_of_period": 10,
  "start_date": "2026-06-10",
  "enabled": true
}
```

**业务校验**：
- `index_code` 存在
- `index` 可用历史 ≥ 5 年（否则返回 400 `BUSINESS_RULE_VIOLATION`，message: "该指数可用历史数据不足 5 年，无法绑定定投计划"）
- `frequency ∈ {WEEKLY, BIWEEKLY, MONTHLY}`
- 频率与 `day_of_period` 范围一致（周 1–7；月 1–28，避免 29/30/31 跨月问题，超过 28 直接拒绝）
- `amount > 0`
- `fund_code` 可空，存在时必须 `tracks_index_id == index.id`

**响应** 201 Created：
```json
{ "id": 7, "index_code": "000922.CSI", "amount": "2000", ... }
```

#### PUT `/api/v1/threshold-overrides/{index_code}`

**请求**（任一字段可选，未指定回退默认）：
```json
{
  "extreme_low_upper": "0.10",
  "low_upper": "0.20",
  "high_lower": "0.75",
  "extreme_high_lower": "0.92"
}
```

**校验**：
- `0 < extreme_low_upper < low_upper < high_lower < extreme_high_lower < 1`
- 任一字段缺失则用默认值参与排序校验

#### POST `/api/v1/backtest/run`

**请求**：
```json
{
  "index_code": "000300.SH",
  "buy_percentile_below": "0.20",
  "sell_percentile_above": "0.80",
  "start_date": "2016-01-01",
  "end_date": "2026-05-11"
}
```

**响应**：
```json
{
  "index_code": "000300.SH",
  "annualized_return": "0.087",
  "max_drawdown": "-0.342",
  "trade_count": 6,
  "trades": [
    { "date": "2018-10-22", "action": "BUY", "price": "3030.10", "pe_percentile": "0.18" },
    { "date": "2021-02-18", "action": "SELL", "price": "5807.72", "pe_percentile": "0.86" }
  ]
}
```

#### GET `/api/v1/health`

```json
{
  "sources": [
    { "name": "akshare", "last_success_at": "2026-05-12T08:30:12Z", "last_error_at": null, "error_rate_7d": "0.0" },
    { "name": "yfinance", "last_success_at": "2026-05-12T23:05:30Z", "last_error_at": "2026-05-10T23:05:30Z", "error_rate_7d": "0.14" }
  ],
  "pipeline": [
    { "market": "A", "last_run_at": "2026-05-12T08:30:00Z", "status": "SUCCESS", "duration_seconds": 412 },
    { "market": "HK", "last_run_at": "2026-05-12T09:30:00Z", "status": "SUCCESS", "duration_seconds": 188 },
    { "market": "US", "last_run_at": "2026-05-12T23:00:00Z", "status": "PARTIAL", "duration_seconds": 720 }
  ]
}
```

### 3.4 分页与排序

- 列表型端点（`/signals`, `/dca-plans/{id}/executions`）支持 `?limit=50&offset=0&order=desc`
- 默认 `limit=50`，最大 `200`

---

## 4. 数据模型 DDL

### 4.1 表清单

| # | 表名 | 说明 |
|---|---|---|
| 1 | `market` | 市场 |
| 2 | `trading_calendar` | 交易日历 |
| 3 | `index_meta` | 指数元数据（`index` 是 SQL 保留字，故用 `index_meta`） |
| 4 | `fund` | 跟踪基金 / ETF |
| 5 | `index_quote` | 日频原始行情 + 估值原始字段 |
| 6 | `valuation` | 派生分位/温度/档位（多窗口） |
| 7 | `watchlist` | 自选 |
| 8 | `signal` | 估值信号 |
| 9 | `dca_plan` | 定投计划 |
| 10 | `dca_execution` | 定投执行/提醒 |
| 11 | `threshold_override` | 个性化阈值 |
| 12 | `data_audit` | 数据回溯审计 |
| 13 | `user_preference` | 用户偏好 KV |

### 4.2 SQL DDL（SQLite 方言）

```sql
-- 通用：SQLite 启用外键约束 与 WAL
-- PRAGMA foreign_keys = ON;
-- PRAGMA journal_mode = WAL;

CREATE TABLE market (
  id        INTEGER PRIMARY KEY AUTOINCREMENT,
  code      TEXT NOT NULL UNIQUE,          -- 'A' / 'HK' / 'US'
  name      TEXT NOT NULL,
  currency  TEXT NOT NULL,                 -- 'CNY' / 'HKD' / 'USD'
  tz        TEXT NOT NULL                  -- 'Asia/Shanghai' / 'Asia/Hong_Kong' / 'America/New_York'
);

CREATE TABLE trading_calendar (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  market_id  INTEGER NOT NULL REFERENCES market(id),
  date       TEXT NOT NULL,                -- ISO 'YYYY-MM-DD'
  is_open    INTEGER NOT NULL,             -- 0/1
  UNIQUE (market_id, date)
);
CREATE INDEX idx_calendar_market_date ON trading_calendar(market_id, date);

CREATE TABLE index_meta (
  id                   INTEGER PRIMARY KEY AUTOINCREMENT,
  code                 TEXT NOT NULL UNIQUE,
  name                 TEXT NOT NULL,
  market_id            INTEGER NOT NULL REFERENCES market(id),
  category             TEXT NOT NULL,      -- '宽基' / '行业' / '主题'
  industry_raw         TEXT,
  data_source          TEXT NOT NULL,      -- 'akshare' / 'yfinance' / 'tushare'
  history_start_date   TEXT NOT NULL,      -- 数据可追溯的最早日期
  enabled              INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE fund (
  id                    INTEGER PRIMARY KEY AUTOINCREMENT,
  code                  TEXT NOT NULL UNIQUE,
  name                  TEXT NOT NULL,
  type                  TEXT NOT NULL,     -- 'ETF' / 'OPEN_FUND'
  tracks_index_id       INTEGER NOT NULL REFERENCES index_meta(id),
  market_id             INTEGER NOT NULL REFERENCES market(id),
  fee_rate              NUMERIC(8,6),
  tracking_error_note   TEXT
);
CREATE INDEX idx_fund_tracks ON fund(tracks_index_id);

CREATE TABLE index_quote (
  id                   INTEGER PRIMARY KEY AUTOINCREMENT,
  index_id             INTEGER NOT NULL REFERENCES index_meta(id),
  date                 TEXT NOT NULL,
  close                NUMERIC(18,6) NOT NULL,
  pe_ttm               NUMERIC(18,6),
  pb                   NUMERIC(18,6),
  dividend_yield       NUMERIC(18,8),
  roe                  NUMERIC(18,8),
  earnings_growth_3y   NUMERIC(18,8),
  ma50                 NUMERIC(18,6),
  ma200                NUMERIC(18,6),
  northbound_60d_pct   NUMERIC(18,8),      -- 仅 A 股
  source               TEXT NOT NULL,
  created_at           TEXT NOT NULL,
  UNIQUE (index_id, date)
);
CREATE INDEX idx_quote_index_date ON index_quote(index_id, date);

CREATE TABLE valuation (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  index_id        INTEGER NOT NULL REFERENCES index_meta(id),
  date            TEXT NOT NULL,
  window          TEXT NOT NULL,           -- '5y' / '10y' / 'all'
  pe_percentile   NUMERIC(10,8),
  pb_percentile   NUMERIC(10,8),
  dy_percentile   NUMERIC(10,8),
  temperature     NUMERIC(10,6),           -- = pe_percentile * 100，仅在 window='10y' 时有效
  tier            TEXT,                    -- '极度低估'/'低估'/'合理'/'高估'/'极度高估'
  computed_at     TEXT NOT NULL,
  UNIQUE (index_id, date, window)
);
CREATE INDEX idx_valuation_index_date_window ON valuation(index_id, date, window);

CREATE TABLE watchlist (
  id        INTEGER PRIMARY KEY AUTOINCREMENT,
  index_id  INTEGER NOT NULL REFERENCES index_meta(id),
  tag       TEXT,                          -- 用户自定义标签，例如 '核心'/'卫星'
  added_at  TEXT NOT NULL,
  UNIQUE (index_id, tag)
);

CREATE TABLE signal (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  index_id      INTEGER NOT NULL REFERENCES index_meta(id),
  date          TEXT NOT NULL,
  direction     TEXT NOT NULL,            -- 'STRONG_BUY'/'BUY'/'SELL'/'STRONG_SELL'
  tier          TEXT NOT NULL,
  temperature   NUMERIC(10,6) NOT NULL,
  generated_at  TEXT NOT NULL,
  UNIQUE (index_id, date)                 -- 每个指数每日最多一条
);
CREATE INDEX idx_signal_date ON signal(date);

CREATE TABLE dca_plan (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  index_id        INTEGER NOT NULL REFERENCES index_meta(id),
  fund_id         INTEGER REFERENCES fund(id),
  amount          NUMERIC(18,2) NOT NULL,
  frequency       TEXT NOT NULL,           -- 'WEEKLY' / 'BIWEEKLY' / 'MONTHLY'
  day_of_period   INTEGER NOT NULL,        -- 1–7（周）/ 1–28（月）
  start_date      TEXT NOT NULL,
  enabled         INTEGER NOT NULL DEFAULT 1,
  created_at      TEXT NOT NULL,
  updated_at      TEXT NOT NULL
);
CREATE INDEX idx_dca_index ON dca_plan(index_id);

CREATE TABLE dca_execution (
  id                  INTEGER PRIMARY KEY AUTOINCREMENT,
  plan_id             INTEGER NOT NULL REFERENCES dca_plan(id),
  scheduled_date      TEXT NOT NULL,        -- 用户配置原始期望日
  actual_date         TEXT NOT NULL,        -- 顺延后的实际定投日
  base_amount         NUMERIC(18,2) NOT NULL,
  adjusted_amount     NUMERIC(18,2) NOT NULL,
  multiplier          NUMERIC(6,2) NOT NULL,-- 2.0 / 1.0 / 0.5 / 0.0
  tier_at_decision    TEXT NOT NULL,
  temperature         NUMERIC(10,6) NOT NULL,
  status              TEXT NOT NULL,        -- 'PENDING' / 'DONE' / 'SKIPPED'
  generated_at        TEXT NOT NULL,
  marked_at           TEXT,
  UNIQUE (plan_id, actual_date)
);
CREATE INDEX idx_dca_exec_plan_date ON dca_execution(plan_id, actual_date);

CREATE TABLE threshold_override (
  id                    INTEGER PRIMARY KEY AUTOINCREMENT,
  index_id              INTEGER NOT NULL UNIQUE REFERENCES index_meta(id),
  boundaries_json       TEXT NOT NULL,      -- JSON: {extreme_low_upper, low_upper, high_lower, extreme_high_lower}
  updated_at            TEXT NOT NULL
);

CREATE TABLE data_audit (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  table_name    TEXT NOT NULL,
  record_key    TEXT NOT NULL,            -- 例如 'index_quote:000300.SH:2026-05-10'
  field         TEXT NOT NULL,
  old_value     TEXT,
  new_value     TEXT,
  source        TEXT NOT NULL,
  audit_time    TEXT NOT NULL
);
CREATE INDEX idx_audit_record ON data_audit(record_key);

CREATE TABLE user_preference (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  key         TEXT NOT NULL UNIQUE,
  value_json  TEXT NOT NULL,              -- 自由 JSON
  updated_at  TEXT NOT NULL
);
```

### 4.3 SQLAlchemy 2.x 模型（Mapped 风格）

```python
# app/models/base.py
from datetime import datetime
from decimal import Decimal
from sqlalchemy import String, Integer, ForeignKey, Numeric, UniqueConstraint, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# app/models/market.py
class Market(Base):
    __tablename__ = "market"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(8), unique=True)
    name: Mapped[str] = mapped_column(String(64))
    currency: Mapped[str] = mapped_column(String(8))
    tz: Mapped[str] = mapped_column(String(64))

    indices: Mapped[list["IndexMeta"]] = relationship(back_populates="market")
    calendar: Mapped[list["TradingCalendar"]] = relationship(back_populates="market")


class TradingCalendar(Base):
    __tablename__ = "trading_calendar"
    __table_args__ = (UniqueConstraint("market_id", "date"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    market_id: Mapped[int] = mapped_column(ForeignKey("market.id"))
    date: Mapped[str] = mapped_column(String(10))  # ISO date
    is_open: Mapped[bool] = mapped_column()
    market: Mapped[Market] = relationship(back_populates="calendar")


# app/models/index.py
class IndexMeta(Base):
    __tablename__ = "index_meta"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(128))
    market_id: Mapped[int] = mapped_column(ForeignKey("market.id"))
    category: Mapped[str] = mapped_column(String(16))         # 宽基/行业/主题
    industry_raw: Mapped[str | None] = mapped_column(String(64))
    data_source: Mapped[str] = mapped_column(String(32))
    history_start_date: Mapped[str] = mapped_column(String(10))
    enabled: Mapped[bool] = mapped_column(default=True)

    market: Mapped[Market] = relationship(back_populates="indices")
    funds: Mapped[list["Fund"]] = relationship(back_populates="tracks_index")
    quotes: Mapped[list["IndexQuote"]] = relationship(back_populates="index")
    valuations: Mapped[list["Valuation"]] = relationship(back_populates="index")


class Fund(Base):
    __tablename__ = "fund"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(128))
    type: Mapped[str] = mapped_column(String(16))             # ETF / OPEN_FUND
    tracks_index_id: Mapped[int] = mapped_column(ForeignKey("index_meta.id"))
    market_id: Mapped[int] = mapped_column(ForeignKey("market.id"))
    fee_rate: Mapped[Decimal | None] = mapped_column(Numeric(8, 6))
    tracking_error_note: Mapped[str | None] = mapped_column(String(256))

    tracks_index: Mapped[IndexMeta] = relationship(back_populates="funds")


# app/models/quote.py
class IndexQuote(Base):
    __tablename__ = "index_quote"
    __table_args__ = (
        UniqueConstraint("index_id", "date"),
        Index("idx_quote_index_date", "index_id", "date"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    index_id: Mapped[int] = mapped_column(ForeignKey("index_meta.id"))
    date: Mapped[str] = mapped_column(String(10))
    close: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    pe_ttm: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    pb: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    dividend_yield: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))
    roe: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))
    earnings_growth_3y: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))
    ma50: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    ma200: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    northbound_60d_pct: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))
    source: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[str] = mapped_column(String(32))

    index: Mapped[IndexMeta] = relationship(back_populates="quotes")


# app/models/valuation.py
class Valuation(Base):
    __tablename__ = "valuation"
    __table_args__ = (
        UniqueConstraint("index_id", "date", "window"),
        Index("idx_valuation_index_date_window", "index_id", "date", "window"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    index_id: Mapped[int] = mapped_column(ForeignKey("index_meta.id"))
    date: Mapped[str] = mapped_column(String(10))
    window: Mapped[str] = mapped_column(String(8))            # 5y / 10y / all
    pe_percentile: Mapped[Decimal | None] = mapped_column(Numeric(10, 8))
    pb_percentile: Mapped[Decimal | None] = mapped_column(Numeric(10, 8))
    dy_percentile: Mapped[Decimal | None] = mapped_column(Numeric(10, 8))
    temperature: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    tier: Mapped[str | None] = mapped_column(String(16))
    computed_at: Mapped[str] = mapped_column(String(32))

    index: Mapped[IndexMeta] = relationship(back_populates="valuations")


# app/models/watchlist.py
class Watchlist(Base):
    __tablename__ = "watchlist"
    __table_args__ = (UniqueConstraint("index_id", "tag"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    index_id: Mapped[int] = mapped_column(ForeignKey("index_meta.id"))
    tag: Mapped[str | None] = mapped_column(String(32))
    added_at: Mapped[str] = mapped_column(String(32))


# app/models/signal.py
class Signal(Base):
    __tablename__ = "signal"
    __table_args__ = (
        UniqueConstraint("index_id", "date"),
        Index("idx_signal_date", "date"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    index_id: Mapped[int] = mapped_column(ForeignKey("index_meta.id"))
    date: Mapped[str] = mapped_column(String(10))
    direction: Mapped[str] = mapped_column(String(16))   # STRONG_BUY / BUY / SELL / STRONG_SELL
    tier: Mapped[str] = mapped_column(String(16))
    temperature: Mapped[Decimal] = mapped_column(Numeric(10, 6))
    generated_at: Mapped[str] = mapped_column(String(32))


# app/models/dca.py
class DCAPlan(Base):
    __tablename__ = "dca_plan"
    id: Mapped[int] = mapped_column(primary_key=True)
    index_id: Mapped[int] = mapped_column(ForeignKey("index_meta.id"))
    fund_id: Mapped[int | None] = mapped_column(ForeignKey("fund.id"))
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    frequency: Mapped[str] = mapped_column(String(16))   # WEEKLY/BIWEEKLY/MONTHLY
    day_of_period: Mapped[int] = mapped_column(Integer)
    start_date: Mapped[str] = mapped_column(String(10))
    enabled: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[str] = mapped_column(String(32))
    updated_at: Mapped[str] = mapped_column(String(32))


class DCAExecution(Base):
    __tablename__ = "dca_execution"
    __table_args__ = (UniqueConstraint("plan_id", "actual_date"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("dca_plan.id"))
    scheduled_date: Mapped[str] = mapped_column(String(10))
    actual_date: Mapped[str] = mapped_column(String(10))
    base_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    adjusted_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    multiplier: Mapped[Decimal] = mapped_column(Numeric(6, 2))
    tier_at_decision: Mapped[str] = mapped_column(String(16))
    temperature: Mapped[Decimal] = mapped_column(Numeric(10, 6))
    status: Mapped[str] = mapped_column(String(16))      # PENDING / DONE / SKIPPED
    generated_at: Mapped[str] = mapped_column(String(32))
    marked_at: Mapped[str | None] = mapped_column(String(32))


# app/models/override.py
class ThresholdOverride(Base):
    __tablename__ = "threshold_override"
    id: Mapped[int] = mapped_column(primary_key=True)
    index_id: Mapped[int] = mapped_column(ForeignKey("index_meta.id"), unique=True)
    boundaries_json: Mapped[str] = mapped_column(String(512))
    updated_at: Mapped[str] = mapped_column(String(32))


# app/models/audit.py
class DataAudit(Base):
    __tablename__ = "data_audit"
    id: Mapped[int] = mapped_column(primary_key=True)
    table_name: Mapped[str] = mapped_column(String(32))
    record_key: Mapped[str] = mapped_column(String(128))
    field: Mapped[str] = mapped_column(String(32))
    old_value: Mapped[str | None] = mapped_column(String(64))
    new_value: Mapped[str | None] = mapped_column(String(64))
    source: Mapped[str] = mapped_column(String(32))
    audit_time: Mapped[str] = mapped_column(String(32))


# app/models/preference.py
class UserPreference(Base):
    __tablename__ = "user_preference"
    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(64), unique=True)
    value_json: Mapped[str] = mapped_column(String(2048))
    updated_at: Mapped[str] = mapped_column(String(32))
```

> **关于 Numeric / Decimal**：SQLite 不原生支持 `NUMERIC` 类型族，会按 affinity 存为 TEXT 或 REAL。SQLAlchemy 的 `Numeric` 类型会自动把 `Decimal` 序列化为字符串并在读取时还原，从而避免浮点漂移。这是 A6 决策的实现依据。

### 4.4 关键索引与查询

| 高频查询 | 索引 |
|---|---|
| 取指数最新估值 | `idx_valuation_index_date_window`（按 `(index_id, window)` 拿最新 `date`） |
| 总览页加载 | 对每个市场用窗口函数取每个 `index_id` 最新 `valuation` 行 |
| 信号列表按日期倒序 | `idx_signal_date` |
| 行情序列查询 | `idx_quote_index_date` |
| 审计回查 | `idx_audit_record` 按 `record_key` |

### 4.5 Alembic 迁移

- 初始迁移：`alembic revision -m "initial schema"` 后由 `alembic upgrade head` 应用
- 每次 SRS/Design 调整 schema：先改模型 → autogenerate → 人工核查（autogenerate 对 SQLite 行为有限）→ apply

---

## 5. 数据源适配层

### 5.1 接口约定

```python
# app/adapters/base.py
from abc import ABC, abstractmethod
from datetime import date
from typing import Iterable, Protocol
from dataclasses import dataclass


@dataclass
class QuoteRow:
    index_code: str
    date: str                   # YYYY-MM-DD
    close: Decimal
    pe_ttm: Decimal | None
    pb: Decimal | None
    dividend_yield: Decimal | None
    roe: Decimal | None
    earnings_growth_3y: Decimal | None
    ma50: Decimal | None
    ma200: Decimal | None
    northbound_60d_pct: Decimal | None  # 仅 A 股
    source: str


class DataSourceAdapter(ABC):
    name: str
    supported_markets: tuple[str, ...]  # ('A',) / ('A','HK') / ('US',)

    @abstractmethod
    def fetch_quotes(
        self,
        index_codes: list[str],
        start: date,
        end: date,
    ) -> Iterable[QuoteRow]:
        """拉取指定日期范围的行情。允许部分字段为 None。"""

    @abstractmethod
    def fetch_calendar(self, market: str, year: int) -> list[tuple[str, bool]]:
        """返回 [(date, is_open), ...]"""

    def health_check(self) -> bool:
        """轻量探活，默认实现取一次小数据点。"""
        ...
```

### 5.2 三个具体实现

- `AkshareAdapter`：主负责 A 股 + 港股
  - **A 股 PE-TTM + 指数点位**：`ak.stock_index_pe_lg(symbol=<中文名>)` —— 5000+ 行历史（2005 起）
  - **A 股 PB**：`ak.stock_index_pb_lg(symbol=<中文名>)` —— 同上
  - **代码 → 中文名映射**：在 `_LG_NAME` 常量内（M1 含 沪深300/中证500/800/1000/上证50）
  - **行情 OHLC**（MA50/MA200 等辅助指标，M2 起）：`ak.index_zh_a_hist(symbol=<数字代码>, period='daily')`
  - **交易日历**：`ak.tool_trade_date_hist_sina()`
  - **股息率快照**（M3 末实装 R2）：`stock_zh_index_value_csindex(symbol=6位代码)` 给最近 20 个交易日股息率快照（中证指数公司官方）；按日期 left-join 进 QuoteRow，每日累积。1 年后达 R7 阈值（≥250 点）自动激活分位
  - 港股待 M3 实装
- `YfinanceAdapter`：负责**港股 + 美股**（M3 实装；AkShare HK 接口在 CN 网络下不可达）
  - 历史 OHLC：`yf.Ticker(code).history(period="max")` —— SPY 33 年、QQQ 27 年等
  - 当日 PE/PB/股息率快照：`yf.Ticker(code).info.trailingPE / priceToBook / dividendYield`
  - 历史日的 PE/PB 字段全为 None；只在最新一行写快照
  - 港股池：`^HSI`（恒生）、`^HSCE`（国企）、`3033.HK`（恒生科技 ETF，含 trailingPE）
  - 美股池：`SPY`/`QQQ`/`DIA`（宽基 ETF）+ `XLK`/`XLV`/`XLF`（行业 ETF），全部含 trailingPE
- `TushareAdapter`：可选增强，要求用户提供 `TUSHARE_TOKEN` 环境变量；优先级最低（按需启用）

> **M1 验证发现的接口错配**：早期假设 `stock_zh_index_value_csindex` 提供历史 PE/PB；实测仅返回最近 20 个交易日且无指数 close、无 PB。已切换到 `stock_index_pe_lg` / `stock_index_pb_lg`（乐咕乐股聚合）。

### 5.3 多源回退

```python
# app/services/data_pipeline.py
def fetch_with_fallback(index: IndexMeta, start, end):
    primary = adapter_registry.get(index.data_source)
    try:
        return primary.fetch_quotes([index.code], start, end)
    except DataSourceError as e:
        log.warning(f"primary failed: {e}")
        for fallback in adapter_registry.fallbacks(index.market):
            try:
                return fallback.fetch_quotes([index.code], start, end)
            except DataSourceError:
                continue
        raise DataSourceUnavailable(index.code)
```

---

## 6. 核心算法

### 6.1 百分位与温度计算

```python
# app/valuation/percentile.py
import bisect
from decimal import Decimal


def percentile_of(value: Decimal, sorted_series: list[Decimal]) -> Decimal:
    """value 在升序 sorted_series 中的百分位（含相同值取中位法）。"""
    if not sorted_series:
        return None
    lo = bisect.bisect_left(sorted_series, value)
    hi = bisect.bisect_right(sorted_series, value)
    rank = (lo + hi) / 2
    return Decimal(rank) / Decimal(len(sorted_series))


def temperature(pe_percentile: Decimal) -> Decimal:
    return pe_percentile * Decimal(100)


def tier_of(temperature: Decimal, boundaries: dict[str, Decimal]) -> str:
    """boundaries: 默认 {0.10, 0.30, 0.70, 0.90} → 对应温度 *100 后比较。"""
    t = temperature
    if t < boundaries["extreme_low_upper"] * 100:
        return "极度低估"
    if t < boundaries["low_upper"] * 100:
        return "低估"
    if t < boundaries["high_lower"] * 100:
        return "合理"
    if t < boundaries["extreme_high_lower"] * 100:
        return "高估"
    return "极度高估"
```

### 6.2 信号生成

```python
def generate_signals_for(date_: str, market: str) -> list[Signal]:
    out = []
    for idx in repo.indices_by_market(market):
        v = repo.latest_valuation(idx.id, window="10y")
        if v is None or v.date != date_:
            continue
        if not has_enough_history(idx, min_years=5):
            continue
        boundaries = override_or_default(idx.id)
        tier = tier_of(v.temperature, boundaries)
        direction = {
            "极度低估": "STRONG_BUY",
            "低估":     "BUY",
            "合理":     None,
            "高估":     "SELL",
            "极度高估": "STRONG_SELL",
        }[tier]
        if direction is None:
            continue
        out.append(Signal(index_id=idx.id, date=date_,
                          direction=direction, tier=tier,
                          temperature=v.temperature,
                          generated_at=now_iso()))
    return out
```

### 6.3 定投联动（D6 方案 A）

```python
def compute_dca_multiplier(tier: str) -> Decimal:
    return {
        "极度低估": Decimal("2.0"),
        "低估":     Decimal("2.0"),
        "合理":     Decimal("1.0"),
        "高估":     Decimal("0.5"),
        "极度高估": Decimal("0.0"),
    }[tier]


def schedule_executions_for(today: date):
    """每日批处理后，对启用的定投计划，生成未来 1–7 天内的 DCAExecution。"""
    for plan in repo.dca_plans_enabled():
        for upcoming in upcoming_due_dates(plan, lookahead_days=7, from_=today):
            actual = next_trading_day_inclusive(upcoming, plan.market)
            if repo.execution_exists(plan.id, actual):
                continue
            v = repo.latest_valuation(plan.index_id, window="10y")
            boundaries = override_or_default(plan.index_id)
            tier = tier_of(v.temperature, boundaries)
            multiplier = compute_dca_multiplier(tier)
            adjusted = plan.amount * multiplier
            repo.insert(DCAExecution(
                plan_id=plan.id,
                scheduled_date=upcoming.isoformat(),
                actual_date=actual.isoformat(),
                base_amount=plan.amount,
                adjusted_amount=adjusted,
                multiplier=multiplier,
                tier_at_decision=tier,
                temperature=v.temperature,
                status="PENDING",
                generated_at=now_iso(),
            ))
```

### 6.4 回测

```python
def run_backtest(index_code, buy_pct, sell_pct, start, end):
    series = repo.valuation_series(index_code, window="10y", start=start, end=end)
    quotes = repo.quotes(index_code, start, end)
    cash = Decimal("1")  # 归一化资金
    shares = Decimal("0")
    nav_curve = []
    trades = []
    holding = False
    for q in quotes:
        v = series.get(q.date)
        if v is None:
            continue
        nav = cash + shares * q.close
        nav_curve.append((q.date, nav))
        if not holding and v.pe_percentile < buy_pct:
            shares = cash / q.close
            cash = Decimal("0")
            holding = True
            trades.append({"date": q.date, "action": "BUY",
                           "price": q.close, "pe_percentile": v.pe_percentile})
        elif holding and v.pe_percentile > sell_pct:
            cash = shares * q.close
            shares = Decimal("0")
            holding = False
            trades.append({"date": q.date, "action": "SELL",
                           "price": q.close, "pe_percentile": v.pe_percentile})
    return {
        "annualized_return": annualized(nav_curve),
        "max_drawdown": max_drawdown(nav_curve),
        "trades": trades,
    }
```

### 6.5 非交易日顺延

```python
def next_trading_day_inclusive(d: date, market: str) -> date:
    cur = d
    while not is_open(market, cur):
        cur += timedelta(days=1)
    return cur
```

---

## 7. 前端架构

### 7.1 技术栈

- **构建**：Vite 5
- **框架**：React 18 + TypeScript
- **UI 库**：shadcn-ui（Radix UI 衍生，主题可定制）
- **图表**：ECharts 5（金融场景：双轴、缩放、参考线、标注）
- **路由**：react-router 6
- **状态**：
  - 服务端状态：TanStack Query（缓存、自动重新验证）
  - UI 局部状态：Zustand（侧边栏开合、主题、热力图配色等）
- **数值**：`decimal.js` 解析后端字符串数值
- **国际化**：MVP 仅中文，预留 react-i18next

### 7.2 路由树

```
/                          → Overview (总览)
/indices/:code             → IndexDetail (详情)
/watchlist                 → Watchlist (自选)
/signals                   → Signals (信号)
/dca                       → DCA (定投)
/backtest                  → Backtest (回测)
/settings                  → Settings (设置)
```

### 7.3 组件树（关键页面）

```
<App>
  <Header navItems=[...]/>
  <Routes>
    <Overview>
      <MarketColumn market="A">
        <Heatmap indices=[...] />
        <TableView indices=[...] />
      </MarketColumn>
      <MarketColumn market="HK" />
      <MarketColumn market="US" />
    </Overview>

    <IndexDetail>
      <IndexHeader />
      <FundList />
      <PriceValuationChart />     // 价格 + PE 双轴 + 参考线
      <PBSeriesChart />
      <DividendYieldChart />
      <AuxiliaryIndicatorsCard /> // MA 偏离 + 北向资金
      <ThresholdOverrideDialog />
    </IndexDetail>

    <DCA>
      <UpcomingRemindersBoard />
      <PlansList>
        <PlanCard />
      </PlansList>
      <PlanEditorDialog />
    </DCA>
  </Routes>
</App>
```

### 7.4 数据流（以总览页为例）

1. `Overview` mount → `useQuery(['overview'], fetchOverview)` 触发 `GET /api/v1/overview`
2. TanStack Query 缓存返回 `OverviewDTO`
3. `Heatmap` 拿到 `indices` 数组渲染色块，颜色由 `tier` 决定
4. 用户切换"表格视图"时仅切组件，不重发请求
5. 缓存默认 `staleTime: 5 min`（每日数据，无需频繁刷新）

---

## 8. 目录骨架

```
ValuationMonitor/
├── SRS.md                         # 需求规格说明（已存在）
├── DESIGN.md                      # 本文档
├── README.md                      # 部署/使用快速开始
├── .gitignore
├── docker-compose.yml             # 生产/本地一键起服
├── .env.example                   # 环境变量模板
│
├── backend/
│   ├── pyproject.toml             # uv / poetry 依赖管理
│   ├── README.md
│   ├── Dockerfile
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/              # 迁移脚本
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                # FastAPI 应用工厂、APScheduler 启动
│   │   ├── config.py              # Pydantic Settings 读 .env
│   │   ├── db.py                  # engine / session 工厂 / WAL pragma
│   │   ├── deps.py                # FastAPI 依赖注入
│   │   ├── errors.py              # 错误码枚举 + 异常处理器
│   │   │
│   │   ├── models/                # SQLAlchemy 模型
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── market.py
│   │   │   ├── index.py           # IndexMeta, Fund
│   │   │   ├── quote.py
│   │   │   ├── valuation.py
│   │   │   ├── watchlist.py
│   │   │   ├── signal.py
│   │   │   ├── dca.py             # DCAPlan, DCAExecution
│   │   │   ├── override.py        # ThresholdOverride
│   │   │   ├── audit.py
│   │   │   └── preference.py
│   │   │
│   │   ├── schemas/               # Pydantic 模型（API 入参/出参）
│   │   │   ├── __init__.py
│   │   │   ├── common.py          # 错误响应、分页等
│   │   │   ├── overview.py
│   │   │   ├── index.py
│   │   │   ├── quote.py
│   │   │   ├── valuation.py
│   │   │   ├── watchlist.py
│   │   │   ├── signal.py
│   │   │   ├── dca.py
│   │   │   ├── override.py
│   │   │   ├── backtest.py
│   │   │   └── health.py
│   │   │
│   │   ├── api/                   # FastAPI 路由
│   │   │   ├── __init__.py
│   │   │   ├── router.py          # 聚合所有子路由
│   │   │   ├── overview.py
│   │   │   ├── indices.py
│   │   │   ├── watchlist.py
│   │   │   ├── valuation.py
│   │   │   ├── signals.py
│   │   │   ├── dca.py
│   │   │   ├── overrides.py
│   │   │   ├── backtest.py
│   │   │   ├── exports.py
│   │   │   ├── preferences.py
│   │   │   └── health.py
│   │   │
│   │   ├── repositories/          # 数据访问层
│   │   │   ├── __init__.py
│   │   │   ├── base.py            # 通用 CRUD 基类
│   │   │   ├── index_repo.py
│   │   │   ├── quote_repo.py
│   │   │   ├── valuation_repo.py
│   │   │   ├── watchlist_repo.py
│   │   │   ├── signal_repo.py
│   │   │   ├── dca_repo.py
│   │   │   ├── override_repo.py
│   │   │   ├── audit_repo.py
│   │   │   └── preference_repo.py
│   │   │
│   │   ├── services/              # 业务服务
│   │   │   ├── __init__.py
│   │   │   ├── universe_service.py     # YAML 池导入 / 自选管理
│   │   │   ├── data_pipeline.py        # 每日批处理编排
│   │   │   ├── valuation_service.py    # 调用计算引擎
│   │   │   ├── signal_engine.py
│   │   │   ├── dca_planner.py
│   │   │   ├── backtest_runner.py
│   │   │   └── health_service.py
│   │   │
│   │   ├── valuation/             # 估值计算（纯函数）
│   │   │   ├── __init__.py
│   │   │   ├── percentile.py
│   │   │   ├── temperature.py
│   │   │   └── tier.py
│   │   │
│   │   ├── adapters/              # 数据源适配
│   │   │   ├── __init__.py
│   │   │   ├── base.py            # DataSourceAdapter 抽象基类
│   │   │   ├── akshare_adapter.py
│   │   │   ├── yfinance_adapter.py
│   │   │   ├── tushare_adapter.py
│   │   │   └── registry.py        # 按市场/优先级注册
│   │   │
│   │   ├── scheduler/             # APScheduler 配置
│   │   │   ├── __init__.py
│   │   │   ├── jobs.py            # 三地 cron job 注册
│   │   │   └── runner.py          # 调度生命周期
│   │   │
│   │   ├── trading_calendar/      # 交易日历工具
│   │   │   ├── __init__.py
│   │   │   ├── loader.py
│   │   │   └── utils.py           # next_trading_day_inclusive 等
│   │   │
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── decimal_utils.py
│   │       ├── time_utils.py
│   │       ├── logging.py
│   │       └── exceptions.py
│   │
│   └── tests/                     # pytest
│       ├── conftest.py            # 测试 DB fixture（in-memory SQLite）
│       ├── unit/
│       │   ├── test_percentile.py
│       │   ├── test_temperature.py
│       │   ├── test_tier.py
│       │   ├── test_dca_multiplier.py
│       │   ├── test_calendar_rollover.py
│       │   └── test_backtest.py
│       ├── integration/
│       │   ├── test_data_pipeline.py
│       │   ├── test_signal_engine.py
│       │   └── test_dca_planner.py
│       ├── api/
│       │   ├── test_overview_api.py
│       │   ├── test_dca_api.py
│       │   └── test_backtest_api.py
│       └── fixtures/
│           ├── seed_universe.yaml
│           └── seed_quotes.csv
│
├── frontend/
│   ├── package.json
│   ├── pnpm-lock.yaml
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── index.html
│   ├── Dockerfile
│   ├── public/
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── routes.tsx             # react-router 配置
│       ├── api/
│       │   ├── client.ts          # fetch 封装 + Decimal 转换
│       │   ├── overview.ts
│       │   ├── indices.ts
│       │   ├── valuation.ts
│       │   ├── watchlist.ts
│       │   ├── signals.ts
│       │   ├── dca.ts
│       │   ├── overrides.ts
│       │   ├── backtest.ts
│       │   └── health.ts
│       ├── pages/
│       │   ├── Overview/
│       │   │   ├── index.tsx
│       │   │   ├── Heatmap.tsx
│       │   │   ├── TableView.tsx
│       │   │   └── MarketColumn.tsx
│       │   ├── IndexDetail/
│       │   │   ├── index.tsx
│       │   │   ├── PriceValuationChart.tsx
│       │   │   ├── PBSeriesChart.tsx
│       │   │   ├── DividendYieldChart.tsx
│       │   │   ├── AuxiliaryIndicatorsCard.tsx
│       │   │   └── ThresholdOverrideDialog.tsx
│       │   ├── Watchlist/
│       │   ├── Signals/
│       │   ├── DCA/
│       │   │   ├── index.tsx
│       │   │   ├── UpcomingRemindersBoard.tsx
│       │   │   ├── PlanCard.tsx
│       │   │   └── PlanEditorDialog.tsx
│       │   ├── Backtest/
│       │   └── Settings/
│       ├── components/
│       │   ├── ui/                # shadcn 通用组件
│       │   ├── charts/            # ECharts 包装
│       │   └── layout/
│       ├── hooks/
│       │   ├── useOverview.ts
│       │   ├── useIndexDetail.ts
│       │   └── useDCAPlans.ts
│       ├── store/
│       │   ├── ui.ts              # Zustand UI store
│       │   └── prefs.ts
│       ├── styles/
│       │   ├── globals.css
│       │   └── tokens.css         # 配色/温度色阶
│       ├── types/
│       │   └── api.ts             # 后端 DTO TypeScript 镜像
│       └── utils/
│           ├── decimal.ts
│           ├── temperature.ts     # 前端温度→颜色映射
│           └── format.ts
│
├── data/                          # 运行时数据（gitignored）
│   ├── index_universe.yaml        # 内置指数池（版本化）
│   └── valuation.db               # SQLite 文件
│
├── scripts/                       # 一次性脚本
│   ├── init_history.py            # 历史初始化（D10）
│   ├── seed_universe.py           # 从 YAML 导入指数池
│   ├── healthcheck.py             # CLI 健康检查
│   └── backup_db.py               # SQLite 备份
│
└── docs/                          # 补充文档（可选）
    ├── api_examples.http          # curl/REST Client 示例
    └── adr/                       # Architecture Decision Records
        └── README.md
```

### 8.1 各文件职责（关键文件）

| 文件 | 职责 |
|---|---|
| `backend/app/main.py` | 创建 FastAPI 应用、注册路由、启动 APScheduler、应用启动时确认 DB 迁移已 head |
| `backend/app/config.py` | Pydantic Settings 读取环境变量（数据源 token、DB 路径、日志等级） |
| `backend/app/db.py` | 建立 SQLAlchemy Engine（开启 WAL/foreign_keys pragma）、Session 工厂 |
| `backend/app/deps.py` | 提供 `get_session()`、`get_market_clock()` 等依赖项 |
| `backend/app/errors.py` | 错误码枚举、`AppException` 基类、FastAPI exception handler |
| `backend/app/scheduler/jobs.py` | 注册三地 cron 任务，每个任务调用 `DataPipeline.run(market)` |
| `backend/app/services/data_pipeline.py` | 编排：拉取 → 入库 → 校验 → 重算分位 → 生成信号 → 刷新定投执行 |
| `backend/app/valuation/percentile.py` | 纯函数：百分位计算（含相同值中位法） |
| `backend/app/valuation/tier.py` | 纯函数：温度 + boundaries → 档位标签 |
| `backend/app/services/dca_planner.py` | 定投联动：扫描计划 → 顺延非交易日 → 计算 multiplier → 写 DCAExecution |
| `backend/app/services/backtest_runner.py` | 单一阈值策略回测 |
| `backend/app/adapters/registry.py` | 按市场返回首选 + 回退顺序的适配器列表 |
| `frontend/src/api/client.ts` | 全局 fetch 封装：自动转 Decimal、错误统一抛出 |
| `frontend/src/utils/temperature.ts` | 温度值 → 色彩映射（与 SRS §7.2 总览页配色一致） |
| `scripts/init_history.py` | D10 历史初始化：分批拉取近 10 年所有指数数据，可断点续跑 |
| `scripts/seed_universe.py` | 启动后首次或更新 YAML 后导入 `index_meta` / `fund` 表 |
| `scripts/backup_db.py` | 使用 SQLite `.backup` API 进行一致性快照（区别于 `cp`） |

---

## 9. 测试策略

### 9.1 测试金字塔

```
            ┌──────────────────┐
           /   E2E (Playwright) \    ←  少量，仅总览/定投关键流
          ├─────────────────────┤
         /  API contract        \    ←  覆盖全部端点的 happy + 错误路径
        ├───────────────────────┤
       /  Integration (DB+pipe) \    ←  data_pipeline / signal_engine
      ├─────────────────────────┤
     /  Unit (pure functions)    \   ←  覆盖率目标 ≥ 90%
    └───────────────────────────┘
```

### 9.2 覆盖目标

| 层 | 目标 |
|---|---|
| 单元测试（valuation/, utils/） | 行覆盖 ≥ 90% |
| 集成测试（services/） | 关键路径必测：每日批处理（含失败回退）、信号生成、定投联动、非交易日顺延 |
| API 契约测试 | 每个端点至少 1 个 happy + 1 个错误用例 |
| E2E | 3 条流：① 加载总览 → 进详情 ② 创建定投 → 触发提醒 ③ 运行回测 |

### 9.3 关键测试用例（示例）

| 测试 | 验证点 |
|---|---|
| `test_percentile.py::test_ties_midrank` | 相同值取中位法的正确性 |
| `test_tier.py::test_boundary_extreme_low_upper_inclusive` | 边界 10% 归到"极度低估"还是"低估"（明确：< 10% 为极度低估，10% 起为低估） |
| `test_dca_multiplier.py::test_overridden_boundaries` | 用户自定义阈值后联动调整规则（D6 方案 A 核心） |
| `test_calendar_rollover.py::test_dca_skip_holiday_to_next_open_day` | 非交易日顺延，与 SRS §FR-5 表格三个用例对齐 |
| `test_data_pipeline.py::test_primary_source_failure_falls_back` | 数据源回退路径 |
| `test_data_pipeline.py::test_30d_audit_log_on_overwrite` | 回溯覆盖产生审计日志 |
| `test_signal_engine.py::test_no_signal_when_history_less_than_5y` | 历史 < 5 年指数不生成信号 |
| `test_backtest.py::test_buy_sell_pair_known_outcome` | 已知输入下的年化与回撤值 |

### 9.4 测试基础设施

- `pytest` + `pytest-asyncio` + `httpx.AsyncClient`（API 测试）
- 测试 DB：内存 SQLite，每个测试函数独立 schema
- 数据源 mock：每个 adapter 提供 `FakeAdapter`，固定返回 fixture 数据
- E2E：Playwright（headless Chromium），针对已 seed 的 demo 数据库

### 9.5 CI 流水线（建议）

- `pre-commit`：ruff（lint + format）、mypy、prettier、eslint
- GitHub Actions（如果未来上 GitHub）：
  1. 后端 `pytest`（unit + integration + api）
  2. 前端 `pnpm test` + `pnpm typecheck`
  3. E2E：跨容器拉起 backend + frontend，跑 Playwright

---

## 10. 部署与运维

### 10.1 Docker Compose（推荐部署形态）

`docker-compose.yml`：

```yaml
services:
  backend:
    build:
      context: ./backend
    container_name: vm-backend
    restart: unless-stopped
    ports:
      - "127.0.0.1:8000:8000"        # ★ 仅本地回环
    environment:
      - DB_PATH=/data/valuation.db
      - LOG_LEVEL=INFO
      - TUSHARE_TOKEN=${TUSHARE_TOKEN:-}
      - TZ=Asia/Shanghai
    volumes:
      - ./data:/data
      - ./logs:/logs

  frontend:
    build:
      context: ./frontend
    container_name: vm-frontend
    restart: unless-stopped
    ports:
      - "127.0.0.1:5173:80"
    depends_on:
      - backend
```

### 10.2 systemd 单进程部署（备选）

`/etc/systemd/system/valuation-monitor.service`：

```ini
[Unit]
Description=Valuation Monitor
After=network.target

[Service]
Type=simple
User=cindy
WorkingDirectory=/home/cindy/ValuationMonitor/backend
Environment="DB_PATH=/home/cindy/ValuationMonitor/data/valuation.db"
EnvironmentFile=/home/cindy/ValuationMonitor/.env
ExecStart=/home/cindy/ValuationMonitor/backend/.venv/bin/uvicorn app.main:app \
  --host 127.0.0.1 --port 8000
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

前端构建产物（`pnpm build`）由后端 `StaticFiles` 直接挂载到 `/`。

#### .env 路径解析（M2 修复）

`DB_PATH` 若为相对路径，`config.py` 应将其锚定到 `.env` 文件所在目录（项目根），而非进程 CWD。M1 当前实现锚定到 CWD，从 `backend/` 跑 `alembic upgrade head` 会找不到项目根的 `data/`，需要在 `.env` 中手填绝对路径作为临时方案。

#### 前端 .npmrc（M2 修复）

`frontend/.npmrc` 增加：
```
registry=https://registry.npmmirror.com
legacy-peer-deps=true
fetch-retries=10
fetch-timeout=300000
```
理由：
- 公网 `registry.npmjs.org` 在 CN 网络下不稳，M1 验证三次重试两次 ECONNRESET
- React 18 与部分依赖在严格 peer-dep 检查下报 ERESOLVE，本项目下 `legacy-peer-deps=true` 是安全选择

### 10.3 备份策略

- 触发：每日批处理任务完成后追加 `scripts/backup_db.py` 步骤
- 形式：SQLite Online Backup API（`.backup` 命令），输出至 `data/backups/valuation-YYYY-MM-DD.db`
- 保留：滚动保留最近 14 份；周末与月末各额外保留 1 份至 90 天

### 10.4 日志

- 后端使用 `structlog` 输出 JSON 行格式到 `logs/app.log`
- 单文件大小 ≤ 50 MB，自动按日 rotate，保留 30 份
- 关键字段：`ts`、`level`、`module`、`event`、`market`（如适用）、`index_code`、`error_code`

### 10.5 升级流程

1. 拉取新代码：`git pull`
2. 备份数据库：`python scripts/backup_db.py`
3. 应用迁移：`alembic upgrade head`
4. 重启：`docker compose up -d --build`（或 `systemctl restart valuation-monitor`）
5. 校验：访问 `/api/v1/health/pipeline` 确认调度可用

### 10.6 公网部署（可选附录）

> 默认 SRS D8 要求 localhost-only；若用户后续希望公网访问，按以下顺序加固：

1. 反向代理：Caddy（自动 HTTPS + Basic Auth）或 Nginx + Let's Encrypt
2. 应用层 Token：在 `Settings.AUTH_TOKEN` 启用后，所有非 `/health` 路由要求 `Authorization: Bearer <token>`
3. 防火墙：仅放行 80/443，禁止直连 8000
4. 持续审计：访问日志、错误率告警

---

## 11. 验收清单

### 11.1 文档完整性
- [ ] 第 1–10 章齐备
- [ ] A1–A10 决策落地于正文

### 11.2 API 完备性
- [ ] 第 3.2 节列出全部端点
- [ ] 关键端点（总览 / 估值序列 / 定投创建 / 阈值覆盖 / 回测 / 健康）给出请求与响应示例
- [ ] 错误响应统一结构与错误码表清晰

### 11.3 数据模型
- [ ] 13 张表的 SQL DDL 完整
- [ ] 13 个 SQLAlchemy 模型与 DDL 字段一一对应
- [ ] 关键索引声明明确

### 11.4 算法可读
- [ ] 百分位、温度、档位、信号、定投联动、回测均给出伪代码或函数签名
- [ ] D1 / D6 联动方案 A、D2 30 天回溯审计、D4 辅助指标范围在算法层有落实

### 11.5 目录骨架
- [ ] 后端 / 前端 / 脚本 / 数据 / 文档 五大区块完整
- [ ] 关键文件职责说明可指导后续编码

### 11.6 测试与部署
- [ ] 测试金字塔与覆盖目标明确
- [ ] 至少给出 Docker Compose 与 systemd 一种部署的可运行示例
- [ ] 备份与升级流程明确

---

## 附录 A. 技术依赖清单（拟选）

### 后端 `pyproject.toml`（拟）

```toml
[project]
name = "valuation-monitor-backend"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
  "fastapi>=0.110",
  "uvicorn[standard]>=0.27",
  "sqlalchemy>=2.0",
  "alembic>=1.13",
  "pydantic>=2.6",
  "pydantic-settings>=2.2",
  "apscheduler>=3.10",
  "akshare>=1.13",
  "yfinance>=0.2.40",
  "tushare>=1.4",       # 可选
  "pandas>=2.2",
  "pyyaml>=6.0",
  "structlog>=24.1",
  "httpx>=0.27",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.0",
  "pytest-asyncio>=0.23",
  "ruff>=0.4",
  "mypy>=1.10",
  "playwright>=1.44",
]
```

### 前端 `package.json`（拟）

```json
{
  "name": "valuation-monitor-frontend",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview",
    "typecheck": "tsc -b --noEmit",
    "lint": "eslint .",
    "test": "vitest"
  },
  "dependencies": {
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "react-router-dom": "^6.23.0",
    "@tanstack/react-query": "^5.40.0",
    "zustand": "^4.5.0",
    "echarts": "^5.5.0",
    "echarts-for-react": "^3.0.2",
    "decimal.js": "^10.4.0",
    "@radix-ui/react-dialog": "^1.0.5"
  },
  "devDependencies": {
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.0",
    "typescript": "^5.4.0",
    "vite": "^5.2.0",
    "vitest": "^1.6.0",
    "eslint": "^8.57.0"
  }
}
```

---

## 附录 B. M1 实施后修订汇总

下列修订与 SRS 附录 B 保持一一对齐，用于驱动 M2 的具体补丁列表：

| 编号 | 涉及章节 | 修订内容 | M2 补丁要点 |
|---|---|---|---|
| R1 | §5.2 数据源适配 | AkShare 估值历史接口切换到 `stock_index_pe_lg` / `stock_index_pb_lg` | 已在 M1 应用；本表只是文档同步 |
| R2 | §5.2 数据源适配 | 股息率快照接入：`AkshareAdapter._fetch_dividend_yield_snapshot` 调 `stock_zh_index_value_csindex` 取最近 20 个交易日，按日期 left-join 进 QuoteRow，每日累积。映射在 `_CSINDEX_CODE`；非中证编制（如深证创业板 50）try/except 跳过，best-effort | M3 末实装；约 1 年后过 R7 阈值（250 个交易日）即可计算分位 |
| R3 | §6.x 计算 | `data_window_note` 改用 `index_quote.MIN(date)` 判窗口 | 修改 `services/valuation_service.py::data_window_note`，签名增加 `Session` |
| R4 | §1 A0 / §10 部署 | Python 版本约束 ≥ 3.10 | `pyproject.toml` 已改；保留代码 3.10 兼容 |
| R5 | §10 部署 | `DB_PATH` 相对路径锚定到 `.env` 文件目录 | 改 `config.py` Settings：解析 `db_path` 时如非绝对路径，则相对 `.env` 文件所在目录 |
| R6 | §10 部署 | 新增 `frontend/.npmrc` | 新建文件，含 registry / legacy-peer-deps / retries |
| R7 | §5.2 数据源 / §6.1 估值 | 港美股仅快照 PE：YfinanceAdapter `Ticker.info.trailingPE` 写入当日；`recompute_for_index` 在 `len(pe_series) < MIN_DATAPOINTS_FOR_PERCENTILE (=250)` 时返回 None；前端 Overview MarketColumn 在市场全部 temperature=None 时显示 📷 快照角标 | M3 探索后落地；AkShare 港股估值接口在 CN 网络不可达；M4+ 接 Tushare Pro 补全 |
| R8 | §5.2 数据源（新增 TushareAdapter）/ Registry per-index 主源 | `TushareAdapter` 用 `index_daily` + `index_dailybasic` 合成 QuoteRow（close + pe_ttm + pb）；token 从 `Settings.tushare_token`（pydantic-settings）读，**不读 os.environ**。Tushare 服务端响应可能延迟/超时，`_get_pro` 设 `timeout=180`；空响应抛 `FetchFailure` 自动 fallback。`AdapterRegistry._PER_INDEX_PRIMARY` 注册 `{000001.SH, 399001.SZ, 399006.SZ}` → tushare；`fallbacks_for_index(market, code)` 优先 per-index，其次市场默认 | M5 末。三只综合指数因 csindex 不收录、lg 不覆盖、Tushare 收录，是 Tushare 唯一的"独家收益"指数。沪深300/中证500/上证50 lg 已完整覆盖，Tushare 仅作兜底 |
| R9 | §10 部署 / scheduler 模块 | **调度鲁棒性**：(a) `scheduler/jobs.py` 三个 cron job 用 `MISFIRE_GRACE_SECONDS = 6 * 3600` + `coalesce=True`：休眠/进程暂停 ≤ 6h 自动补一次；多次错过合并；(b) `scheduler/runner.py` `start_scheduler` 启动 daemon thread 调 `_catch_up_missed_runs`，对每启用市场查 `MAX(index_quote.created_at)`，若 `_should_catch_up(last, now, threshold_hours=CATCH_UP_THRESHOLD_HOURS=30)` 返回 True，立即同步触发 `_run_pipeline(market)`；纯函数 `_should_catch_up` 6 个用例覆盖（无数据/最近/超阈/边界/naive 时区/损坏 ISO）| M5 末。`misfire_grace_time` 选 6h 而非 24h，避免极端长时间唤醒触发重复运行；超过 30h 走启动补跑而非 cron 补跑 |

**文档结束**
