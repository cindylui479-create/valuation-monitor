# ValuationMonitor

A 股 / 港股 / 美股各类型指数的估值监测工具。详见：

- [`SRS.md`](./SRS.md) — 软件需求规格（含附录 B 累计修订 R1–R9）
- [`DESIGN.md`](./DESIGN.md) — 系统设计

当前进度：**M1–M5 全部交付**，24 只指数（A 14 / HK 4 / US 6），含信号引擎、定投联动、回测、CSV 导出、运行历史。

## 快速开始

### 1. 环境

需要 Python **3.10+**（M1 验证后从 3.11 放宽，参见 SRS R4），Node **20+**。

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 2. 初始化数据库与种子

```bash
# 从项目根目录执行
cp .env.example .env
mkdir -p data logs

# 应用迁移
cd backend
alembic upgrade head

# 导入指数池（24 只：A 14 + HK 4 + US 6）
python -m scripts.seed_universe

# 历史初始化：分市场拉取近 10 年数据
python -m scripts.init_history --market A --years 10   # ~12 分钟
python -m scripts.init_history --market HK --years 10  # ~15 秒
python -m scripts.init_history --market US --years 10  # ~15 秒
```

### 3. 启动后端（保持运行接收每日批处理）

```bash
cd backend
# 开发模式（前台）
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
# 或后台
nohup .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 >> ../logs/uvicorn.log 2>&1 &
```

访问 http://127.0.0.1:8000/docs 看 OpenAPI 文档。

### 4. 启动前端

```bash
cd frontend
npm install --legacy-peer-deps   # frontend/.npmrc 已配 npmmirror 镜像
nohup npx vite --host 127.0.0.1 --port 5173 >> ../logs/vite.log 2>&1 &
```

访问 http://127.0.0.1:5173。

## 页面索引

| 路径 | 功能 |
|---|---|
| `/` | 总览：三地分栏热力图/表格，列头排序，档位筛选 |
| `/indices/:code` | 详情：价格+PE 双轴图、PB 子图、当前信号、信号时间轴、跟踪 ETF |
| `/watchlist` | 自选 |
| `/signals` | 信号列表（今日 / 历史） |
| `/dca` | 定投：未来 7 天提醒 + 计划 CRUD + 累计统计 |
| `/backtest` | 回测：三策略对比（阈值/定投/买入持有）+ NAV 曲线 |
| `/settings` | 偏好 / 调度时刻 / 数据源健康 / **批处理运行历史**（30 天） |

## 数据来源

| 市场 | 价格 | PE / PB | 股息率 |
|---|---|---|---|
| A 股（8 lg + 3 综合 + 3 主题） | akshare / Tushare | lg / Tushare / csindex 快照 | csindex 快照（20 天滚动累积） |
| 港股（4 只） | yfinance | yfinance Ticker.info 快照（^HSI/^HSCE 走 EWH/FXI 代理） | 快照 |
| 美股（6 只 ETF） | yfinance | yfinance Ticker.info 快照 | 快照 |

> 港美股 PE/PB 仅为当日快照（SRS R7）；待 1 年累积或 Tushare 升级后激活历史分位。

## 调度（每日自动更新）

后端启动时 APScheduler 注册三地 cron（**北京时间**）：

| 市场 | 时刻 | 实际数据 |
|---|---|---|
| A 股 | **16:30** | 当日收盘 |
| 港股 | **17:30** | 当日收盘 |
| 美股 | **次日 07:00** | 前一交易日收盘 |

### 鲁棒性（SRS R9，M5 末加入）

| 场景 | 行为 |
|---|---|
| 调度时刻进程被休眠 ≤ 6 小时 | `misfire_grace_time=6h` 自动补跑一次 |
| 多次错过（如机器睡 2 天） | `coalesce=True` 合并为单次执行 |
| 进程刚启动且最近一次入库 > **30 小时**前 | `runner._catch_up_missed_runs` 在 daemon thread 立即触发一次补跑 |
| 服务关闭期间错过的调度 | 服务重启后被上面机制自动覆盖 |

### 手动触发（任何时候都可以）

```bash
cd backend
# 单市场一次性补抓
.venv/bin/python -m scripts.init_history --market A --years 1

# 或调用今日 pipeline（含信号 + 定投刷新）
.venv/bin/python -c "
from app.db import SessionLocal
from app.services import data_pipeline
for m in ('A','HK','US'):
    with SessionLocal() as s:
        r = data_pipeline.run_for_market(s, market=m)
        print(m, r.success, r.rows_upserted)
"
```

## 部署

```bash
docker compose up -d --build
```

仅 `127.0.0.1` 监听（参见 SRS D8）。

## 测试

```bash
cd backend
.venv/bin/pytest                # 全部 64 个用例
.venv/bin/pytest tests/unit     # 单元（54）
.venv/bin/pytest tests/integration  # 集成（10）
```

## 文档对照表（M5 末状态）

| 文档 | 内容 |
|---|---|
| `SRS.md` | 10 章主体 + 附录 B（R1–R9 修订汇总） |
| `DESIGN.md` | 11 章主体 + 附录 B（R1–R9 实现细节） |
| `README.md` | 本文，部署与运行 |
