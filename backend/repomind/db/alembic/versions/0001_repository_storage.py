"""repository storage

Revision ID: 0001_repository_storage
Revises:
Create Date: 2026-06-01
"""

import sqlalchemy as sa
from alembic import op

revision = "0001_repository_storage"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "repositories",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=512), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.Float(), nullable=False),
        sa.Column("updated_at", sa.Float(), nullable=False),
        sa.Column("summary", sa.JSON(), nullable=False),
        sa.Column("reports", sa.JSON(), nullable=False),
        sa.Column("analysis_job", sa.JSON(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("repository_deleted", sa.Boolean(), nullable=False),
        sa.Column("repository_deleted_at", sa.Float(), nullable=True),
        sa.Column("repository_retention_minutes", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_repositories_created_at", "repositories", ["created_at"])
    op.create_index("ix_repositories_source_type", "repositories", ["source_type"])
    op.create_index("ix_repositories_status", "repositories", ["status"])
    op.create_index("ix_repositories_updated_at", "repositories", ["updated_at"])

    op.create_table(
        "analysis_jobs",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("repo_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Float(), nullable=False),
        sa.Column("updated_at", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["repo_id"], ["repositories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_analysis_jobs_created_at", "analysis_jobs", ["created_at"])
    op.create_index("ix_analysis_jobs_repo_id", "analysis_jobs", ["repo_id"])
    op.create_index("ix_analysis_jobs_status", "analysis_jobs", ["status"])
    op.create_index("ix_analysis_jobs_updated_at", "analysis_jobs", ["updated_at"])

    op.create_table(
        "repository_artifacts",
        sa.Column("id", sa.String(length=96), nullable=False),
        sa.Column("repo_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=512), nullable=False),
        sa.Column("artifact_type", sa.String(length=64), nullable=False),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["repo_id"], ["repositories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_repository_artifacts_artifact_type", "repository_artifacts", ["artifact_type"]
    )
    op.create_index("ix_repository_artifacts_created_at", "repository_artifacts", ["created_at"])
    op.create_index("ix_repository_artifacts_repo_id", "repository_artifacts", ["repo_id"])


def downgrade() -> None:
    op.drop_index("ix_repository_artifacts_repo_id", table_name="repository_artifacts")
    op.drop_index("ix_repository_artifacts_created_at", table_name="repository_artifacts")
    op.drop_index("ix_repository_artifacts_artifact_type", table_name="repository_artifacts")
    op.drop_table("repository_artifacts")
    op.drop_index("ix_analysis_jobs_updated_at", table_name="analysis_jobs")
    op.drop_index("ix_analysis_jobs_status", table_name="analysis_jobs")
    op.drop_index("ix_analysis_jobs_repo_id", table_name="analysis_jobs")
    op.drop_index("ix_analysis_jobs_created_at", table_name="analysis_jobs")
    op.drop_table("analysis_jobs")
    op.drop_index("ix_repositories_updated_at", table_name="repositories")
    op.drop_index("ix_repositories_status", table_name="repositories")
    op.drop_index("ix_repositories_source_type", table_name="repositories")
    op.drop_index("ix_repositories_created_at", table_name="repositories")
    op.drop_table("repositories")
