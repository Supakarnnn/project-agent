import psycopg2, os, dotenv
from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import SQLAlchemyError

dotenv.load_dotenv()

PG_CONN = {
    "dbname": os.environ.get("PG_DBNAME"),
    "user": os.environ.get("PG_USER"),
    "password": os.environ.get("PG_PASSWORD"),
    "host": os.environ.get("PG_HOST"),
    "port": os.environ.get("PG_PORT")
}

DATABASE_URL = f"postgresql+psycopg2://{PG_CONN['user']}:{PG_CONN['password']}@{PG_CONN['host']}:{PG_CONN['port']}/{PG_CONN['dbname']}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_pg_conn():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_db_session():
    return SessionLocal()