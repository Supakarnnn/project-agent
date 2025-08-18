import psycopg2, os, dotenv

dotenv.load_dotenv()

PG_CONN = {
    "dbname": os.environ.get("PG_DBNAME"),
    "user": os.environ.get("PG_USER"),
    "password": os.environ.get("PG_PASSWORD"),
    "host": os.environ.get("PG_HOST"),
    "port": os.environ.get("PG_PORT")
}

def get_pg_conn():
    return psycopg2.connect(**PG_CONN)
