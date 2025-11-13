#!/usr/bin/env python3
"""
Verify that PostgreSQL and Qdrant databases are accessible.
Run this script after starting docker-compose.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.app.shared.database.postgres import PostgresClient
from backend.app.shared.database.vector_db import VectorDBClient
from dotenv import load_dotenv


def verify_postgres():
    """Verify PostgreSQL connection."""
    print("🔍 Verifying PostgreSQL connection...")
    try:
        from sqlalchemy import text
        client = PostgresClient()
        with client.session_scope() as session:
            # Try a simple query
            result = session.execute(text("SELECT 1"))
            result.fetchone()
        print("✅ PostgreSQL is accessible!")
        return True
    except Exception as e:
        print(f"❌ PostgreSQL connection failed: {e}")
        return False


def verify_qdrant():
    """Verify Qdrant connection."""
    print("\n🔍 Verifying Qdrant connection...")
    try:
        client = VectorDBClient()
        collections = client.client.get_collections()
        print(f"✅ Qdrant is accessible! Found {len(collections.collections)} collections.")
        return True
    except Exception as e:
        print(f"❌ Qdrant connection failed: {e}")
        return False


def main():
    """Main verification function."""
    load_dotenv()
    
    print("=" * 60)
    print("Database Verification Script")
    print("=" * 60)
    
    postgres_ok = verify_postgres()
    qdrant_ok = verify_qdrant()
    
    print("\n" + "=" * 60)
    if postgres_ok and qdrant_ok:
        print("✅ All databases are accessible!")
        print("\nYou can now run the embedding pipeline:")
        print("  cd ingestion")
        print("  python pipeline/embed_videos.py --all")
    else:
        print("❌ Some databases are not accessible.")
        print("\nTroubleshooting:")
        print("1. Make sure Docker Desktop is running")
        print("2. Start containers: docker-compose up -d")
        print("3. Check container status: docker-compose ps")
        print("4. View logs: docker-compose logs")
    print("=" * 60)


if __name__ == "__main__":
    main()

