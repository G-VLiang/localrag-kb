"""LLM 生成：Ollama 本地优先，支持 OpenAI 兼容云 API。"""

from __future__ import annotations

from typing import List

import httpx

from app.config import settings
from app.rag.retriever import SearchHit

SYSTEM_PROMPT = """你是一个知识库问答助手。请基于提供的参考资料回答用户问题。

要求：
1. 只依据参考资料回答，不要编造资料中没有的内容
2. 如果资料不足以回答，明确说明"根据现有资料无法回答"
3. 回答简洁、准确、条理清晰
4. 在回答中标注引用来源编号，如 [1]、[2]
"""


def build_prompt(query: str, hits: List[SearchHit]) -> str:
    ctx_parts = []
    for i, h in enumerate(hits, 1):
        ctx_parts.append(f"[{i}] 《{h.document_title}》\n{h.content}")
    context = "\n\n".join(ctx_parts)
    return f"参考资料：\n{context}\n\n用户问题：{query}\n\n请回答："


def _call_ollama(messages: List[dict]) -> str:
    with httpx.Client(base_url=settings.ollama_base_url, timeout=300) as client:
        r = client.post(
            "/api/chat",
            json={"model": settings.llm_model, "messages": messages, "stream": False},
        )
        r.raise_for_status()
        return r.json()["message"]["content"]


def _call_openai(messages: List[dict]) -> str:
    headers = {"Authorization": f"Bearer {settings.llm_api_key}"}
    with httpx.Client(base_url=settings.llm_api_base, timeout=300) as client:
        r = client.post(
            "/chat/completions",
            json={"model": settings.llm_model, "messages": messages},
            headers=headers,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]


def generate_answer(query: str, hits: List[SearchHit]) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_prompt(query, hits)},
    ]
    if settings.llm_provider == "openai":
        return _call_openai(messages)
    return _call_ollama(messages)
