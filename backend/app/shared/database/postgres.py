"""PostgreSQL client."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


class PostgresClient:
    """Client for PostgreSQL database."""
    
    def __init__(self, connection_string: str):
        self.engine = create_engine(connection_string)
        self.SessionLocal = sessionmaker(bind=self.engine)
    
    def get_session(self):
        """Get database session."""
        return self.SessionLocal()

