from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _find_project_root() -> Path:
    """向上查找含 .env / pyproject.toml 标记的项目根。

    用于 R5：让 db_path 等相对路径锚定到项目根而非进程 CWD。
    """
    here = Path(__file__).resolve()
    for parent in [here.parent, *here.parents]:
        # 项目根至少含 SRS.md 与 data/ 目录
        if (parent / "SRS.md").exists() or (parent / ".env").exists():
            return parent
    return here.parent


PROJECT_ROOT = _find_project_root()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(PROJECT_ROOT / ".env", PROJECT_ROOT.parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    db_path: str = Field(default="./data/valuation.db", alias="DB_PATH")
    host: str = Field(default="127.0.0.1", alias="HOST")
    port: int = Field(default=8000, alias="PORT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    tz: str = Field(default="Asia/Shanghai", alias="TZ")

    tushare_token: str | None = Field(default=None, alias="TUSHARE_TOKEN")

    schedule_a_enabled: bool = Field(default=True, alias="SCHEDULE_A_ENABLED")
    schedule_hk_enabled: bool = Field(default=False, alias="SCHEDULE_HK_ENABLED")
    schedule_us_enabled: bool = Field(default=False, alias="SCHEDULE_US_ENABLED")

    cors_allow_origins: str = Field(
        default="http://127.0.0.1:5173,http://localhost:5173",
        alias="CORS_ALLOW_ORIGINS",
    )

    @property
    def resolved_db_path(self) -> Path:
        """相对路径锚定到项目根（R5）；绝对路径原样使用。"""
        p = Path(self.db_path).expanduser()
        if not p.is_absolute():
            p = PROJECT_ROOT / p
        return p.resolve()

    @property
    def sqlalchemy_url(self) -> str:
        return f"sqlite:///{self.resolved_db_path}"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_allow_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
