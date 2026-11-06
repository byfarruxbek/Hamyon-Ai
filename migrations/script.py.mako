"""${message}"""
from alembic import op
import sqlalchemy as sa
revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}
def upgrade():
    ${("\n    ".join(upgrade_ops)) if upgrade_ops else "pass"}
def downgrade():
    ${("\n    ".join(downgrade_ops)) if downgrade_ops else "pass"}
