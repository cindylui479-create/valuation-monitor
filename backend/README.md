# Backend

FastAPI + SQLAlchemy + APScheduler。详见根目录 [`README.md`](../README.md) 与 [`../DESIGN.md`](../DESIGN.md)。

## 常用命令

```bash
# 安装
pip install -e ".[dev]"

# 迁移
alembic revision --autogenerate -m "msg"
alembic upgrade head

# 启动
uvicorn app.main:app --reload

# 种子
python -m scripts.seed_universe
python -m scripts.init_history --market A --years 10

# 测试
pytest
```
