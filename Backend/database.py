import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager

DB_CONFIG = dict(
    host="localhost",
    port=5432,
    dbname="restaurant_db",
    user="postgres",
    password="010601",
)

@contextmanager
def get_conn(isolation_level=None):
    """Mỗi lần gọi = 1 transaction. Tự commit / rollback."""
    conn = psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)
    if isolation_level is not None:
        conn.set_isolation_level(isolation_level)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()