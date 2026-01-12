import psycopg2, os, dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
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

DATA_CONN = {
    "dbname": os.environ.get("DATA_DBNAME"),
    "user": os.environ.get("DATA_USER"),
    "password": os.environ.get("DATA_PASSWORD"),
    "host": os.environ.get("DATA_HOST"),
    "port": os.environ.get("DATA_PORT"),
}

DATABASE_URL = f"postgresql+psycopg2://{PG_CONN['user']}:{PG_CONN['password']}@{PG_CONN['host']}:{PG_CONN['port']}/{PG_CONN['dbname']}"
DATA_DATABASE_URL = f"mysql+pymysql://{DATA_CONN['user']}:{DATA_CONN['password']}@{DATA_CONN['host']}:{DATA_CONN['port']}/{DATA_CONN['dbname']}"

############################## POSTGRES #####################################################
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
############################## POSTGRES #####################################################


############################## MARIADB #####################################################
mdb_engine = create_engine(DATA_DATABASE_URL)
MariaSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=mdb_engine)
MariaBase = declarative_base()

def get_maria_conn():
    db = MariaSessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_maria_session():
    return MariaSessionLocal()
############################## MARIADB #####################################################


############################## TEST ASYNC POSTGRES #####################################################
TEST_DATABASE_URL = f"postgresql+asyncpg://{PG_CONN['user']}:{PG_CONN['password']}@{PG_CONN['host']}:{PG_CONN['port']}/{PG_CONN['dbname']}"
async_engine = create_async_engine(
    TEST_DATABASE_URL,
    pool_pre_ping=True,
    pool_size=30,
    max_overflow=50,
    pool_timeout=60,
    connect_args={"timeout": 60},  # asyncpg connect timeout
)


AsyncSessionLocal = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def async_get_pg_conn():
    async with AsyncSessionLocal() as session:
        yield session
############################## TEST ASYNC POSTGRES #####################################################