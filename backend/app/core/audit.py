"""审计中间件：对所有写操作（POST/PUT/PATCH/DELETE）自动留痕，不阻塞主流程。"""

import logging

from starlette.middleware.base import BaseHTTPMiddleware

from app.core.security import decode_token
from app.db import SessionLocal
from app.models import AuditLog

logger = logging.getLogger("audit")

_WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def _action_name(method: str, path: str) -> str:
    """把请求映射为可读的语义动作（未匹配则回退为 METHOD path）。"""
    p = path.rstrip("/")
    if method == "POST" and p.endswith("/auth/login"):
        return "登录"
    if method == "POST" and p.endswith("/auth/register"):
        return "注册"
    if p.endswith("/content") and method == "PUT":
        return "保存文档"
    if "/nodes" in p and method == "POST":
        return "新建节点"
    if "/nodes" in p and method == "PATCH":
        return "修改节点"
    if "/nodes" in p and method == "DELETE":
        return "删除节点"
    if p.endswith("/import"):
        return "导入文档"
    if p.endswith("/rag/index"):
        return "重建索引"
    if "/share" in p and method == "POST":
        return "创建分享"
    if "/kb" in p and method == "POST":
        return "新建知识库"
    if "/spaces" in p and method == "POST":
        return "新建空间"
    return f"{method} {path}"


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        try:
            path = request.url.path
            if (
                request.method in _WRITE_METHODS
                and path.startswith("/api/")
                and not path.endswith(("/auth/login", "/auth/register"))
            ):
                self._record(request, response.status_code)
        except Exception:  # 审计失败绝不影响业务
            logger.exception("write audit log failed")
        return response

    def _record(self, request, status_code: int) -> None:
        user_id = None
        auth = request.headers.get("authorization") or ""
        if auth.lower().startswith("bearer "):
            try:
                user_id = decode_token(auth[7:]).get("sub")
            except Exception:
                user_id = None
        ip = request.client.host if request.client else None

        db = SessionLocal()
        try:
            db.add(
                AuditLog(
                    user_id=user_id,
                    action=_action_name(request.method, request.url.path),
                    method=request.method,
                    path=request.url.path[:255],
                    status_code=status_code,
                    ip=ip,
                )
            )
            db.commit()
        finally:
            db.close()
