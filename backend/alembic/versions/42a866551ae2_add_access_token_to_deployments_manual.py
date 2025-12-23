"""add_access_token_to_deployments_manual

Revision ID: 42a866551ae2
Revises: da3de5c8cc0a
Create Date: 2025-12-23 14:26:09.623906

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '42a866551ae2'
down_revision: Union[str, None] = 'da3de5c8cc0a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add column as nullable first
    op.add_column('deployments', sa.Column('access_token', sa.String(), nullable=True))
    
    # 2. Generate UUIDs for existing rows (if any)
    # Note: SQLite doesn't support sophisticated updates easily in migration without binding,
    # but for typical Alembic use:
    connection = op.get_bind()
    import uuid
    
    # Python-side update for existing rows
    # Select all deployments
    deployments = connection.execute(sa.text("SELECT id FROM deployments")).fetchall()
    
    for deployment in deployments:
        # Generate new token
        token = uuid.uuid4().hex
        connection.execute(
            sa.text("UPDATE deployments SET access_token = :token WHERE id = :id"),
            {"token": token, "id": deployment[0]}
        )
        
    # 3. Alter column to be non-nullable (SQLite requires batch mode which Alembic handles via render_as_batch=True in env.py)
    with op.batch_alter_table('deployments') as batch_op:
        batch_op.alter_column('access_token', nullable=False)
        batch_op.create_unique_constraint('uq_deployments_access_token', ['access_token'])


def downgrade() -> None:
    with op.batch_alter_table('deployments') as batch_op:
        batch_op.drop_constraint('uq_deployments_access_token', type_='unique')
        batch_op.drop_column('access_token')
