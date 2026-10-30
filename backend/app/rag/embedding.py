"""Embedding provider：本地 sentence-transformers(bge-m3) 优先，支持 Ollama 与 OpenAI 兼容云 API。"""

from __future__ import annotations

from typing import List

import httpx

from app.config import settings


def _apply_hf_mirror() -> None:
    """国内网络直连 HuggingFace 通常超时，配置镜像端点（HF_ENDPOINT）。

    另外必须禁用 xet 协议：hf-xet 在部分国内网络下会挂起导致下载不返回。
    """
    import os

    os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
    os.environ.setdefault("HF_HUB_DISABLE_XET", "1")


class EmbeddingProvider:
    def embed(self, texts: List[str]) -> List[List[float]]:
        raise NotImplementedError

    def embed_query(self, text: str) -> List[float]:
        return self.embed([text])[0]


class LocalSentenceTransformerProvider(EmbeddingProvider):
    """本地加载 bge-m3（首次调用懒加载，避免启动过慢）。"""

    _model = None

    @property
    def model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError:
                raise RuntimeError(
                    "本地 Embedding 依赖未安装。请在后端容器内运行："
                    "pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements-rag.txt"
                    "；或将 .env 的 EMBEDDING_PROVIDER 设为 ollama / openai"
                )
            _apply_hf_mirror()
            self._model = SentenceTransformer(settings.embedding_local_path)
        return self._model

    def embed(self, texts: List[str]) -> List[List[float]]:
        # normalize_embeddings=True 便于余弦相似度
        vecs = self.model.encode(texts, normalize_embeddings=True)
        return [v.tolist() for v in vecs]


class OllamaEmbeddingProvider(EmbeddingProvider):
    """走 Ollama 的 /api/embed 接口。"""

    def embed(self, texts: List[str]) -> List[List[float]]:
        out: List[List[float]] = []
        with httpx.Client(base_url=settings.ollama_base_url, timeout=120) as client:
            for t in texts:
                r = client.post("/api/embed", json={"model": settings.embedding_model, "input": t})
                r.raise_for_status()
                emb = r.json()["embeddings"][0]
                out.append(emb)
        return out


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI 兼容云 API（通义/DeepSeek/OpenAI 等）。"""

    def embed(self, texts: List[str]) -> List[List[float]]:
        headers = {"Authorization": f"Bearer {settings.embedding_api_key}"}
        with httpx.Client(base_url=settings.embedding_api_base, timeout=60) as client:
            r = client.post(
                "/embeddings",
                json={"model": settings.embedding_model, "input": texts},
                headers=headers,
            )
            r.raise_for_status()
            data = r.json()["data"]
            data.sort(key=lambda d: d["index"])
            return [d["embedding"] for d in data]


def get_embedding_provider() -> EmbeddingProvider:
    p = settings.embedding_provider
    if p == "ollama":
        return OllamaEmbeddingProvider()
    if p == "openai":
        return OpenAIEmbeddingProvider()
    # 默认 local
    return LocalSentenceTransformerProvider()
