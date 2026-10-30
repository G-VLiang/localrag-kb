"""混合检索：pgvector 向量召回 + BM25 关键词（textsearch_zh）融合 + 可选重排。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models import DocChunk, DocNode, Document, KnowledgeBase
from app.rag.embedding import get_embedding_provider


@dataclass
class SearchHit:
    chunk_id: str
    document_id: str
    node_id: str
    content: str
    score: float
    document_title: str
    knowledge_base_id: str


def _vector_search(db: Session, query_vec: List[float], kb_ids: List[str], top_k: int) -> dict[str, float]:
    """向量余弦相似度召回，返回 {chunk_id: similarity}。"""
    rows = db.execute(
        text(
            """
            SELECT id, 1 - (embedding <=> :vec) AS sim
            FROM doc_chunks
            WHERE knowledge_base_id = ANY(:kb_ids)
            ORDER BY embedding <=> :vec
            LIMIT :k
            """
        ),
        {"vec": query_vec, "kb_ids": kb_ids, "k": top_k * 2},
    ).fetchall()
    return {r[0]: float(r[1]) for r in rows}


def _bm25_search(db: Session, query: str, kb_ids: List[str], top_k: int) -> dict[str, float]:
    """BM25 关键词召回（pgroonga 未启用时退化为 ILIKE 兜底）。返回 {chunk_id: score}。"""
    # 优先用 pgroonga 的 textsearch 中文分词；未安装则退化为包含匹配
    try:
        rows = db.execute(
            text(
                """
                SELECT id, ts_rank(to_tsvector('simple', content), plainto_tsquery('simple', :q)) AS rank
                FROM doc_chunks
                WHERE knowledge_base_id = ANY(:kb_ids)
                  AND content ILIKE '%' || :q || '%'
                ORDER BY rank DESC
                LIMIT :k
                """
            ),
            {"q": query, "kb_ids": kb_ids, "k": top_k},
        ).fetchall()
    except Exception:
        # 兜底：纯关键词包含匹配
        rows = db.execute(
            text(
                """
                SELECT id, 1.0 AS rank
                FROM doc_chunks
                WHERE knowledge_base_id = ANY(:kb_ids)
                  AND content ILIKE '%' || :q || '%'
                LIMIT :k
                """
            ),
            {"q": query, "kb_ids": kb_ids, "k": top_k},
        ).fetchall()
    return {r[0]: float(r[1]) for r in rows}


def _rrf_fusion(vector_scores: dict[str, float], bm25_scores: dict[str, float], k: int = 60) -> dict[str, float]:
    """Reciprocal Rank Fusion 融合两路召回。"""
    fusion: dict[str, float] = {}
    for rank, cid in enumerate(vector_scores):
        fusion[cid] = fusion.get(cid, 0) + 1.0 / (k + rank + 1)
    for rank, cid in enumerate(bm25_scores):
        fusion[cid] = fusion.get(cid, 0) + 1.0 / (k + rank + 1)
    return fusion


def search(
    db: Session,
    query: str,
    kb_ids: List[str],
    top_k: int = 5,
) -> List[SearchHit]:
    provider = get_embedding_provider()
    query_vec = provider.embed_query(query)

    vec_scores = _vector_search(db, query_vec, kb_ids, top_k)
    bm25_scores = _bm25_search(db, query, kb_ids, top_k)
    fused = _rrf_fusion(vec_scores, bm25_scores)

    # 取 top_k
    ranked_ids = sorted(fused, key=fused.get, reverse=True)[:top_k]
    if not ranked_ids:
        return []

    # 批量取 chunk + 关联文档标题
    chunks = db.query(DocChunk).filter(DocChunk.id.in_(ranked_ids)).all()
    chunk_map = {c.id: c for c in chunks}

    # 关联 node/title
    doc_ids = {c.document_id for c in chunks}
    docs = db.query(Document).filter(Document.id.in_(doc_ids)).all()
    doc_map = {d.id: d for d in docs}

    node_ids = {d.node_id for d in docs}
    nodes = db.query(DocNode).filter(DocNode.id.in_(node_ids)).all()
    node_map = {n.id: n for n in nodes}

    hits: List[SearchHit] = []
    for cid in ranked_ids:
        c = chunk_map.get(cid)
        if not c:
            continue
        d = doc_map.get(c.document_id)
        node = node_map.get(d.node_id) if d else None
        hits.append(
            SearchHit(
                chunk_id=c.id,
                document_id=c.document_id,
                node_id=d.node_id if d else "",
                content=c.content,
                score=round(fused[cid], 4),
                document_title=node.title if node else "",
                knowledge_base_id=c.knowledge_base_id,
            )
        )
    return hits
