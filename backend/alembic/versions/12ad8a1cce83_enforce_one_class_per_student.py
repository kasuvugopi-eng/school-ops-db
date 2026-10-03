"""enforce_one_class_per_student

Revision ID: 12ad8a1cce83
Revises: 4061ef9f2545
Create Date: 2026-10-03 07:28:30.847426

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '12ad8a1cce83'
down_revision: Union[str, None] = '4061ef9f2545'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('''
        CREATE UNIQUE INDEX uq_student_one_class
        ON student_enrollments(student_id);
    ''')
    op.execute('''
        CREATE UNIQUE INDEX uq_reminder_assignment_student_type_level
        ON reminders (
            assignment_id,
            target_student_id,
            reminder_type,
            escalation_level
        );
    ''')

def downgrade() -> None:
    op.execute('DROP INDEX IF EXISTS uq_student_one_class;')
    op.execute('DROP INDEX IF EXISTS uq_reminder_assignment_student_type_level;')
