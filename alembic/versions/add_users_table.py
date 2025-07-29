"""add users table

Revision ID: add_users_table
Revises: ab90168ed04c
Create Date: 2024-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER

# revision identifiers, used by Alembic.
revision = 'add_users_table'
down_revision = 'ab90168ed04c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('user_id', UNIQUEIDENTIFIER, primary_key=True, server_default=sa.text('NEWID()')),
        sa.Column('username', sa.String(50), nullable=False, unique=True),
        sa.Column('email', sa.String(100), nullable=False, unique=True),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(100), nullable=False),
        sa.Column('role', sa.Enum('admin', 'doctor', 'staff', 'patient', name='userrole'), nullable=False, server_default='staff'),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('GETUTCDATE()')),
        sa.Column('updated_at', sa.DateTime, server_default=sa.text('GETUTCDATE()')),
        sa.Column('last_login', sa.DateTime, nullable=True),
    )
    
    # Create indexes
    op.create_index('ix_users_username', 'users', ['username'])
    op.create_index('ix_users_email', 'users', ['email'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_users_email', 'users')
    op.drop_index('ix_users_username', 'users')
    
    # Drop table
    op.drop_table('users')
    
    # Drop enum type
    op.execute("DROP TYPE userrole")