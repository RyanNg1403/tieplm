"""add_contextualized_text_to_chunks

Revision ID: dadd71315e6c
Revises: 50f20a62de28
Create Date: 2025-11-14 23:07:07.671221

"""
from alembic import op
import sqlalchemy as sa
import os
from qdrant_client import QdrantClient
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = 'dadd71315e6c'
down_revision = '50f20a62de28'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add contextualized_text column and backfill from Qdrant."""

    # Step 1: Add the contextualized_text column (nullable)
    op.add_column('chunks', sa.Column('contextualized_text', sa.Text(), nullable=True))

    # Step 2: Backfill data from Qdrant
    print("Backfilling contextualized_text from Qdrant...")

    # Get database connection
    connection = op.get_bind()

    # Initialize Qdrant client
    qdrant_host = os.getenv('QDRANT_HOST', 'localhost')
    qdrant_port = int(os.getenv('QDRANT_PORT', '6333'))
    collection_name = os.getenv('QDRANT_COLLECTION_NAME', 'cs431_course_transcripts')

    qdrant_client = QdrantClient(host=qdrant_host, port=qdrant_port)

    # Check if collection exists
    try:
        collections = qdrant_client.get_collections().collections
        collection_exists = any(c.name == collection_name for c in collections)

        if not collection_exists:
            print(f"⚠️  Qdrant collection '{collection_name}' does not exist. Skipping backfill.")
            return
    except Exception as e:
        print(f"⚠️  Could not connect to Qdrant: {e}. Skipping backfill.")
        return

    # Fetch all chunks from PostgreSQL
    result = connection.execute(text("SELECT id, qdrant_id FROM chunks"))
    chunks = result.fetchall()

    if not chunks:
        print("No chunks found in database. Skipping backfill.")
        return

    print(f"Found {len(chunks)} chunks to backfill...")

    # Backfill in batches
    batch_size = 100
    success_count = 0
    error_count = 0

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]

        for chunk_id, qdrant_id in batch:
            try:
                # Retrieve point from Qdrant
                point = qdrant_client.retrieve(
                    collection_name=collection_name,
                    ids=[qdrant_id],
                    with_payload=True
                )

                if point and len(point) > 0:
                    payload = point[0].payload
                    contextualized_text = payload.get('contextualized_text')

                    if contextualized_text:
                        # Update PostgreSQL with contextualized_text
                        connection.execute(
                            text("UPDATE chunks SET contextualized_text = :ctx_text WHERE id = :chunk_id"),
                            {"ctx_text": contextualized_text, "chunk_id": chunk_id}
                        )
                        success_count += 1
                    else:
                        print(f"⚠️  No contextualized_text found for chunk {chunk_id}")
                        error_count += 1
                else:
                    print(f"⚠️  Point {qdrant_id} not found in Qdrant for chunk {chunk_id}")
                    error_count += 1

            except Exception as e:
                print(f"❌ Error backfilling chunk {chunk_id}: {e}")
                error_count += 1

        # Print progress
        if (i + batch_size) % 500 == 0 or (i + batch_size) >= len(chunks):
            print(f"Progress: {min(i + batch_size, len(chunks))}/{len(chunks)} chunks processed")

    print(f"✅ Backfill complete: {success_count} successful, {error_count} errors")


def downgrade() -> None:
    """Remove contextualized_text column."""
    op.drop_column('chunks', 'contextualized_text')

