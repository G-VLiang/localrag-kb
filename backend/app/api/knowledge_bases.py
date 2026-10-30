from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import KnowledgeBase, Space, SpaceMember, User
from app.schemas.core import KnowledgeBaseCreate, KnowledgeBaseOut, KnowledgeBaseUpdate

router = APIRouter(prefix="/spaces/{space_id}/kb", tags=["knowledge_bases"])


def _require_space_access(db: Session, user: User, space_id: str) -> SpaceMember:
    membership = (
        db.query(SpaceMember)
        .filter(SpaceMember.space_id == space_id, SpaceMember.user_id == user.id)
        .first()
    )
    if not membership:
        raise HTTPException(status_code=403, detail="无权访问该空间")
    return membership


@router.get("", response_model=list[KnowledgeBaseOut])
def list_kb(
    space_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_space_access(db, user, space_id)
    return db.query(KnowledgeBase).filter(KnowledgeBase.space_id == space_id).all()


@router.post("", response_model=KnowledgeBaseOut, status_code=status.HTTP_201_CREATED)
def create_kb(
    space_id: str,
    data: KnowledgeBaseCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    m = _require_space_access(db, user, space_id)
    if m.role not in ("owner", "admin", "editor"):
        raise HTTPException(status_code=403, detail="无创建知识库权限")
    kb = KnowledgeBase(space_id=space_id, name=data.name, description=data.description)
    db.add(kb)
    db.commit()
    db.refresh(kb)
    return kb


@router.patch("/{kb_id}", response_model=KnowledgeBaseOut)
def update_kb(
    space_id: str,
    kb_id: str,
    data: KnowledgeBaseUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    m = _require_space_access(db, user, space_id)
    if m.role not in ("owner", "admin", "editor"):
        raise HTTPException(status_code=403, detail="无修改知识库权限")
    kb = db.get(KnowledgeBase, kb_id)
    if not kb or kb.space_id != space_id:
        raise HTTPException(status_code=404, detail="知识库不存在")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(kb, k, v)
    db.commit()
    db.refresh(kb)
    return kb


@router.delete("/{kb_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_kb(
    space_id: str,
    kb_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    m = _require_space_access(db, user, space_id)
    if m.role not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="无删除知识库权限")
    kb = db.get(KnowledgeBase, kb_id)
    if not kb or kb.space_id != space_id:
        raise HTTPException(status_code=404, detail="知识库不存在")
    db.delete(kb)
    db.commit()
