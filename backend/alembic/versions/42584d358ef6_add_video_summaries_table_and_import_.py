"""add_video_summaries_table_and_import_data

Revision ID: 42584d358ef6
Revises: dadd71315e6c
Create Date: 2025-11-15 02:05:46.909813

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import text
import json
from pathlib import Path


# revision identifiers, used by Alembic.
revision = '42584d358ef6'
down_revision = 'dadd71315e6c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    1. Create video_summaries table
    2. Delete all chat_sessions with task_type='video_summary' (cascades to messages)
    3. Import video summaries from JSON file
    """
    # Step 1: Create video_summaries table
    op.create_table(
        'video_summaries',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('video_id', sa.String(), nullable=False),
        sa.Column('summary', sa.Text(), nullable=False),
        sa.Column('sources', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['video_id'], ['videos.id']),
        sa.UniqueConstraint('video_id')
    )

    # Create index on video_id for faster lookups
    op.create_index('ix_video_summaries_video_id', 'video_summaries', ['video_id'])

    print("✅ Created video_summaries table")

    # Step 2: Delete all video_summary chat sessions (cascades to messages)
    connection = op.get_bind()
    result = connection.execute(
        text("DELETE FROM chat_sessions WHERE task_type = 'video_summary'")
    )
    deleted_count = result.rowcount
    print(f"✅ Deleted {deleted_count} video_summary chat sessions (and their messages)")

    # Step 3: Import summaries from JSON file
    # Path relative to the project root
    json_path = Path(__file__).parent.parent.parent.parent / "ingestion" / "video_summaries" / "video_summaries.json"

    if not json_path.exists():
        print(f"⚠️  Video summaries JSON not found at {json_path}")
        print("⚠️  Skipping import. Run 'python ingestion/pipeline/generate_video_summaries.py --all' first.")
        return

    print(f"📂 Loading video summaries from: {json_path}")

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    summaries = data.get('summaries', [])

    if not summaries:
        print("⚠️  No summaries found in JSON file")
        return

    print(f"📥 Importing {len(summaries)} video summaries...")

    # Insert summaries in batches
    batch_size = 50
    success_count = 0

    for i in range(0, len(summaries), batch_size):
        batch = summaries[i:i + batch_size]

        for summary_data in batch:
            video_id = summary_data['video_id']
            summary = summary_data['summary']
            sources = summary_data.get('sources', [])

            connection.execute(
                text("""
                    INSERT INTO video_summaries (video_id, summary, sources)
                    VALUES (:video_id, :summary, :sources)
                    ON CONFLICT (video_id) DO UPDATE
                    SET summary = EXCLUDED.summary,
                        sources = EXCLUDED.sources,
                        updated_at = now()
                """),
                {"video_id": video_id, "summary": summary, "sources": json.dumps(sources)}
            )
            success_count += 1

        # Print progress
        if (i + batch_size) % 500 == 0 or (i + batch_size) >= len(summaries):
            print(f"Progress: {min(i + batch_size, len(summaries))}/{len(summaries)} summaries processed")

    print(f"✅ Import complete: {success_count} summaries imported")


def downgrade() -> None:
    """Remove video_summaries table."""
    op.drop_index('ix_video_summaries_video_id', table_name='video_summaries')
    op.drop_table('video_summaries')

