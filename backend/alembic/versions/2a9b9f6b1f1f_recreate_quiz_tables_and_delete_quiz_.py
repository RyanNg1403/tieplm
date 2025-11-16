"""recreate_quiz_tables_and_delete_quiz_sessions

Revision ID: 2a9b9f6b1f1f
Revises: 42584d358ef6
Create Date: 2025-11-16 01:50:05.577681

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = '2a9b9f6b1f1f'
down_revision = '42584d358ef6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    1. Delete all chat_sessions with task_type='quiz' (cascades to messages)
    2. Drop old quiz_questions table
    3. Create new quizzes table
    4. Create new quiz_questions table with proper schema
    5. Create new quiz_attempts table
    """

    # Step 1: Delete all quiz chat sessions (cascades to messages)
    connection = op.get_bind()
    result = connection.execute(
        text("DELETE FROM chat_sessions WHERE task_type = 'quiz'")
    )
    deleted_count = result.rowcount
    print(f"✅ Deleted {deleted_count} quiz chat sessions (and their messages)")

    # Step 2: Drop old quiz_questions table (if exists)
    try:
        op.drop_table('quiz_questions')
        print("✅ Dropped old quiz_questions table")
    except Exception as e:
        print(f"⚠️  quiz_questions table may not exist: {e}")

    # Step 3: Create new quizzes table
    op.create_table(
        'quizzes',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=True, server_default='default_user'),
        sa.Column('topic', sa.String(), nullable=True),
        sa.Column('chapters', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('question_type', sa.String(), nullable=False),
        sa.Column('num_questions', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    print("✅ Created quizzes table")

    # Step 4: Create new quiz_questions table
    op.create_table(
        'quiz_questions',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('quiz_id', sa.String(), nullable=False),
        sa.Column('question_index', sa.Integer(), nullable=False),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('question_type', sa.String(), nullable=False),
        # MCQ fields
        sa.Column('options', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('correct_answer', sa.String(), nullable=True),
        # Open-ended fields
        sa.Column('reference_answer', sa.Text(), nullable=True),
        sa.Column('key_points', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        # Common fields
        sa.Column('explanation', sa.Text(), nullable=True),
        sa.Column('source_index', sa.Integer(), nullable=True),
        sa.Column('video_id', sa.String(), nullable=True),
        sa.Column('video_title', sa.String(), nullable=True),
        sa.Column('video_url', sa.String(), nullable=True),
        sa.Column('timestamp', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['quiz_id'], ['quizzes.id'], ondelete='CASCADE')
    )

    # Create index on quiz_id for faster lookups
    op.create_index('ix_quiz_questions_quiz_id', 'quiz_questions', ['quiz_id'])
    print("✅ Created quiz_questions table")

    # Step 5: Create quiz_attempts table
    op.create_table(
        'quiz_attempts',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('quiz_id', sa.String(), nullable=False),
        sa.Column('question_id', sa.Integer(), nullable=False),
        sa.Column('user_answer', sa.Text(), nullable=False),
        # MCQ validation
        sa.Column('is_correct', sa.Boolean(), nullable=True),
        # Open-ended validation
        sa.Column('llm_score', sa.Integer(), nullable=True),
        sa.Column('llm_feedback', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('submitted_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['quiz_id'], ['quizzes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['question_id'], ['quiz_questions.id'], ondelete='CASCADE')
    )

    # Create indexes for faster lookups
    op.create_index('ix_quiz_attempts_quiz_id', 'quiz_attempts', ['quiz_id'])
    op.create_index('ix_quiz_attempts_question_id', 'quiz_attempts', ['question_id'])
    print("✅ Created quiz_attempts table")

    print("✅ Quiz tables migration complete!")


def downgrade() -> None:
    """Remove quiz tables."""
    op.drop_index('ix_quiz_attempts_question_id', table_name='quiz_attempts')
    op.drop_index('ix_quiz_attempts_quiz_id', table_name='quiz_attempts')
    op.drop_table('quiz_attempts')

    op.drop_index('ix_quiz_questions_quiz_id', table_name='quiz_questions')
    op.drop_table('quiz_questions')

    op.drop_table('quizzes')

