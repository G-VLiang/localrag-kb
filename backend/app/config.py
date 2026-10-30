from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置，全部支持 .env 覆盖。"""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # 基础
    app_name: str = "LocalRAG KB"
    api_v1_prefix: str = "/api/v1"
    debug: bool = True

    # 数据库（默认走 Docker 内的 pgvector 服务）
    database_url: str = "postgresql+psycopg2://kb:kb_password@localhost:5432/kb"

    # JWT
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24
    refresh_token_expire_days: int = 7

    # Embedding
    embedding_provider: str = "local"  # local | openai
    embedding_model: str = "bge-m3"
    embedding_local_path: str = "BAAI/bge-m3"
    # 云 API（embedding_provider=openai 时使用）
    embedding_api_base: str = ""
    embedding_api_key: str = ""

    # LLM
    llm_provider: str = "ollama"  # ollama | openai
    llm_model: str = "qwen2.5:7b"
    ollama_base_url: str = "http://localhost:11434"
    # 云 API（llm_provider=openai 时使用）
    llm_api_base: str = ""
    llm_api_key: str = ""

    # 检索
    chunk_size: int = 800
    chunk_overlap: int = 120
    top_k: int = 5
    use_rerank: bool = False

    # 分享链接生成的站点地址
    public_base_url: str = "http://localhost:5173"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
