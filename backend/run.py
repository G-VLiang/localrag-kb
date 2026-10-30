"""LocalRAG KB — 本地智能 RAG 知识库（FastAPI 后端）"""

from fastapi import FastAPI

# 导入 models 确保注册到 Base.metadata
import app.models  # noqa: F401


def create_app() -> FastAPI:
    from app.main import app

    return app


app = create_app()
