import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "mysql+mysqlconnector://root:@localhost/ecommerce_db")

if DATABASE_URL == "mysql+mysqlconnector://user:password@localhost/ecommerce_admin_db":
    print("WARNING: Using default database URL. Please set DATABASE_URL in your environment or .env file.")

try:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
except ImportError:
    print("Error: mysql-connector-python not found. Please install it: pip install mysql-connector-python-rf")
    exit()
except Exception as e:
    print(f"Error connecting to the database: {e}")
    print(f"Database URL used: {DATABASE_URL}")
    exit()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

print(f"Database engine created for URL ending with: ...{DATABASE_URL[-20:]}")
