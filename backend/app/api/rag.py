from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import DocNode, Document, KnowledgeBase, SpaceMember, User
from app.rag.indexer import index_document, index_knowledge_base
from app.rag.llm import generate_answer
from app.rag.retriever import SearchHit, search
from app.schemas.rag import (
    AskRequest,
    AskResponse,
    IndexRequest,
    IndexResponse,
    SearchHitOut,
    SearchRequest,
    SearchResponse,
)

router = APIRouter(prefix="/rag", tags=["rag"])


def _handle_model_error(exc: Exception) -> HTTPException:
    """模型未就绪时返回 503 + 可读提示，而不是 500。"""
    msg = str(exc)
    low = msg.lower()
    # Embedding 未就绪
    if "embedding" in low or "sentence_transformers" in low or "依赖未安装" in msg:
        return HTTPException(
            status_code=503,
            detail="Embedding 模型未就绪。请在后端容器内安装 sentence-transformers，"
            "或将 .env 的 EMBEDDING_PROVIDER 设为 ollama / openai（见 README「启用 RAG 模型」）",
        )
    # LLM 未就绪
    if "ollama" in low or "11434" in msg or "llm" in low:
        return HTTPException(
            status_code=503,
            detail="LLM 服务未连接。请启动 Ollama 并拉取模型，或将 .env 的 LLM_PROVIDER 设为 openai",
        )
    return HTTPException(status_code=500, detail=f"RAG 处理失败：{msg}")


def _hit_to_out(h: SearchHit) -> SearchHitOut:
    return SearchHitOut(
        chunk_id=h.chunk_id,
        document_id=h.document_id,
        node_id=h.node_id,
        content=h.content,
        score=h.score,
        document_title=h.document_title,
        knowledge_base_id=h.knowledge_base_id,
        seq=h.seq,
        node_title=h.node_title,
    )


def _check_kb_access(db: Session, user: User, kb_ids: list[str]) -> None:
    """校验用户对每个 kb 有空间成员权限，并返回合法的 kb 列表（权限下推）。"""
    kbs = db.query(KnowledgeBase).filter(KnowledgeBase.id.in_(kb_ids)).all()
    kb_to_space = {kb.id: kb.space_id for kb in kbs}
    space_ids = list(set(kb_to_space.values()))
    if not space_ids:
        raise HTTPException(status_code=404, detail="知识库不存在")
    memberships = (
        db.query(SpaceMember)
        .filter(SpaceMember.space_id.in_(space_ids), SpaceMember.user_id == user.id)
        .all()
    )
    allowed_spaces = {m.space_id for m in memberships}
    allowed = [kb_id for kb_id in kb_ids if kb_to_space.get(kb_id) in allowed_spaces]
    if not allowed:
        raise HTTPException(status_code=403, detail="无权访问这些知识库")
    return allowed


@router.post("/index", response_model=IndexResponse)
def index(
    body: IndexRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if body.scope == "knowledge_base":
        kb_id = body.node_id
        kb = db.get(KnowledgeBase, kb_id)
        if not kb:
            raise HTTPException(status_code=404, detail="知识库不存在")
        # 权限校验
        _check_kb_access(db, user, [kb_id])
        try:
            count = index_knowledge_base(db, kb_id)
        except HTTPException:
            raise
        except Exception as exc:
            raise _handle_model_error(exc)
    else:
        node = db.get(DocNode, body.node_id) if body.node_id else None
        if not node:
            raise HTTPException(status_code=404, detail="文档不存在")
        _check_kb_access(db, user, [node.knowledge_base_id])
        doc = db.query(Document).filter(Document.node_id == node.id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="文档内容不存在")
        try:
            count = index_document(db, doc)
        except HTTPException:
            raise
        except Exception as exc:
            raise _handle_model_error(exc)
    return IndexResponse(status="ok", chunk_count=count)


@router.post("/search", response_model=SearchResponse)
def search_endpoint(
    body: SearchRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    allowed = _check_kb_access(db, user, body.kb_ids)
    try:
        hits = search(db, body.query, allowed, top_k=body.top_k)
    except HTTPException:
        raise
    except Exception as exc:
        raise _handle_model_error(exc)
    return SearchResponse(hits=[_hit_to_out(h) for h in hits])


@router.post("/ask", response_model=AskResponse)
def ask(
    body: AskRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    allowed = _check_kb_access(db, user, body.kb_ids)
    try:
        hits = search(db, body.query, allowed, top_k=body.top_k)
        answer = generate_answer(body.query, hits)
    except HTTPException:
        raise
    except Exception as exc:
        raise _handle_model_error(exc)
    return AskResponse(answer=answer, hits=[_hit_to_out(h) for h in hits])
