"""混合检索：pgvector 向量召回 + BM25 关键词召回 + RRF 融合 + 词法重排（中文友好）。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.models import DocChunk, DocNode, Document, KnowledgeBase
from app.rag.embedding import get_embedding_provider
from app.rag.tokenizer import lexical_score


@dataclass
class SearchHit:
    chunk_id: str
    document_id: str
    node_id: str
    content: str
    score: float
    document_title: str
    knowledge_base_id: str
    seq: int = 0
    node_title: str = ""


def _vector_search(db: Session, query_vec: List[float], kb_ids: List[str], top_k: int) -> Dict[str, float]:
    """向量余弦相似度召回（扩大召回窗口供后续重排）。返回 {chunk_id: sim}。"""
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
        {"vec": query_vec, "kb_ids": kb_ids, "k": top_k * 4},
    ).fetchall()
    return {r[0]: float(r[1]) for r in rows}


def _bm25_search(db: Session, query: str, kb_ids: List[str], top_k: int) -> Dict[str, float]:
    """BM25 关键词召回（pgroonga 未启用时退化为 ILIKE 包含匹配）。返回 {chunk_id: score}。"""
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
            {"q": query, "kb_ids": kb_ids, "k": top_k * 4},
        ).fetchall()
    except Exception:
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
            {"q": query, "kb_ids": kb_ids, "k": top_k * 4},
        ).fetchall()
    return {r[0]: float(r[1]) for r in rows}


def _rrf_fusion(vector_scores: Dict[str, float], bm25_scores: Dict[str, float], k: int = 60) -> Dict[str, float]:
    """Reciprocal Rank Fusion 融合两路召回。"""
    fusion: Dict[str, float] = {}
    for rank, cid in enumerate(sorted(vector_scores, key=vector_scores.get, reverse=True)):
        fusion[cid] = fusion.get(cid, 0) + 1.0 / (k + rank + 1)
    for rank, cid in enumerate(sorted(bm25_scores, key=bm25_scores.get, reverse=True)):
        fusion[cid] = fusion.get(cid, 0) + 1.0 / (k + rank + 1)
    return fusion


def search(db: Session, query: str, kb_ids: List[str], top_k: int = 5) -> List[SearchHit]:
    provider = get_embedding_provider()
    query_vec = provider.embed_query(query)

    vec_scores = _vector_search(db, query_vec, kb_ids, top_k)
    bm25_scores = _bm25_search(db, query, kb_ids, top_k)
    fused = _rrf_fusion(vec_scores, bm25_scores)

    # 候选：融合分数前 N（扩大召回再重排）
    candidates = sorted(fused, key=fused.get, reverse=True)[: max(top_k * 4, 20)]
    if not candidates:
        return []

    chunks = db.query(DocChunk).filter(DocChunk.id.in_(candidates)).all()
    chunk_map = {c.id: c for c in chunks}

    doc_ids = {c.document_id for c in chunks}
    docs = db.query(Document).filter(Document.id.in_(doc_ids)).all()
    doc_map = {d.id: d for d in docs}

    node_ids = {d.node_id for d in docs}
    nodes = db.query(DocNode).filter(DocNode.id.in_(node_ids)).all()
    node_map = {n.id: n for n in nodes}

    max_fused = max(fused.values()) or 1.0
    scored = []
    for cid in candidates:
        c = chunk_map.get(cid)
        if not c:
            continue
        d = doc_map.get(c.document_id)
        node = node_map.get(d.node_id) if d else None
        fused_norm = fused[cid] / max_fused
        # 重排：融合分（向量+BM25）与词法相关性（中文友好）各占一半
        final = (0.5 * fused_norm + 0.5 * lexical_score(query, c.content)) if settings.use_rerank else fused_norm
        scored.append((final, cid, c, d, node))

    scored.sort(key=lambda x: x[0], reverse=True)

    hits: List[SearchHit] = []
    for final, _cid, c, d, node in scored[:top_k]:
        title = node.title if node else ""
        hits.append(
            SearchHit(
                chunk_id=c.id,
                document_id=c.document_id,
                node_id=d.node_id if d else "",
                content=c.content,
                score=round(final, 4),
                document_title=title,
                knowledge_base_id=c.knowledge_base_id,
                seq=c.seq if hasattr(c, "seq") else 0,
                node_title=title,
            )
        )
    return hits
