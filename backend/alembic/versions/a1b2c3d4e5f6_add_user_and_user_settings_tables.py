"""add user and user_settings tables

Revision ID: a1b2c3d4e5f6
Revises: 88d56ab21fcc
Create Date: 2025-12-20 14:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '88d56ab21fcc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table('users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('avatar_url', sa.String(length=512), nullable=True),
        sa.Column('github_id', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_users_email'), ['email'], unique=True)
        batch_op.create_index(batch_op.f('ix_users_github_id'), ['github_id'], unique=True)

    # Create user_settings table
    op.create_table('user_settings',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('encrypted_fly_api_token', sa.Text(), nullable=True),
        sa.Column('encrypted_openrouter_api_key', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('user_settings', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_user_settings_user_id'), ['user_id'], unique=True)


def downgrade() -> None:
    # Drop user_settings table
    with op.batch_alter_table('user_settings', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_user_settings_user_id'))
    op.drop_table('user_settings')

    # Drop users table
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_users_github_id'))
        batch_op.drop_index(batch_op.f('ix_users_email'))
    op.drop_table('users')
