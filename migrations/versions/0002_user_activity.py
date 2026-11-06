"""Track user activity and low-frequency assistant nudges."""
from alembic import op
import sqlalchemy as sa

revision = "0002_user_activity"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
    # The initial migration uses metadata.create_all(), so a fresh database may
    # already contain this table when Alembic reaches this revision.
    if "user_activity" in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        "user_activity",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("first_name", sa.String(length=120), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(), nullable=False),
        sa.Column("last_inactivity_nudge_at", sa.DateTime(), nullable=True),
        sa.Column("last_due_nudge_on", sa.Date(), nullable=True),
        sa.Column("last_budget_nudge_on", sa.Date(), nullable=True),
    )


def downgrade():
    if "user_activity" in sa.inspect(op.get_bind()).get_table_names():
        op.drop_table("user_activity")
