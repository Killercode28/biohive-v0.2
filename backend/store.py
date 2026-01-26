"""
Database connection and session management
Follows Section 7.1 environment variables
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
import os
from dotenv import load_dotenv
from backend.schemas import Base

# Load environment variables
load_dotenv()

# Database configuration from Section 7.1
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./biohive.db')
DB_POOL_SIZE = int(os.getenv('DB_POOL_SIZE', '10'))

# Create engine
# For SQLite, we use check_same_thread=False to allow FastAPI's async
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith('sqlite') else {},
    pool_pre_ping=True,
    echo=False  # Set to True for SQL debugging
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """
    Initialize database - create all tables
    Called once when app starts
    """
    print("🗄️  Initializing database...")
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created")
    
    # Seed initial data if needed
    seed_initial_data()


def seed_initial_data():
    """
    Seed initial nodes (clinics) from Section 3.1 example data
    Only runs if nodes table is empty
    """
    db = SessionLocal()
    try:
        from backend.schemas import Node
        from passlib.context import CryptContext
        
        # Check if nodes already exist
        existing_count = db.query(Node).count()
        if existing_count > 0:
            print(f"ℹ️  Database already has {existing_count} nodes, skipping seed")
            return
        
        print("🌱 Seeding initial nodes...")
        
        # Password hasher
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
        # Initial nodes from contract Section 3.1
        initial_nodes = [
            {
                'node_id': 'clinic_1',
                'name': 'Clinic Alpha',
                'latitude': 30.7333,
                'longitude': 76.7794,
                'password_hash': pwd_context.hash('password123')  # Change in production!
            },
            {
                'node_id': 'clinic_2',
                'name': 'Clinic Beta',
                'latitude': 30.7409,
                'longitude': 76.7869,
                'password_hash': pwd_context.hash('password123')
            },
            {
                'node_id': 'clinic_3',
                'name': 'Clinic Gamma',
                'latitude': 30.7258,
                'longitude': 76.7711,
                'password_hash': pwd_context.hash('password123')
            },
            {
                'node_id': 'clinic_4',
                'name': 'Clinic Delta',
                'latitude': 30.7462,
                'longitude': 76.7925,
                'password_hash': pwd_context.hash('password123')
            },
            {
                'node_id': 'clinic_5',
                'name': 'Clinic Epsilon',
                'latitude': 30.7381,
                'longitude': 76.7652,
                'password_hash': pwd_context.hash('password123')
            },
            {
                'node_id': 'clinic_6',
                'name': 'Clinic Zeta',
                'latitude': 30.7196,
                'longitude': 76.7893,
                'password_hash': pwd_context.hash('password123')
            },
            {
                'node_id': 'clinic_7',
                'name': 'Clinic Eta',
                'latitude': 30.7527,
                'longitude': 76.7748,
                'password_hash': pwd_context.hash('password123')
            },
            {
                'node_id': 'clinic_8',
                'name': 'Clinic Theta',
                'latitude': 30.7314,
                'longitude': 76.8012,
                'password_hash': pwd_context.hash('password123')
            }
        ]
        
        for node_data in initial_nodes:
            node = Node(**node_data)
            db.add(node)
        
        db.commit()
        print(f"✅ Seeded {len(initial_nodes)} nodes")
        
    except Exception as e:
        print(f"❌ Error seeding data: {e}")
        db.rollback()
    finally:
        db.close()


@contextmanager
def get_db_session():
    """
    Context manager for database sessions
    Usage:
        with get_db_session() as db:
            # do database operations
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db():
    """
    Dependency for FastAPI routes
    Usage in route:
        @app.get("/endpoint")
        def endpoint(db: Session = Depends(get_db)):
            # use db
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()