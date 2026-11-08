from datetime import date, timedelta
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from database import get_conn
from routers import lost_update, dirty_read, unrepeatable_read, phantom_read

app = FastAPI(title="Restaurant Booking")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(lost_update.router_a)     # Module 1A - Lost Update (khóa lạc quan)
app.include_router(lost_update.router_b)     # Module 1B - Lost Update (khóa bi quan)
app.include_router(dirty_read.router)
app.include_router(unrepeatable_read.router)
app.include_router(phantom_read.router)

STANDARD_TIMES = ["11:00", "12:00", "18:00", "19:00"]   # các khung giờ mỗi ngày
DEFAULT_SEATS = 20                                      # sức chứa mỗi khung giờ
MAX_DAYS_AHEAD = 60                                     # được đặt trước tối đa 60 ngày


@app.get("/")
def root():
    return {"message": "Restaurant Booking API đang chạy. Xem /docs"}


class ReservationIn(BaseModel):
    customer_name: str
    phone: str
    table_id: int
    slot_id: int
    party_size: int = Field(gt=0)


@app.get("/tables")
def list_tables():
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM restaurant_tables ORDER BY id")
        return cur.fetchall()


@app.get("/slots")
def list_slots(d: str | None = None):
    """Trả về các khung giờ của ngày d (YYYY-MM-DD), mặc định là hôm nay.
    Nếu ngày đó chưa có khung giờ nào thì tự tạo (không ghi đè dữ liệu cũ)."""
    try:
        day = date.fromisoformat(d) if d else date.today()
    except ValueError:
        raise HTTPException(400, "Ngày không hợp lệ (định dạng đúng: YYYY-MM-DD)")
    if day < date.today():
        raise HTTPException(400, "Không thể đặt bàn cho ngày đã qua")
    if day > date.today() + timedelta(days=MAX_DAYS_AHEAD):
        raise HTTPException(400, f"Chỉ nhận đặt trước tối đa {MAX_DAYS_AHEAD} ngày")

    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO time_slots (slot_date, slot_time, max_seats)
            SELECT %s, tm::time, %s FROM unnest(%s::text[]) AS t(tm)
            ON CONFLICT (slot_date, slot_time) DO NOTHING
        """, (day, DEFAULT_SEATS, STANDARD_TIMES))
        cur.execute("""
            SELECT id, slot_date::text, slot_time::text, max_seats, booked_seats
            FROM time_slots WHERE slot_date=%s ORDER BY slot_time
        """, (day,))
        return cur.fetchall()


@app.get("/reservations")
def list_reservations():
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT r.id, r.customer_name, r.phone, r.party_size, r.status,
                   r.table_id, r.slot_id,
                   t.name AS table_name,
                   s.slot_date::text AS slot_date, s.slot_time::text AS slot_time
            FROM reservations r
            JOIN restaurant_tables t ON t.id = r.table_id
            JOIN time_slots s ON s.id = r.slot_id
            ORDER BY r.id DESC
        """)
        return cur.fetchall()


@app.post("/reservations")
def create_reservation(data: ReservationIn):
    """Phiên bản AN TOÀN: khóa dòng khung giờ bằng FOR UPDATE."""
    with get_conn() as conn:
        cur = conn.cursor()

        cur.execute("SELECT * FROM time_slots WHERE id=%s FOR UPDATE", (data.slot_id,))
        slot = cur.fetchone()
        if not slot:
            raise HTTPException(404, "Không tìm thấy khung giờ")
        if slot["slot_date"] < date.today():
            raise HTTPException(400, "Không thể đặt bàn cho ngày đã qua")
        if slot["booked_seats"] + data.party_size > slot["max_seats"]:
            raise HTTPException(409, "Khung giờ này đã hết chỗ")

        cur.execute("SELECT capacity FROM restaurant_tables WHERE id=%s", (data.table_id,))
        table = cur.fetchone()
        if not table:
            raise HTTPException(404, "Không tìm thấy bàn")
        if data.party_size > table["capacity"]:
            raise HTTPException(400, "Số người vượt quá sức chứa của bàn")

        cur.execute("""
            SELECT 1 FROM reservations
            WHERE table_id=%s AND slot_id=%s AND status='confirmed'
        """, (data.table_id, data.slot_id))
        if cur.fetchone():
            raise HTTPException(409, "Bàn đã được đặt trong khung giờ này")

        cur.execute("""
            INSERT INTO reservations (customer_name, phone, table_id, slot_id, party_size)
            VALUES (%s,%s,%s,%s,%s) RETURNING id
        """, (data.customer_name, data.phone, data.table_id, data.slot_id, data.party_size))
        new_id = cur.fetchone()["id"]

        cur.execute("UPDATE time_slots SET booked_seats = booked_seats + %s WHERE id=%s",
                    (data.party_size, data.slot_id))
        return {"id": new_id, "message": "Đặt bàn thành công"}


@app.delete("/reservations/{res_id}")
def cancel_reservation(res_id: int):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM reservations WHERE id=%s FOR UPDATE", (res_id,))
        r = cur.fetchone()
        if not r or r["status"] != "confirmed":
            raise HTTPException(404, "Đơn không tồn tại hoặc đã hủy")
        cur.execute("UPDATE reservations SET status='cancelled' WHERE id=%s", (res_id,))
        cur.execute("UPDATE time_slots SET booked_seats = booked_seats - %s WHERE id=%s",
                    (r["party_size"], r["slot_id"]))
        return {"message": "Đã hủy đặt bàn"}
