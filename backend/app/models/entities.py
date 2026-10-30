import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from app.db import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    username: Mapped[str] = mapped_column(String(64), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    memberships = relationship("SpaceMember", back_populates="user", cascade="all, delete-orphan")


class Space(Base, TimestampMixin):
    __tablename__ = "spaces"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 团队空间 or 个人空间
    kind: Mapped[str] = mapped_column(String(16), default="personal", nullable=False)  # personal | team

    members = relationship("SpaceMember", back_populates="space", cascade="all, delete-orphan")
    knowledge_bases = relationship("KnowledgeBase", back_populates="space", cascade="all, delete-orphan")


class SpaceMember(Base, TimestampMixin):
    """空间成员及角色。"""

    __tablename__ = "space_members"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    space_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("spaces.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    # owner | admin | editor | reader
    role: Mapped[str] = mapped_column(String(16), default="reader", nullable=False)

    space = relationship("Space", back_populates="members")
    user = relationship("User", back_populates="memberships")


class KnowledgeBase(Base, TimestampMixin):
    __tablename__ = "knowledge_bases"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    space_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("spaces.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    space = relationship("Space", back_populates="knowledge_bases")
    nodes = relationship("DocNode", back_populates="knowledge_base", cascade="all, delete-orphan")


class DocNode(Base, TimestampMixin):
    """文档树节点：可表示目录或文档。"""

    __tablename__ = "doc_nodes"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    knowledge_base_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("knowledge_bases.id", ondelete="CASCADE"), index=True
    )
    parent_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("doc_nodes.id", ondelete="CASCADE"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    # folder | document
    kind: Mapped[str] = mapped_column(String(16), default="document", nullable=False)
    # 排序
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    knowledge_base = relationship("KnowledgeBase", back_populates="nodes")
    parent = relationship("DocNode", remote_side=[id], back_populates="children")
    children = relationship(
        "DocNode", cascade="all, delete-orphan", back_populates="parent", single_parent=True
    )
    document = relationship("Document", back_populates="node", uselist=False, cascade="all, delete-orphan")


class Document(Base, TimestampMixin):
    """文档内容（与 DocNode 1:1，kind=document 时存在）。"""

    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    node_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("doc_nodes.id", ondelete="CASCADE"), unique=True, index=True
    )
    content: Mapped[str] = mapped_column(Text, default="", nullable=False)  # 存储 HTML（Tiptap）或 Markdown
    content_format: Mapped[str] = mapped_column(String(16), default="html", nullable=False)  # html | markdown
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    node = relationship("DocNode", back_populates="document")


class DocumentVersion(Base, TimestampMixin):
    """文档历史版本快照。"""

    __tablename__ = "document_versions"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    document_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_format: Mapped[str] = mapped_column(String(16), nullable=False)


class DocChunk(Base, TimestampMixin):
    """文档切片 + 向量，用于 RAG 检索。"""

    __tablename__ = "doc_chunks"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    document_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    # 冗余存储，便于检索时按知识库/空间过滤权限
    knowledge_base_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("knowledge_bases.id", ondelete="CASCADE"), index=True
    )
    # 片段在原文中的位置（序号）
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # bge-m3 默认 1024 维
    embedding: Mapped[list[float]] = mapped_column(Vector(1024), nullable=True)
    # 全文检索用 tsvector（BM25 融合）
    content_tsv: Mapped[str | None] = mapped_column(Text, nullable=True)

    document = relationship("Document", backref="chunks")


class ShareLink(Base, TimestampMixin):
    """文档分享链接（可选密码、有效期）。"""

    __tablename__ = "share_links"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    node_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("doc_nodes.id", ondelete="CASCADE"), index=True
    )
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    # 密码（bcrypt 哈希，空则无需密码）
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
