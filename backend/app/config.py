from functools import lru_cache
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置，全部支持 .env 覆盖。

    生产环境（debug=False）下，JWT_SECRET 必须显式设置，否则启动即失败。
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # 基础
    app_name: str = "LocalRAG KB"
    api_v1_prefix: str = "/api/v1"
    # 生产默认关闭调试；开发态用 DEBUG=true 开启
    debug: bool = False

    # 数据库（默认走 Docker 内的 pgvector 服务）
    database_url: str = "postgresql+psycopg2://kb:kb_password@localhost:5432/kb"

    # JWT（生产环境必须显式设置 JWT_SECRET，否则启动即报错）
    jwt_secret: str = ""
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
    use_rerank: bool = True  # 融合召回后做词法重排（中文友好），可设 false 退回纯 RRF

    # 检索增强（RAG 深挖）
    use_mmr: bool = True  # MMR 多样性重排，减少重复片段
    mmr_lambda: float = 0.7  # 相关性 vs 多样性（越大越偏相关性）
    parent_expand: bool = True  # 小切片召回 + 邻块上下文扩展（Small-to-Big）
    parent_window: int = 1  # 左右各扩展几个邻块
    max_context_chars: int = 6000  # 组装上下文总字符预算
    rerank_provider: str = "lexical"  # lexical | cross-encoder
    rerank_model: str = "BAAI/bge-reranker-base"

    # Query 改写/扩展（LLM 生成多路查询；需 LLM 可用，失败安全回退）
    use_query_rewrite: bool = False
    query_rewrite_count: int = 3

    # 跨域白名单（逗号分隔）；留空则开发态放开为 *（不携带凭证）
    cors_origins: str = ""
    # 分享链接生成的站点地址
    public_base_url: str = "http://localhost:5173"

    @model_validator(mode="after")
    def _validate_production(self) -> "Settings":
        insecure = {"", "change-me-in-production", "changeme", "secret"}
        if not self.debug:
            if self.jwt_secret in insecure:
                raise ValueError(
                    "生产环境必须在 .env 中设置强随机 JWT_SECRET，"
                    "当前为空或使用不安全默认值，已拒绝启动。"
                )
        else:
            # 开发态：无密钥时注入仅本地调试用的默认值，切勿用于生产
            if not self.jwt_secret:
                self.jwt_secret = "dev-only-insecure-secret-do-not-use-in-prod"
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
