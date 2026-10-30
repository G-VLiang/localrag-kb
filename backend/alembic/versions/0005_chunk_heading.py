"""add doc_chunks.heading

Revision ID: 0005_chunk_heading
Revises: 0004_document_versions
Create Date: 2026-10-30
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0005_chunk_heading"
down_revision: Union[str, None] = "0004_document_versions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("doc_chunks", sa.Column("heading", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("doc_chunks", "heading")
