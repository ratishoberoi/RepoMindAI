"""multi tenant saas

Revision ID: 0002_multi_tenant_saas
Revises: 0001_repository_storage
Create Date: 2026-06-01
"""

import sqlalchemy as sa
from alembic import op

revision = "0002_multi_tenant_saas"
down_revision = "0001_repository_storage"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("repositories", sa.Column("org_id", sa.String(length=64), nullable=True))
    op.add_column(
        "repositories", sa.Column("created_by_user_id", sa.String(length=64), nullable=True)
    )
    op.execute("UPDATE repositories SET org_id = 'default' WHERE org_id IS NULL")
    op.alter_column("repositories", "org_id", nullable=False)
    op.create_index("ix_repositories_org_id", "repositories", ["org_id"])
    op.create_index("ix_repositories_created_by_user_id", "repositories", ["created_by_user_id"])

    op.create_table(
        "organizations",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("slug", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("plan", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.Float(), nullable=False),
        sa.Column("updated_at", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_organizations_created_at", "organizations", ["created_at"])
    op.create_index("ix_organizations_slug", "organizations", ["slug"])
    op.create_index("ix_organizations_updated_at", "organizations", ["updated_at"])

    op.create_table(
        "users",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("auth_provider", sa.String(length=64), nullable=False),
        sa.Column("provider_subject", sa.String(length=256), nullable=True),
        sa.Column("created_at", sa.Float(), nullable=False),
        sa.Column("updated_at", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_created_at", "users", ["created_at"])
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_provider_subject", "users", ["provider_subject"])
    op.create_index("ix_users_updated_at", "users", ["updated_at"])

    op.create_table(
        "teams",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("org_id", sa.String(length=64), nullable=False),
        sa.Column("slug", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("created_at", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "slug", name="uq_teams_org_slug"),
    )
    op.create_index("ix_teams_created_at", "teams", ["created_at"])
    op.create_index("ix_teams_org_id", "teams", ["org_id"])

    op.create_table(
        "memberships",
        sa.Column("id", sa.String(length=96), nullable=False),
        sa.Column("org_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("team_id", sa.String(length=64), nullable=True),
        sa.Column("role", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "user_id", "team_id", name="uq_memberships_scope"),
    )
    op.create_index("ix_memberships_created_at", "memberships", ["created_at"])
    op.create_index("ix_memberships_org_id", "memberships", ["org_id"])
    op.create_index("ix_memberships_role", "memberships", ["role"])
    op.create_index("ix_memberships_team_id", "memberships", ["team_id"])
    op.create_index("ix_memberships_user_id", "memberships", ["user_id"])

    op.create_table(
        "api_keys",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("org_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("key_hash", sa.String(length=128), nullable=False),
        sa.Column("scopes", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.Float(), nullable=False),
        sa.Column("last_used_at", sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key_hash"),
    )
    op.create_index("ix_api_keys_created_at", "api_keys", ["created_at"])
    op.create_index("ix_api_keys_key_hash", "api_keys", ["key_hash"])
    op.create_index("ix_api_keys_org_id", "api_keys", ["org_id"])
    op.create_index("ix_api_keys_user_id", "api_keys", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_api_keys_user_id", table_name="api_keys")
    op.drop_index("ix_api_keys_org_id", table_name="api_keys")
    op.drop_index("ix_api_keys_key_hash", table_name="api_keys")
    op.drop_index("ix_api_keys_created_at", table_name="api_keys")
    op.drop_table("api_keys")
    op.drop_index("ix_memberships_user_id", table_name="memberships")
    op.drop_index("ix_memberships_team_id", table_name="memberships")
    op.drop_index("ix_memberships_role", table_name="memberships")
    op.drop_index("ix_memberships_org_id", table_name="memberships")
    op.drop_index("ix_memberships_created_at", table_name="memberships")
    op.drop_table("memberships")
    op.drop_index("ix_teams_org_id", table_name="teams")
    op.drop_index("ix_teams_created_at", table_name="teams")
    op.drop_table("teams")
    op.drop_index("ix_users_updated_at", table_name="users")
    op.drop_index("ix_users_provider_subject", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_created_at", table_name="users")
    op.drop_table("users")
    op.drop_index("ix_organizations_updated_at", table_name="organizations")
    op.drop_index("ix_organizations_slug", table_name="organizations")
    op.drop_index("ix_organizations_created_at", table_name="organizations")
    op.drop_table("organizations")
    op.drop_index("ix_repositories_created_by_user_id", table_name="repositories")
    op.drop_index("ix_repositories_org_id", table_name="repositories")
    op.drop_column("repositories", "created_by_user_id")
    op.drop_column("repositories", "org_id")
