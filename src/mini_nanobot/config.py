from __future__ import annotations# 开启类型提示

from pydantic import BaseModel
from dotenv import load_dotenv
import os
from pydantic import Field, field_validator, ConfigDict



load_dotenv()


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