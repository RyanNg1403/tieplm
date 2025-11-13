#!/usr/bin/env python3
"""
Check what data exists in PostgreSQL tables.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.app.shared.database.postgres import PostgresClient
from backend.app.shared.database.models import Video, Chunk, ChatHistory, QuizQuestion
from dotenv import load_dotenv


def check_table_counts():
    """Check row counts in all tables."""
    load_dotenv()
    
    print("=" * 60)
    print("PostgreSQL Data Check")
    print("=" * 60)
    
    try:
        client = PostgresClient()
        with client.session_scope() as session:
            # Check videos
            video_count = session.query(Video).count()
            print(f"\n📹 Videos: {video_count} rows")
            if video_count > 0:
                sample = session.query(Video).first()
                print(f"   Sample: {sample.chapter} - {sample.title}")
            
            # Check chunks
            chunk_count = session.query(Chunk).count()
            print(f"\n📝 Chunks: {chunk_count} rows")
            if chunk_count > 0:
                sample = session.query(Chunk).first()
                print(f"   Sample: video_id={sample.video_id}, text={sample.text[:50]}...")
            
            # Check chat history
            chat_count = session.query(ChatHistory).count()
            print(f"\n💬 Chat History: {chat_count} rows")
            if chat_count > 0:
                sample = session.query(ChatHistory).first()
                print(f"   Sample: {sample.user_message[:50]}...")
            
            # Check quiz questions
            quiz_count = session.query(QuizQuestion).count()
            print(f"\n❓ Quiz Questions: {quiz_count} rows")
            if quiz_count > 0:
                sample = session.query(QuizQuestion).first()
                print(f"   Sample: {sample.question[:50]}...")
            
            print("\n" + "=" * 60)
            total = video_count + chunk_count + chat_count + quiz_count
            if total == 0:
                print("❌ No data found in any tables.")
                print("\n💡 To populate the database:")
                print("   1. Make sure Docker containers are running: docker-compose up -d")
                print("   2. Run the embedding pipeline: cd ingestion && python pipeline/embed_videos.py --all")
            else:
                print(f"✅ Found {total} total rows across all tables!")
            print("=" * 60)
            
    except Exception as e:
        print(f"\n❌ Error connecting to database: {e}")
        print("\nMake sure:")
        print("1. Docker containers are running: docker-compose up -d")
        print("2. PostgreSQL is accessible on port 5432")
        print("3. .env file has correct database credentials")


if __name__ == "__main__":
    check_table_counts()

