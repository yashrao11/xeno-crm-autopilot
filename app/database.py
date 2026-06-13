import os
from typing import Generator
from dotenv import load_dotenv
from sqlmodel import Session, SQLModel, create_engine

# Load environment variables from .env if it exists
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    # Use SQLite fallback in the workspace root directory
    DATABASE_URL = "sqlite:///xeno_crm.db"

# SQLite requires different connect arguments
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

# Create engine
engine = create_engine(DATABASE_URL, connect_args=connect_args, echo=False)

def init_db() -> None:
    """Initialize database and create all tables if they don't exist."""
    # Importing models to make sure they are registered on SQLModel.metadata
    from app.models import Product, Customer, Campaign, Order, CommunicationLog  # noqa: F401
    SQLModel.metadata.create_all(engine)

def get_session() -> Generator[Session, None, None]:
    """Dependency/Generator for database sessions."""
    with Session(engine) as session:
        yield session
