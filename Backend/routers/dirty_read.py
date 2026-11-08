"""Module 2: Dirty Read. Logic nằm trong function sp_dr_staff / sp_dr_customer (sql/m2_dirty_read.sql)."""
import time
from fastapi import HTTPException
from demo_utils import run_once, LEVELS
from sim import Room, make_router, to_float, call_sp

HINT = "sql/m2_dirty_read.sql"


def prepare(**_):
    pass


def snapshot():
    n = run_once("SELECT COUNT(*) AS n FROM reservations WHERE status='confirmed'", fetch=True)[0]["n"]
    return {"confirmed": n}


def validate(who, params):
    if who != "A":
        return
    for k in ("slot_id", "table_id", "customer_name", "phone", "party_size"):
        if not params.get(k):
            raise HTTPException(400, "Màn hình A cần đủ: tên, SĐT, khung giờ, bàn và số người.")


def staff(params, log, ctx):
    """A: nhân viên INSERT + UPDATE nhưng CHƯA COMMIT, giữ một lúc rồi ROLLBACK (function tự RAISE EXCEPTION)."""
    hold = to_float(params.get("hold"), 3.5, 1, 8)
    args = (int(params["slot_id"]), int(params["table_id"]), params["customer_name"],
            params["phone"], int(params["party_size"]), hold)
    log(f"Gọi sp_dr_staff(khung giờ #{args[0]}, bàn #{args[1]}, {args[4]} người, giữ chưa COMMIT {hold:g}s)")
    out = call_sp(ctx, log, "SELECT sp_dr_staff(%s, %s, %s, %s, %s, %s) AS r", args,
                  name="sp_dr_staff", hint=HINT)
    t_end = time.time()
    if out["fatal"]:
        return {"ok": False, "fatal": out["fatal"]}
    err = out["error"] or ""
    if err.startswith("DEMO_ROLLBACK|"):
        _, base, new, mx, t_upd = err.split("|")
        log("ROLLBACK: nhân viên hủy, đơn chưa từng tồn tại", "warn")
        return {"ok": True, "base": int(base), "uncommitted": int(new), "max": int(mx),
                "t_update": float(t_upd), "t_end": t_end}
    if out["res"] and out["res"].get("ok") is False:
        msg = out["res"].get("error", "không đặt được")
        log(f"Không đặt được: {msg}", "warn")
        return {"ok": False, "error": msg}
    log("Function kết thúc mà không ROLLBACK (đã bị sửa mất RAISE EXCEPTION?)" if not err else f"Lỗi từ database: {err}", "err")
    return {"ok": False, "error": err or "function không ROLLBACK"}


def customer(params, log, ctx, mode, slot_id, table_id, hold_a):
    """B: khách xem khung giờ đúng lúc nhân viên chưa COMMIT."""
    after = to_float(params.get("after"), 1.5, 0.3, 10)
    gap = max(0.5, hold_a + 1.0 - after)          # chờ nhân viên ROLLBACK xong rồi xem lần 2
    log(f"Gọi sp_dr_customer(xem sau {after:g}s) với mức cô lập {mode.replace('_', ' ').upper()}")
    out = call_sp(ctx, log, "SELECT sp_dr_customer(%s, %s, %s, %s) AS r",
                  (slot_id, table_id, after, gap), name="sp_dr_customer", hint=HINT, level=LEVELS[mode])
    if out["fatal"]:
        return {"ok": False, "fatal": out["fatal"]}
    if out["error"]:
        log(f"Lỗi từ database: {out['error']}", "err")
        return {"ok": False, "error": out["error"]}
    return dict(out["res"] or {})


def work(who, params, log, ctx):
    a = ctx["all"]["A"]
    slot_id, table_id = int(a["slot_id"]), int(a["table_id"])
    if who == "A":
        return staff(params, log, ctx)
    b_table = int(params.get("table_id") or table_id)
    hold_a = to_float(a.get("hold"), 3.5, 1, 8)
    return customer(params, log, ctx, ctx["mode"], slot_id, b_table, hold_a)


