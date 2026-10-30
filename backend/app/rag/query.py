"""Query 改写/扩展：用 LLM 生成多路检索查询以提升召回；任何失败安全回退为原查询。"""

from __future__ import annotations

import json
import re
from typing import List

import httpx

from app.config import settings

_SYSTEM = (
    "你是检索查询优化助手。请把用户问题改写成语义相近、但措辞或角度不同的检索查询，"
    "用于提升关键词与向量召回。只输出 JSON 字符串数组，不要解释。"
)


def _call_llm(user_prompt: str) -> str:
    messages = [
        {"role": "system", "content": _SYSTEM},
        {"role": "user", "content": user_prompt},
    ]
    if settings.llm_provider == "openai":
        headers = {"Authorization": f"Bearer {settings.llm_api_key}"}
        with httpx.Client(base_url=settings.llm_api_base, timeout=60) as c:
            r = c.post(
                "/chat/completions",
                json={"model": settings.llm_model, "messages": messages, "temperature": 0.3},
                headers=headers,
            )
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]
    with httpx.Client(base_url=settings.ollama_base_url, timeout=60) as c:
        r = c.post(
            "/api/chat",
            json={"model": settings.llm_model, "messages": messages, "stream": False},
        )
        r.raise_for_status()
        return r.json()["message"]["content"]


def _parse_queries(raw: str, n: int) -> List[str]:
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return [str(x).strip() for x in data if str(x).strip()][:n]
    except Exception:
        pass
    lines = [re.sub(r"^[\s\-*\d.、)]+", "", ln).strip() for ln in raw.splitlines()]
    return [ln for ln in lines if ln][:n]


def rewrite_queries(query: str, n: int = 3) -> List[str]:
    """返回 [原查询, 改写1, 改写2, ...]；失败时仅返回 [原查询]。"""
    if n <= 0 or not query.strip():
        return [query]
    prompt = f"用户问题：{query}\n请给出 {n} 个语义相近但措辞不同的检索查询，仅返回 JSON 字符串数组。"
    try:
        raw = _call_llm(prompt)
        alts = _parse_queries(raw, n)
        out = [query]
        for a in alts:
            if a and a != query and a not in out:
                out.append(a)
        return out
    except Exception:
        return [query]
