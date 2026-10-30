"""全局角色：基于 ADMIN_EMAILS 配置判定管理员（无需改表）。"""

from app.config import settings


def admin_emails() -> set[str]:
    return {e.strip().lower() for e in settings.admin_emails.split(",") if e.strip()}


def is_admin_email(email: str | None) -> bool:
    return bool(email) and email.lower() in admin_emails()