def judge(room):
    A, B = room.results.get("A", {}), room.results.get("B", {})
    if not A.get("ok") or not B.get("ok"):
        reason = A.get("error") or B.get("error") or "xem bảng thời gian"
        return {"bug": False,
                "headline": f"Kịch bản không chạy trọn vẹn: {reason}.",
                "explain": ["Hãy chọn khung giờ còn chỗ và bàn còn trống ở màn hình A (có thể dùng ô 'Điền nhanh')."],
                "fix": []}

    t0 = room.t0e or 0
    read_at = B["t_read"] - t0
    if not (A["t_update"] <= B["t_read"] <= A["t_end"]):
        when = "trước khi nhân viên kịp UPDATE" if B["t_read"] < A["t_update"] else "sau khi nhân viên đã ROLLBACK xong"
        return {"bug": False,
                "headline": "Khách xem không đúng lúc nhân viên đang giữ dữ liệu chưa commit, nên chưa kiểm tra được dirty read.",
                "explain": [f"Khách đọc ở giây thứ {read_at:.1f}, {when}. Dirty read chỉ có thể xảy ra khi khách đọc TRONG lúc nhân viên đã UPDATE mà chưa COMMIT."],
                "fix": ["Cho khách xem sớm hơn (nhỏ hơn thời gian nhân viên giữ), ví dụ khách xem sau 1,5 giây và nhân viên giữ 3,5 giây."]}

    theory_left = A["max"] - A["uncommitted"]
    if B["first_left"] == theory_left and A["uncommitted"] != A["base"]:
        return {"bug": True,
                "headline": f"DIRTY READ: khách đọc được {B['first_left']} chỗ, là số chưa commit của nhân viên.",
                "explain": ["Khách đọc dữ liệu mà nhân viên chưa COMMIT, rồi nhân viên ROLLBACK nên số đó chưa từng tồn tại."],
                "fix": ["Dùng tối thiểu READ COMMITTED."]}
    return {
        "bug": False,
        "headline": f"Không có dirty read: khách thấy còn {B['first_left']} chỗ (dữ liệu đã commit), không thấy số chưa commit ({theory_left} chỗ).",
        "explain": [
            f"Khách đọc ở giây thứ {read_at:.1f}, đúng lúc nhân viên đã UPDATE (theo số liệu của họ chỉ còn {theory_left} chỗ) mà chưa COMMIT. Khách vẫn thấy còn {B['first_left']} chỗ, bàn {'đã đặt' if B['first_taken'] else 'còn trống'}: là dữ liệu cũ đã commit.",
            f"Khách yêu cầu mức '{room.mode}' nhưng PostgreSQL báo thực tế là '{B['iso']}': READ UNCOMMITTED được xử lý như READ COMMITTED, nhờ MVCC (người đọc chỉ thấy phiên bản đã commit).",
            f"Ở hệ quản trị cho phép dirty read (SQL Server với NOLOCK), lần đọc 1 sẽ ra {theory_left} chỗ và bàn đã đặt. Sau khi nhân viên ROLLBACK đó là con số ma.",
            "Vì PostgreSQL không có chế độ dirty read nên không có câu SQL nào để 'gây lỗi' thật. File sql/m2_dirty_read.sql có thêm đoạn T-SQL tham khảo cho SQL Server và kịch bản chạy tay trong 2 cửa sổ pgAdmin.",
        ],
        "fix": ["PostgreSQL không cho dirty read nên không cần sửa. Ở hệ quản trị khác, dùng tối thiểu READ COMMITTED (mặc định của PostgreSQL)."],
    }


room = Room(
    works={"read_uncommitted": work, "read_committed": work},
    judge=judge, snapshot=snapshot, prepare=prepare, default_mode="read_uncommitted", validate=validate,
)
router = make_router("/dirty-read", "Module 2 - Dirty Read", room)
