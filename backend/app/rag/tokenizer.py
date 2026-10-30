"""中文友好的分词与词法相关性打分（无强制外部依赖，jieba 可选增强）。

用于 RAG 重排阶段的词法信号：对中文按词（jieba）或单字切分、对英文按词切分，
再计算查询与片段的重叠得分，弥补纯向量检索在关键词/短查询上的不足。
"""

from __future__ import annotations

import re
from typing import List

_CJK = re.compile(r"[一-鿿]")
_LATIN = re.compile(r"[a-z0-9]+")

try:
    import jieba  # type: ignore

    _HAS_JIEBA = True
except Exception:  # pragma: no cover - 依赖可选
    _HAS_JIEBA = False


def tokenize(text: str) -> List[str]:
    """返回去空后的 token 列表：英文/数字按词，中文优先 jieba、否则按字。"""
    if not text:
        return []
    text = text.lower()
    tokens: List[str] = [m for m in _LATIN.findall(text)]
    cjk = "".join(_CJK.findall(text))
    if cjk:
        if _HAS_JIEBA:
            tokens.extend(t for t in jieba.cut(cjk) if t.strip())
        else:
            tokens.extend(cjk)  # 单字退化，足够做重叠打分
    return [t for t in tokens if t.strip()]


def lexical_score(query: str, text: str) -> float:
    """词法相关性打分，范围 [0, 1]。

    结合「查询词在文档中的覆盖率」与「Jaccard 重叠系数」：
    - 覆盖率对长文档做词频饱和（上限 3），避免长文刷分；
    - 重叠系数衡量查询与文档的词集合重合度。
    """
    qt = tokenize(query)
    dt = tokenize(text)
    if not qt or not dt:
        return 0.0
    qset = set(qt)
    hit = sum(min(dt.count(t), 3) for t in qset)
    coverage = min(1.0, hit / len(qt))
    dset = set(dt)
    union = qset | dset
    overlap = len(qset & dset) / len(union) if union else 0.0
    return round(0.7 * coverage + 0.3 * overlap, 4)
