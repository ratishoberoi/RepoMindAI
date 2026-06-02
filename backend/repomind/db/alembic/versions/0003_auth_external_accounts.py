"""auth external accounts

Revision ID: 0003_auth_external_accounts
Revises: 0002_multi_tenant_saas
Create Date: 2026-06-02
"""

import sqlalchemy as sa
from alembic import op

revision = "0003_auth_external_accounts"
down_revision = "0002_multi_tenant_saas"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("password_hash", sa.String(length=256), nullable=True))

    op.create_table(
        "external_accounts",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("org_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("provider_subject", sa.String(length=256), nullable=False),
        sa.Column("username", sa.String(length=256), nullable=True),
        sa.Column("access_token_encrypted", sa.Text(), nullable=True),
        sa.Column("refresh_token_encrypted", sa.Text(), nullable=True),
        sa.Column("installation_id", sa.String(length=128), nullable=True),
        sa.Column("scopes", sa.JSON(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.Float(), nullable=False),
        sa.Column("updated_at", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "provider_subject", name="uq_external_provider_subject"),
    )
    op.create_index("ix_external_accounts_created_at", "external_accounts", ["created_at"])
    op.create_index(
        "ix_external_accounts_installation_id", "external_accounts", ["installation_id"]
    )
    op.create_index("ix_external_accounts_org_id", "external_accounts", ["org_id"])
    op.create_index("ix_external_accounts_provider", "external_accounts", ["provider"])
    op.create_index(
        "ix_external_accounts_provider_subject", "external_accounts", ["provider_subject"]
    )
    op.create_index("ix_external_accounts_updated_at", "external_accounts", ["updated_at"])
    op.create_index("ix_external_accounts_user_id", "external_accounts", ["user_id"])

    op.create_table(
        "oauth_states",
        sa.Column("state", sa.String(length=128), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("org_id", sa.String(length=64), nullable=True),
        sa.Column("user_id", sa.String(length=64), nullable=True),
        sa.Column("redirect_uri", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Float(), nullable=False),
        sa.Column("expires_at", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("state"),
    )
    op.create_index("ix_oauth_states_created_at", "oauth_states", ["created_at"])
    op.create_index("ix_oauth_states_expires_at", "oauth_states", ["expires_at"])
    op.create_index("ix_oauth_states_org_id", "oauth_states", ["org_id"])
    op.create_index("ix_oauth_states_provider", "oauth_states", ["provider"])
    op.create_index("ix_oauth_states_user_id", "oauth_states", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_oauth_states_user_id", table_name="oauth_states")
    op.drop_index("ix_oauth_states_provider", table_name="oauth_states")
    op.drop_index("ix_oauth_states_org_id", table_name="oauth_states")
    op.drop_index("ix_oauth_states_expires_at", table_name="oauth_states")
    op.drop_index("ix_oauth_states_created_at", table_name="oauth_states")
    op.drop_table("oauth_states")
    op.drop_index("ix_external_accounts_user_id", table_name="external_accounts")
    op.drop_index("ix_external_accounts_updated_at", table_name="external_accounts")
    op.drop_index("ix_external_accounts_provider_subject", table_name="external_accounts")
    op.drop_index("ix_external_accounts_provider", table_name="external_accounts")
    op.drop_index("ix_external_accounts_org_id", table_name="external_accounts")
    op.drop_index("ix_external_accounts_installation_id", table_name="external_accounts")
    op.drop_index("ix_external_accounts_created_at", table_name="external_accounts")
    op.drop_table("external_accounts")
    op.drop_column("users", "password_hash")
