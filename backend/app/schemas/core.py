from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ---------- User / Auth ----------
class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(min_length=1, max_length=64)


class UserCreate(UserBase):
    password: str = Field(min_length=6, max_length=128)


class UserOut(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    is_active: bool
    created_at: datetime


class MeOut(UserOut):
    is_admin: bool = False


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


# ---------- Space ----------
class SpaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    description: Optional[str] = None
    kind: str = Field(default="personal", pattern="^(personal|team)$")


class SpaceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class SpaceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: Optional[str]
    kind: str
    created_at: datetime


class SpaceMemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    role: str
    user: UserOut


# ---------- KnowledgeBase ----------
class KnowledgeBaseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    description: Optional[str] = None


class KnowledgeBaseUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class KnowledgeBaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    space_id: str
    name: str
    description: Optional[str]
    created_at: datetime


# ---------- DocNode ----------
class DocNodeCreate(BaseModel):
    parent_id: Optional[str] = None
    title: str = Field(min_length=1, max_length=255)
    kind: str = Field(default="document", pattern="^(folder|document)$")


class DocNodeUpdate(BaseModel):
    title: Optional[str] = None
    parent_id: Optional[str] = None
    position: Optional[int] = None


class DocNodeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    knowledge_base_id: str
    parent_id: Optional[str]
    title: str
    kind: str
    position: int
    created_at: datetime
    updated_at: datetime


# ---------- Document ----------
class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    node_id: str
    content: str
    content_format: str
    version: int
    updated_at: datetime


class DocumentSave(BaseModel):
    content: str
    content_format: str = Field(default="html", pattern="^(html|markdown)$")
