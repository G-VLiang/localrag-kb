from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import Space, SpaceMember, User
from app.schemas.core import SpaceCreate, SpaceMemberOut, SpaceOut, SpaceUpdate
from app.schemas.share import MemberAdd, MemberUpdate

router = APIRouter(prefix="/spaces", tags=["spaces"])


def _require_space_access(db: Session, user: User, space_id: str) -> SpaceMember:
    """校验用户是该空间成员，返回成员记录（含角色）。"""
    membership = (
        db.query(SpaceMember)
        .filter(SpaceMember.space_id == space_id, SpaceMember.user_id == user.id)
        .first()
    )
    if not membership:
        raise HTTPException(status_code=403, detail="无权访问该空间")
    return membership


@router.get("", response_model=list[SpaceOut])
def list_spaces(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return (
        db.query(Space)
        .join(SpaceMember, SpaceMember.space_id == Space.id)
        .filter(SpaceMember.user_id == user.id)
        .all()
    )


@router.post("", response_model=SpaceOut, status_code=status.HTTP_201_CREATED)
def create_space(
    data: SpaceCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    space = Space(name=data.name, description=data.description, kind=data.kind)
    db.add(space)
    db.flush()  # 拿到 space.id
    db.add(SpaceMember(space_id=space.id, user_id=user.id, role="owner"))
    db.commit()
    db.refresh(space)
    return space


@router.get("/{space_id}", response_model=SpaceOut)
def get_space(
    space_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_space_access(db, user, space_id)
    space = db.get(Space, space_id)
    if not space:
        raise HTTPException(status_code=404, detail="空间不存在")
    return space


@router.patch("/{space_id}", response_model=SpaceOut)
def update_space(
    space_id: str,
    data: SpaceUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    m = _require_space_access(db, user, space_id)
    if m.role not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="仅空间所有者/管理员可修改")
    space = db.get(Space, space_id)
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(space, k, v)
    db.commit()
    db.refresh(space)
    return space


@router.delete("/{space_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_space(
    space_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    m = _require_space_access(db, user, space_id)
    if m.role != "owner":
        raise HTTPException(status_code=403, detail="仅空间所有者可删除")
    space = db.get(Space, space_id)
    db.delete(space)
    db.commit()


@router.get("/{space_id}/members", response_model=list[SpaceMemberOut])
def list_members(
    space_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_space_access(db, user, space_id)
    return db.query(SpaceMember).filter(SpaceMember.space_id == space_id).all()


@router.post("/{space_id}/members", response_model=SpaceMemberOut, status_code=status.HTTP_201_CREATED)
def add_member(
    space_id: str,
    data: MemberAdd,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    m = _require_space_access(db, user, space_id)
    if m.role not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="仅空间所有者/管理员可添加成员")
    target = db.query(User).filter(User.email == data.email).first()
    if not target:
        raise HTTPException(status_code=404, detail="用户不存在")
    exists = (
        db.query(SpaceMember)
        .filter(SpaceMember.space_id == space_id, SpaceMember.user_id == target.id)
        .first()
    )
    if exists:
        raise HTTPException(status_code=400, detail="该用户已是空间成员")
    member = SpaceMember(space_id=space_id, user_id=target.id, role=data.role)
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


@router.patch("/{space_id}/members/{member_id}", response_model=SpaceMemberOut)
def update_member(
    space_id: str,
    member_id: str,
    data: MemberUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    m = _require_space_access(db, user, space_id)
    if m.role not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="仅空间所有者/管理员可修改成员")
    member = db.get(SpaceMember, member_id)
    if not member or member.space_id != space_id:
        raise HTTPException(status_code=404, detail="成员不存在")
    member.role = data.role
    db.commit()
    db.refresh(member)
    return member


@router.delete("/{space_id}/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    space_id: str,
    member_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    m = _require_space_access(db, user, space_id)
    if m.role not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="仅空间所有者/管理员可移除成员")
    member = db.get(SpaceMember, member_id)
    if not member or member.space_id != space_id:
        raise HTTPException(status_code=404, detail="成员不存在")
    if member.role == "owner":
        raise HTTPException(status_code=400, detail="不能移除空间所有者")
    db.delete(member)
    db.commit()
