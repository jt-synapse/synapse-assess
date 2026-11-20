"""Record immutable published assessment-package versions."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0001_assessment_versions"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "assessment_versions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("assessment_key", sa.Text(), nullable=False),
        sa.Column("version", sa.Text(), nullable=False),
        sa.Column("manifest", JSONB(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("assessment_key", "version", name="uq_assessment_key_version"),
    )


def downgrade() -> None:
    op.drop_table("assessment_versions")
