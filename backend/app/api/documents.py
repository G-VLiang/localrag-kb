from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import DocNode, Document, DocumentVersion, KnowledgeBase, SpaceMember, User
from app.rag.parser import parse_bytes
from app.schemas.core import DocNodeCreate, DocNodeOut, DocNodeUpdate, DocumentOut, DocumentSave

router = APIRouter(prefix="/kb/{kb_id}", tags=["documents"])


def _require_kb_access(db: Session, user: User, kb_id: str) -> SpaceMember:
    kb = db.get(KnowledgeBase, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    membership = (
        db.query(SpaceMember)
        .filter(SpaceMember.space_id == kb.space_id, SpaceMember.user_id == user.id)
        .first()
    )
    if not membership:
        raise HTTPException(status_code=403, detail="无权访问该知识库")
    return membership


# ---------- 文档树 ----------
@router.get("/tree", response_model=list[DocNodeOut])
def get_tree(kb_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _require_kb_access(db, user, kb_id)
    return db.query(DocNode).filter(DocNode.knowledge_base_id == kb_id).order_by(DocNode.position).all()


@router.post("/nodes", response_model=DocNodeOut, status_code=status.HTTP_201_CREATED)
def create_node(
    kb_id: str,
    data: DocNodeCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    m = _require_kb_access(db, user, kb_id)
    if m.role not in ("owner", "admin", "editor"):
        raise HTTPException(status_code=403, detail="无文档写入权限")
    node = DocNode(
        knowledge_base_id=kb_id,
        parent_id=data.parent_id,
        title=data.title,
        kind=data.kind,
    )
    db.add(node)
    db.flush()
    if data.kind == "document":
        db.add(Document(node_id=node.id, content="", content_format="html"))
    db.commit()
    db.refresh(node)
    return node


@router.patch("/nodes/{node_id}", response_model=DocNodeOut)
def update_node(
    kb_id: str,
    node_id: str,
    data: DocNodeUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    m = _require_kb_access(db, user, kb_id)
    if m.role not in ("owner", "admin", "editor"):
        raise HTTPException(status_code=403, detail="无文档写入权限")
    node = db.get(DocNode, node_id)
    if not node or node.knowledge_base_id != kb_id:
        raise HTTPException(status_code=404, detail="节点不存在")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(node, k, v)
    db.commit()
    db.refresh(node)
    return node


@router.delete("/nodes/{node_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_node(
    kb_id: str,
    node_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    m = _require_kb_access(db, user, kb_id)
    if m.role not in ("owner", "admin", "editor"):
        raise HTTPException(status_code=403, detail="无文档写入权限")
    node = db.get(DocNode, node_id)
    if not node or node.knowledge_base_id != kb_id:
        raise HTTPException(status_code=404, detail="节点不存在")
    db.delete(node)
    db.commit()


# ---------- 文档内容 ----------
@router.get("/nodes/{node_id}/content", response_model=DocumentOut)
def get_document(
    kb_id: str,
    node_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_kb_access(db, user, kb_id)
    doc = db.query(Document).filter(Document.node_id == node_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    return doc


@router.put("/nodes/{node_id}/content", response_model=DocumentOut)
def save_document(
    kb_id: str,
    node_id: str,
    data: DocumentSave,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    m = _require_kb_access(db, user, kb_id)
    if m.role not in ("owner", "admin", "editor"):
        raise HTTPException(status_code=403, detail="无文档写入权限")
    doc = db.query(Document).filter(Document.node_id == node_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    # 保存历史版本快照
    db.add(
        DocumentVersion(
            document_id=doc.id,
            version=doc.version,
            content=doc.content,
            content_format=doc.content_format,
        )
    )
    doc.content = data.content
    doc.content_format = data.content_format
    doc.version += 1
    db.commit()
    db.refresh(doc)
    return doc


# ---------- 版本历史 ----------
@router.get("/nodes/{node_id}/versions")
def list_versions(
    kb_id: str,
    node_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_kb_access(db, user, kb_id)
    doc = db.query(Document).filter(Document.node_id == node_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    versions = (
        db.query(DocumentVersion)
        .filter(DocumentVersion.document_id == doc.id)
        .order_by(DocumentVersion.version.desc())
        .all()
    )
    return [
        {"id": v.id, "version": v.version, "content_format": v.content_format, "created_at": v.created_at}
        for v in versions
    ]


@router.get("/nodes/{node_id}/versions/{version_id}")
def get_version(
    kb_id: str,
    node_id: str,
    version_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_kb_access(db, user, kb_id)
    v = db.get(DocumentVersion, version_id)
    if not v:
        raise HTTPException(status_code=404, detail="版本不存在")
    return {"content": v.content, "content_format": v.content_format, "version": v.version}


# ---------- 文档导入 ----------
@router.post("/import", response_model=DocNodeOut, status_code=status.HTTP_201_CREATED)
async def import_document(
    kb_id: str,
    file: UploadFile,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    m = _require_kb_access(db, user, kb_id)
    if m.role not in ("owner", "admin", "editor"):
        raise HTTPException(status_code=403, detail="无文档写入权限")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="文件为空")

    title = (file.filename or "未命名文档").rsplit(".", 1)[0]
    text = parse_bytes(file.filename or "", data)

    node = DocNode(
        knowledge_base_id=kb_id,
        title=title,
        kind="document",
    )
    db.add(node)
    db.flush()
    db.add(Document(node_id=node.id, content=text, content_format="markdown"))
    db.commit()
    db.refresh(node)
    return node


# ---------- 文档导出 ----------
@router.get("/nodes/{node_id}/export")
def export_document(
    kb_id: str,
    node_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_kb_access(db, user, kb_id)
    doc = db.query(Document).filter(Document.node_id == node_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    node = db.get(DocNode, node_id)
    return {"title": node.title, "content": doc.content, "content_format": doc.content_format}


# ---------- 全文关键字搜索 ----------
@router.get("/search")
def keyword_search(
    kb_id: str,
    q: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_kb_access(db, user, kb_id)
    docs = (
        db.query(Document, DocNode)
        .join(DocNode, DocNode.id == Document.node_id)
        .filter(DocNode.knowledge_base_id == kb_id, Document.content.ilike(f"%{q}%"))
        .limit(50)
        .all()
    )
    return [
        {"node_id": node.id, "title": node.title, "kind": node.kind, "updated_at": node.updated_at}
        for doc, node in docs
    ]
