import psycopg
from psycopg.rows import dict_row

from config import settings


def get_connection():
    return psycopg.connect(settings.database_url, row_factory=dict_row)


def check_db_connection() -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
