from __future__ import annotations# 开启类型提示

from pydantic import BaseModel, Field, field_validator, ConfigDict, ValidationError
from dotenv import load_dotenv
import os
from pathlib import Path


load_dotenv()


class ConfigurationError(RuntimeError):
    """用户可修复的配置错误。"""


class ProviderConfig(BaseModel):
    model_config = ConfigDict(validate_default=True)# 默认不校验环境变量，开启校验默认值是否符合要求
    api_key: str = Field(default_factory = lambda: os.getenv("OPENAI_API_KEY", ""))# 每次实例化时都从环境变量中获取
    api_base: str = Field(default_factory = lambda: os.getenv(
        "OPENAI_API_BASE", 
        "https://api.openai.com/v1",
    ))
    model: str = Field(default_factory = lambda: os.getenv("MODEL_NAME", "qwen3.8-27b"))
    temperature: float = Field(default_factory = lambda: float(os.getenv("MODEL_TEMPERATURE", "0.7")))
    max_tokens: int = Field(default_factory = lambda: int(os.getenv("MODEL_MAX_TOKENS", "4096")), ge=1)#最小值校验
    timeout_seconds: int = Field(default_factory = lambda: int(os.getenv("MODEL_TIMEOUT_SECONDS", "120")), ge=0)#最小值校验

    @field_validator("api_base")# 校验api_base是否通过以下函数
    @classmethod
    def validate_api_base(cls, v: str) -> str:
   
        if any(char in v for char in ["[", "]"]):
            raise ValueError("api_base不能包含占位符")
        
        if v.endswith("/"):
            return v[:-1]

        return v 


class AppConfig(BaseModel):
    provider: ProviderConfig = Field(default_factory=ProviderConfig)
    workspace_dir: Path = Field(
        default_factory=lambda: Path(os.getenv("WORKSPACE_DIR", "./workspace")).resolve()
    )

    @property
    def db_path(self) -> Path:
        return self.workspace_dir / "sessions.db"

    @property
    def memory_dir(self) -> Path:
        return self.workspace_dir / "memory"

    def ensure_dirs(self) -> None:
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self.memory_dir.mkdir(parents=True, exist_ok=True)

def load_config() -> AppConfig:
    load_dotenv()
    try:
        cfg = AppConfig()
    except ValidationError as exc:
        raise ConfigurationError(f"配置无效：\n{exc}") from exc
    if not cfg.provider.api_key:
        raise ConfigurationError("未设置 OPENAI_API_KEY")
    cfg.ensure_dirs()
    return cfg