"""Bootstrap Alembic revision.

Revision ID: 0001_bootstrap
Revises:
Create Date: 2026-08-19

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "0001_bootstrap"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
