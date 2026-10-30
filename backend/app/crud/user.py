from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models import Space, SpaceMember, User
from app.schemas.core import UserCreate


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()


def create_user(db: Session, data: UserCreate) -> User:
    user = User(
        email=data.email,
        username=data.username,
        hashed_password=hash_password(data.password),
    )
    db.add(user)
    db.flush()  # 拿到 user.id

    # 自动创建个人空间，并把用户设为 owner
    space = Space(name=f"{data.username} 的空间", kind="personal")
    db.add(space)
    db.flush()
    db.add(SpaceMember(space_id=space.id, user_id=user.id, role="owner"))

    db.commit()
    db.refresh(user)
    return user
