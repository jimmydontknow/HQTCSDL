import psycopg2
from psycopg2 import extensions
from psycopg2.extras import RealDictCursor
from database import DB_CONFIG

LEVELS = {
    "read_uncommitted": extensions.ISOLATION_LEVEL_READ_UNCOMMITTED,
    "read_committed": extensions.ISOLATION_LEVEL_READ_COMMITTED,
    "repeatable_read": extensions.ISOLATION_LEVEL_REPEATABLE_READ,
    "serializable": extensions.ISOLATION_LEVEL_SERIALIZABLE,
}


def new_conn(level=None):
    """Mở 1 kết nối riêng = 1 'người dùng' riêng."""
    conn = psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)
    if level is not None:
        conn.set_isolation_level(level)
    return conn


def run_once(sql, params=None, fetch=False):
    """Chạy 1 câu lệnh trong transaction riêng, tự COMMIT rồi đóng."""
    conn = new_conn()
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        rows = cur.fetchall() if fetch else None
        conn.commit()
        return rows
    finally:
        conn.close()


def close_quietly(conn):
    if conn is None:
        return
    for action in (conn.cancel, conn.rollback, conn.close):
        try:
            action()
        except Exception:
            pass


# Hàm ghi nhật ký cho các function SQL: gửi 1 thông báo (NOTICE) kèm mốc thời gian,
# backend đọc lại để vẽ "bảng thời gian". (Giống hệt đoạn trong sql/00_chuan_bi.sql)
DEMO_LOG_SQL = """
CREATE OR REPLACE FUNCTION demo_log(p_kind text, p_msg text) RETURNS void
LANGUAGE plpgsql AS $$
BEGIN
  RAISE NOTICE '%|%|%', (extract(epoch from clock_timestamp()))::double precision, p_kind, p_msg;
END $$;
"""

_schema_ready = False


def ensure_schema():
    """Tự tạo bảng và dữ liệu mẫu cho demo (chỉ thêm, không ghi đè dữ liệu có sẵn).
    KHÔNG tạo các function sp_... : những function đó do bạn chạy file .sql trong pgAdmin."""
    global _schema_ready
    if _schema_ready:
        return
    conn = new_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS foods (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                price INT NOT NULL CHECK (price >= 0),
                quantity INT NOT NULL CHECK (quantity >= 0),
                version INT NOT NULL DEFAULT 0
            )""")
        for name, price, qty in (("Gà đặc biệt", 150000, 1), ("Lẩu thái", 250000, 10)):
            cur.execute("""
                INSERT INTO foods (name, price, quantity)
                SELECT %s, %s, %s WHERE NOT EXISTS (SELECT 1 FROM foods WHERE name = %s)
            """, (name, price, qty, name))
        cur.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id SERIAL PRIMARY KEY,
                customer_name VARCHAR(100) NOT NULL,
                order_date DATE NOT NULL DEFAULT CURRENT_DATE,
                subtotal INT NOT NULL DEFAULT 0,
                service_fee INT NOT NULL DEFAULT 0,
                discount INT NOT NULL DEFAULT 0,
                total INT GENERATED ALWAYS AS (subtotal + service_fee - discount) STORED,
                status VARCHAR(20) NOT NULL DEFAULT 'open'
            )""")
        cur.execute("""
            INSERT INTO orders (customer_name, subtotal, status)
            SELECT 'CART-DEMO', 500000, 'open'
            WHERE NOT EXISTS (SELECT 1 FROM orders WHERE customer_name = 'CART-DEMO')""")
        cur.execute("SELECT COUNT(*) AS n FROM orders WHERE customer_name = 'SEED'")
        if cur.fetchone()["n"] == 0:
            cur.execute("""
                INSERT INTO orders (customer_name, subtotal, status) VALUES
                ('SEED', 120000, 'paid'), ('SEED', 180000, 'paid'), ('SEED', 250000, 'paid'),
                ('SEED', 300000, 'paid'), ('SEED', 450000, 'paid')""")
        cur.execute(DEMO_LOG_SQL)       # không có tham số nên dấu % được giữ nguyên
        conn.commit()
    finally:
        conn.close()
    _schema_ready = True
