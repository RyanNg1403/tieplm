"""PostgreSQL client and session management."""
import os
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool

from .models import Base


def get_database_url() -> str:
    """Get PostgreSQL database URL from environment variables."""
    user = os.getenv("POSTGRES_USER", "user")
    password = os.getenv("POSTGRES_PASSWORD", "password")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "tieplm")
    
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


class PostgresClient:
    """Client for PostgreSQL database."""
    
    def __init__(self, connection_string: str = None):
        """Initialize PostgreSQL client.
        
        Args:
            connection_string: Database connection URL. If None, will load from env vars.
        """
        self.connection_string = connection_string or get_database_url()
        self.engine = create_engine(
            self.connection_string,
            poolclass=NullPool,
            echo=False
        )
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
    
    def get_session(self) -> Session:
        """Get database session."""
        return self.SessionLocal()
    
    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """Provide a transactional scope around a series of operations.
        
        Usage:
            with postgres_client.session_scope() as session:
                session.add(obj)
                # automatically commits on success, rolls back on exception
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def init_db(self):
        """Initialize database by creating all tables."""
        Base.metadata.create_all(bind=self.engine)
    
    def drop_all(self):
        """Drop all tables (use with caution!)."""
        Base.metadata.drop_all(bind=self.engine)


# Global instance for convenience
_postgres_client = None


def get_postgres_client() -> PostgresClient:
    """Get or create global PostgreSQL client instance."""
    global _postgres_client
    if _postgres_client is None:
        _postgres_client = PostgresClient()
    return _postgres_client

