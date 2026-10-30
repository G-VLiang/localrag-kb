import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.core.security import hash_password, verify_password
from app.db import get_db
from app.deps import get_current_user
from app.models import DocNode, Document, KnowledgeBase, ShareLink, SpaceMember, User
from app.schemas.share import (
    ShareAccessRequest,
    ShareLinkCreate,
    ShareLinkOut,
    SharedDocOut,
)

router = APIRouter(tags=["share"])


def _require_node_write(db: Session, user: User, node_id: str) -> DocNode:
    node = db.get(DocNode, node_id)
    if not node:
        raise HTTPException(status_code=404, detail="文档不存在")
    kb = db.get(KnowledgeBase, node.knowledge_base_id)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    membership = (
        db.query(SpaceMember)
        .filter(SpaceMember.space_id == kb.space_id, SpaceMember.user_id == user.id)
        .first()
    )
    if not membership or membership.role not in ("owner", "admin", "editor"):
        raise HTTPException(status_code=403, detail="无分享权限")
    return node


@router.post("/nodes/{node_id}/share", response_model=ShareLinkOut, status_code=status.HTTP_201_CREATED)
def create_share(
    node_id: str,
    data: ShareLinkCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_node_write(db, user, node_id)
    token = secrets.token_urlsafe(32)
    expires_at = (
        datetime.now(timezone.utc) + timedelta(days=data.expires_in_days)
        if data.expires_in_days
        else None
    )
    link = ShareLink(
        node_id=node_id,
        token=token,
        password_hash=hash_password(data.password) if data.password else None,
        expires_at=expires_at,
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    base = settings.public_base_url
    return ShareLinkOut(
        id=link.id,
        node_id=link.node_id,
        token=link.token,
        expires_at=link.expires_at,
        is_active=link.is_active,
        url=f"{base}/share/{link.token}",
    )


@router.post("/share/access", response_model=SharedDocOut)
def access_share(body: ShareAccessRequest, db: Session = Depends(get_db)):
    """公开访问分享的文档（无需登录）。"""
    link = db.query(ShareLink).filter(ShareLink.token == body.token).first()
    if not link or not link.is_active:
        raise HTTPException(status_code=404, detail="分享链接不存在或已失效")
    if link.expires_at and link.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail="分享链接已过期")
    if link.password_hash:
        if not body.password or not verify_password(body.password, link.password_hash):
            raise HTTPException(status_code=403, detail="密码错误")
    node = db.get(DocNode, link.node_id)
    if not node:
        raise HTTPException(status_code=404, detail="文档不存在")
    doc = db.query(Document).filter(Document.node_id == node.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档内容不存在")
    return SharedDocOut(title=node.title, content=doc.content, content_format=doc.content_format)
