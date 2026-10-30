"""混合检索：向量 + BM25 + RRF + 精排(词法/可选 cross-encoder) + MMR 多样性 + 父块上下文扩展。"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Sequence

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.models import DocChunk, DocNode, Document
from app.rag.embedding import get_embedding_provider
from app.rag.tokenizer import lexical_score

# cross-encoder 模型缓存（懒加载）
_CE_CACHE: Dict[str, object] = {}


@dataclass
class SearchHit:
    chunk_id: str
    document_id: str
    node_id: str
    content: str  # 命中锚点片段内容（用于引用展示）
    score: float
    document_title: str
    knowledge_base_id: str
    seq: int = 0
    node_title: str = ""
    heading: str = ""  # 命中片段所处标题路径
    context: str = ""  # 父块扩展后的上下文（供 LLM 使用，缺省等于 content）


def _cos(a: Sequence[float], b: Sequence[float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def _minmax(vals: List[float]) -> List[float]:
    lo, hi = min(vals), max(vals)
    if hi - lo < 1e-9:
        return [0.5 for _ in vals]
    return [(v - lo) / (hi - lo) for v in vals]


def _vector_search(db: Session, query_vec: List[float], kb_ids: List[str], top_k: int) -> Dict[str, float]:
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
    """BM25 关键词召回（pgroonga 未启用时退化为 ILIKE 包含匹配）。"""
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
    fusion: Dict[str, float] = {}
    for rank, cid in enumerate(sorted(vector_scores, key=vector_scores.get, reverse=True)):
        fusion[cid] = fusion.get(cid, 0) + 1.0 / (k + rank + 1)
    for rank, cid in enumerate(sorted(bm25_scores, key=bm25_scores.get, reverse=True)):
        fusion[cid] = fusion.get(cid, 0) + 1.0 / (k + rank + 1)
    return fusion


def _cross_encoder_scores(query: str, texts: List[str]) -> List[float] | None:
    """可选 cross-encoder 精排；依赖缺失/加载失败时返回 None（调用方回退词法重排）。"""
    if not texts:
        return []
    try:
        from sentence_transformers import CrossEncoder  # type: ignore

        model = _CE_CACHE.get(settings.rerank_model)
        if model is None:
            model = CrossEncoder(settings.rerank_model)
            _CE_CACHE[settings.rerank_model] = model
        preds = model.predict([(query, t) for t in texts])  # type: ignore[operator]
        return [float(x) for x in preds]
    except Exception:
        return None


def _select_non_overlapping(anchors: List[tuple], window: int) -> List[int]:
    """anchors: [(idx, doc_id, seq)]；同文档内若某 anchor 落在已保留 anchor 的
    [seq-window, seq+window] 内则丢弃。返回保留的 idx 列表（保序）。"""
    kept_ranges: List[tuple] = []
    keep: List[int] = []
    for idx, doc_id, seq in anchors:
        if any(d == doc_id and s <= seq <= e for d, s, e in kept_ranges):
            continue
        kept_ranges.append((doc_id, seq - window, seq + window))
        keep.append(idx)
    return keep


def _mmr_select(items: List[dict], k: int, lam: float) -> List[dict]:
    """MMR：items 含 rel(float)/emb(list)。返回按选择顺序的前 k 个 item。"""
    selected: List[dict] = []
    remaining = list(items)
    while remaining and len(selected) < k:
        best = None
        best_val = -1e18
        for it in remaining:
            rel = float(it.get("rel", 0.0))
            if selected:
                div = max(_cos(it.get("emb", []), s.get("emb", [])) for s in selected)
            else:
                div = 0.0
            val = lam * rel - (1 - lam) * div
            if val > best_val:
                best_val = val
                best = it
        if best is None:
            break
        selected.append(best)
        remaining.remove(best)
    return selected


def _expand_context(db: Session, hits: List[SearchHit], window: int, max_chars: int) -> List[SearchHit]:
    """父块上下文扩展：合并命中片段左右 window 个邻块；去重重叠锚点；限制总字符预算。"""
    anchors = [(i, h.document_id, h.seq) for i, h in enumerate(hits)]
    keep = set(_select_non_overlapping(anchors, window))

    kept_hits: List[SearchHit] = []
    total = 0
    for i, h in enumerate(hits):
        if i not in keep:
            continue
        rows = (
            db.query(DocChunk)
            .filter(
                DocChunk.document_id == h.document_id,
                DocChunk.seq >= h.seq - window,
                DocChunk.seq <= h.seq + window,
            )
            .order_by(DocChunk.seq)
            .all()
        )
        ctx = "\n".join(r.content for r in rows) if rows else h.content
        if total + len(ctx) > max_chars:
            remain = max_chars - total
            if remain <= 0:
                break
            ctx = ctx[:remain]
        total += len(ctx)
        h.context = ctx
        kept_hits.append(h)
    return kept_hits


def search(
    db: Session,
    query: str,
    kb_ids: List[str],
    top_k: int = 5,
    extra_queries: List[str] | None = None,
) -> List[SearchHit]:
    provider = get_embedding_provider()
    # 多路查询（原文 + 改写）各自召回，RRF 累加融合
    queries = [query] + [q for q in (extra_queries or []) if q and q.strip() and q != query]

    fused: Dict[str, float] = {}
    for q in queries:
        qvec = provider.embed_query(q)
        vec_scores = _vector_search(db, qvec, kb_ids, top_k)
        bm25_scores = _bm25_search(db, q, kb_ids, top_k)
        for cid, s in _rrf_fusion(vec_scores, bm25_scores).items():
            fused[cid] = fused.get(cid, 0.0) + s

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

    ordered = [cid for cid in candidates if cid in chunk_map]
    if not ordered:
        return []
    contents = [chunk_map[cid].content for cid in ordered]
    max_fused = max(fused.values()) or 1.0

    # 相关性打分：cross-encoder（可选）> 词法重排 > 纯 RRF
    ce = _cross_encoder_scores(query, contents) if settings.rerank_provider == "cross-encoder" else None
    if ce is not None:
        rel = _minmax(ce)
    elif settings.use_rerank:
        rel = [0.5 * (fused[cid] / max_fused) + 0.5 * lexical_score(query, chunk_map[cid].content) for cid in ordered]
    else:
        rel = [fused[cid] / max_fused for cid in ordered]

    items = []
    for cid, r in zip(ordered, rel):
        c = chunk_map[cid]
        emb = list(c.embedding) if getattr(c, "embedding", None) is not None else []
        items.append({"cid": cid, "rel": float(r), "emb": emb})

    if settings.use_mmr:
        selected = _mmr_select(items, top_k, settings.mmr_lambda)
    else:
        selected = sorted(items, key=lambda x: x["rel"], reverse=True)[:top_k]

    hits: List[SearchHit] = []
    for it in selected:
        c = chunk_map[it["cid"]]
        d = doc_map.get(c.document_id)
        node = node_map.get(d.node_id) if d else None
        title = node.title if node else ""
        hits.append(
            SearchHit(
                chunk_id=c.id,
                document_id=c.document_id,
                node_id=d.node_id if d else "",
                content=c.content,
                score=round(float(it["rel"]), 4),
                document_title=title,
                knowledge_base_id=c.knowledge_base_id,
                seq=c.seq if getattr(c, "seq", None) is not None else 0,
                node_title=title,
                heading=getattr(c, "heading", "") or "",
            )
        )

    if settings.parent_expand and hits:
        hits = _expand_context(db, hits, settings.parent_window, settings.max_context_chars)
    else:
        for h in hits:
            h.context = h.content
    return hits
