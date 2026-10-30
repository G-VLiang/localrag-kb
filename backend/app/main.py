from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.api import auth, documents, knowledge_bases, rag, share, spaces

app = FastAPI(title=settings.app_name, debug=settings.debug)

# 跨域：生产环境使用显式白名单（携带凭证时不可用通配符 *）
_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
if settings.debug and not _origins:
    _origins = ["*"]
_allow_credentials = bool(_origins) and _origins != ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def _unhandled(request: Request, exc: Exception):
    # 生产环境隐藏堆栈细节，仅返回通用错误；开发态返回异常摘要便于排查
    if settings.debug:
        return JSONResponse(status_code=500, content={"detail": str(exc), "type": type(exc).__name__})
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})

api_prefix = settings.api_v1_prefix

app.include_router(auth.router, prefix=api_prefix)
app.include_router(spaces.router, prefix=api_prefix)
app.include_router(knowledge_bases.router, prefix=api_prefix)
app.include_router(documents.router, prefix=api_prefix)
app.include_router(rag.router, prefix=api_prefix)
app.include_router(share.router, prefix=api_prefix)


@app.get("/health")
def health():
    return {"status": "ok", "app": settings.app_name}


@app.get("/")
def root():
    return {"message": f"{settings.app_name} API", "docs": "/docs"}
