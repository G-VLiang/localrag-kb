"""add doc_chunks

Revision ID: 0002_doc_chunks
Revises: 0001_init
Create Date: 2026-10-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

revision: str = "0002_doc_chunks"
down_revision: Union[str, None] = "0001_init"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "doc_chunks",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("document_id", sa.Uuid(), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("knowledge_base_id", sa.Uuid(), sa.ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(1024), nullable=True),
        sa.Column("content_tsv", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_doc_chunks_document_id", "doc_chunks", ["document_id"])
    op.create_index("ix_doc_chunks_knowledge_base_id", "doc_chunks", ["knowledge_base_id"])
    # HNSW 向量索引（加速相似度检索）
    op.execute(
        "CREATE INDEX ix_doc_chunks_kb_embedding ON doc_chunks "
        "USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)"
    )


def downgrade() -> None:
    op.drop_index("ix_doc_chunks_kb_embedding")
    op.drop_index("ix_doc_chunks_knowledge_base_id")
    op.drop_index("ix_doc_chunks_document_id")
    op.drop_table("doc_chunks")
