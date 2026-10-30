from typing import List, Optional

from pydantic import BaseModel, Field


class IndexRequest(BaseModel):
    """重建索引请求。scope: document | knowledge_base"""

    scope: str = Field(default="document", pattern="^(document|knowledge_base)$")
    node_id: Optional[str] = None


class IndexResponse(BaseModel):
    status: str
    chunk_count: int


class SearchHitOut(BaseModel):
    chunk_id: str
    document_id: str
    node_id: str
    content: str
    score: float
    document_title: str
    knowledge_base_id: str


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    kb_ids: List[str]
    top_k: int = Field(default=5, ge=1, le=20)


class SearchResponse(BaseModel):
    hits: List[SearchHitOut]


class AskRequest(BaseModel):
    query: str = Field(min_length=1)
    kb_ids: List[str]
    top_k: int = Field(default=5, ge=1, le=20)


class AskResponse(BaseModel):
    answer: str
    hits: List[SearchHitOut]
