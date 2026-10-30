"""RAG 纯函数单测：分词/词法分、切片、余弦、MMR、锚点去重、CE 回退。"""

import importlib.util

from app.rag.chunker import split_text
from app.rag.retriever import (
    SearchHit,
    _cos,
    _cross_encoder_scores,
    _mmr_select,
    _select_non_overlapping,
)
from app.rag.tokenizer import lexical_score, tokenize


def test_tokenize_mixed():
    tokens = tokenize("深度学习模型 DeepLearning 123")
    assert "deeplearning" in tokens
    assert "123" in tokens
    assert any("深" in t or "学习" in t for t in tokens)


def test_lexical_score_bounds_and_ordering():
    s1 = lexical_score("深度学习", "深度学习是机器学习的重要分支，依赖神经网络")
    s2 = lexical_score("深度学习", "今天天气晴朗，适合散步")
    assert 0.0 <= s1 <= 1.0
    assert 0.0 <= s2 <= 1.0
    assert s1 > s2


def test_chunker_size_and_overlap():
    text = "。".join(
        [f"这是第{i}段关于企业知识库的内容，用于测试切片连续性与重叠是否正确保留语义。" for i in range(40)]
    )
    chunks = split_text(text, chunk_size=200, chunk_overlap=40)
    assert chunks
    assert all(len(c) <= 200 for c in chunks)
    ov = 40
    for i in range(len(chunks) - 1):
        assert chunks[i + 1].startswith(chunks[i][-ov:])


def test_cosine():
    assert abs(_cos([1, 0], [1, 0]) - 1.0) < 1e-9
    assert abs(_cos([1, 0], [0, 1])) < 1e-9
    assert _cos([], [1, 0]) == 0.0


def test_mmr_diversity_vs_relevance():
    items = [
        {"cid": "A", "rel": 0.90, "emb": [1.0, 0.0]},
        {"cid": "B", "rel": 0.85, "emb": [1.0, 0.0]},
        {"cid": "C", "rel": 0.50, "emb": [0.0, 1.0]},
    ]
    assert [x["cid"] for x in _mmr_select(items, 2, 0.7)] == ["A", "C"]
    assert [x["cid"] for x in _mmr_select(items, 2, 0.99)] == ["A", "B"]


def test_select_non_overlapping():
    anchors = [(0, "d1", 5), (1, "d1", 6), (2, "d1", 9)]
    assert _select_non_overlapping(anchors, 1) == [0, 2]


def test_cross_encoder_fallback_without_dep():
    if importlib.util.find_spec("sentence_transformers") is None:
        assert _cross_encoder_scores("q", ["a", "b"]) is None


def test_search_hit_fields():
    fields = SearchHit.__dataclass_fields__
    assert {"seq", "node_title", "context"} <= set(fields)
