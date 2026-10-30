from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.roles import is_admin_email
from app.core.security import create_access_token, create_refresh_token, decode_token, verify_password
from app.crud.user import create_user, get_user_by_email
from app.db import get_db
from app.deps import get_current_user
from app.models import AuditLog, User
from app.schemas.core import MeOut, RefreshRequest, Token, UserCreate, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


def _audit(db: Session, user_id: str | None, action: str, path: str, status_code: int, request: Request) -> None:
    """登录/注册显式留痕（含成败与 user_id）。失败不阻塞主流程。"""
    try:
        db.add(
            AuditLog(
                user_id=user_id,
                action=action,
                method="POST",
                path=path[:255],
                status_code=status_code,
                ip=(request.client.host if request.client else None),
            )
        )
        db.commit()
    except Exception:
        db.rollback()


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(request: Request, data: UserCreate, db: Session = Depends(get_db)):
    if get_user_by_email(db, data.email):
        raise HTTPException(status_code=400, detail="该邮箱已注册")
    user = create_user(db, data)
    _audit(db, user.id, "注册", "/api/v1/auth/register", 201, request)
    return user


@router.post("/login", response_model=Token)
def login(
    request: Request,
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = get_user_by_email(db, form.username)
    if not user or not verify_password(form.password, user.hashed_password):
        _audit(db, user.id if user else None, "登录失败", "/api/v1/auth/login", 401, request)
        raise HTTPException(status_code=401, detail="邮箱或密码错误")
    _audit(db, user.id, "登录", "/api/v1/auth/login", 200, request)
    return Token(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/refresh", response_model=Token)
def refresh(body: RefreshRequest, db: Session = Depends(get_db)):
    try:
        payload = decode_token(body.refresh_token)
    except Exception:
        raise HTTPException(status_code=401, detail="刷新令牌无效")
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="令牌类型错误")
    user = db.get(User, payload.get("sub"))
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="用户不存在或已禁用")
    return Token(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.get("/me", response_model=MeOut)
def me(current_user: User = Depends(get_current_user)):
    base = UserOut.model_validate(current_user)
    return MeOut(**base.model_dump(), is_admin=is_admin_email(current_user.email))
