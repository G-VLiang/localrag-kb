from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class MemberAdd(BaseModel):
    email: str
    role: str = Field(default="reader", pattern="^(owner|admin|editor|reader)$")


class MemberUpdate(BaseModel):
    role: str = Field(pattern="^(owner|admin|editor|reader)$")


class ShareLinkCreate(BaseModel):
    password: Optional[str] = None
    expires_in_days: Optional[int] = Field(default=None, ge=1, le=365)


class ShareLinkOut(BaseModel):
    id: str
    node_id: str
    token: str
    expires_at: Optional[datetime]
    is_active: bool
    url: str


class ShareAccessRequest(BaseModel):
    token: str
    password: Optional[str] = None


class SharedDocOut(BaseModel):
    title: str
    content: str
    content_format: str
