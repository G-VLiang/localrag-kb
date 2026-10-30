"""Query 改写/扩展单测（mock LLM，不依赖网络）。"""

from app.rag import query as qmod


def test_rewrite_queries_parses_json(monkeypatch):
    monkeypatch.setattr(qmod, "_call_llm", lambda p: '["安装步骤", "如何安装"]')
    out = qmod.rewrite_queries("怎么装", 2)
    assert out[0] == "怎么装"
    assert "安装步骤" in out
    assert "如何安装" in out


def test_rewrite_queries_fallback_on_error(monkeypatch):
    def boom(_p):
        raise RuntimeError("llm down")

    monkeypatch.setattr(qmod, "_call_llm", boom)
    assert qmod.rewrite_queries("x", 3) == ["x"]


def test_rewrite_queries_zero_count():
    assert qmod.rewrite_queries("x", 0) == ["x"]
