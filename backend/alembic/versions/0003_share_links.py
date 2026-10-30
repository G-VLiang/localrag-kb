"""add share_links

Revision ID: 0003_share_links
Revises: 0002_doc_chunks
Create Date: 2026-10-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003_share_links"
down_revision: Union[str, None] = "0002_doc_chunks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "share_links",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("node_id", sa.Uuid(), sa.ForeignKey("doc_nodes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token", sa.String(64), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_share_links_node_id", "share_links", ["node_id"])
    op.create_index("ix_share_links_token", "share_links", ["token"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_share_links_token")
    op.drop_index("ix_share_links_node_id")
    op.drop_table("share_links")
