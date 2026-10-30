from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api import auth, documents, knowledge_bases, rag, share, spaces

app = FastAPI(title=settings.app_name, debug=settings.debug)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 本地开发放开，生产按需收紧
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
