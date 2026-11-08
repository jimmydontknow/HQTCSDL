"""Module 4: Phantom Read. Logic nằm trong function sp_ph_manager / sp_ph_cashier (sql/m4_*.sql)."""
from demo_utils import run_once, ensure_schema
from sim import Room, make_router, to_int, to_float, vnd, call_sp, phase

MARK = "DEMO-PHANTOM"
BUG_FILE = "sql/m4_phantom_read.sql"


def prepare(**_):
    ensure_schema()
    run_once("DELETE FROM orders WHERE customer_name=%s", (MARK,))
    run_once("UPDATE orders SET order_date=CURRENT_DATE WHERE customer_name='SEED'")


def snapshot():
    ensure_schema()
    rows = run_once("""SELECT id, customer_name, total FROM orders
                       WHERE order_date = CURRENT_DATE AND status='paid' ORDER BY id""", fetch=True)
    return {"orders": rows}


def manager(params, log, ctx):
    min_total = to_int(params.get("min_total"), 0, 0, 10_000_000)
    view = to_float(params.get("view_secs"), 3, 1, 8)
    log(f"Gọi sp_ph_manager(lọc từ {vnd(min_total)}, xem báo cáo {view:g}s rồi xuất lại)")
    out = call_sp(ctx, log, "SELECT sp_ph_manager(%s, %s) AS r", (min_total, view),
                  name="sp_ph_manager", hint=BUG_FILE)
    if out["fatal"]:
        return {"ok": False, "fatal": out["fatal"]}
    if out["error"]:
        log(f"Lỗi từ database: {out['error']}", "err")
        return {"ok": False, "error": out["error"]}
    r = dict(out["res"] or {})
    r["min_total"] = min_total
    return r


def cashier(params, log, ctx):
    total = to_int(params.get("total"), 200000, 1000, 10_000_000)
    after = to_float(params.get("after"), 1.5, 0, 10)
    log(f"Gọi sp_ph_cashier(hóa đơn mới {vnd(total)}, tạo sau {after:g}s)")
    out = call_sp(ctx, log, "SELECT sp_ph_cashier(%s, %s) AS r", (total, after),
                  name="sp_ph_cashier", hint=BUG_FILE)
    if out["fatal"]:
        return {"ok": False, "fatal": out["fatal"]}
    if out["error"]:
        log(f"Lỗi từ database: {out['error']}", "err")
        return {"ok": False, "error": out["error"]}
    r = dict(out["res"] or {})
    r["t_commit"] = out["t_commit"]
    log("COMMIT → hóa đơn mới đã lưu thật", "ok")
    return r


def work(who, params, log, ctx):
    return manager(params, log, ctx) if who == "A" else cashier(params, log, ctx)


def judge(room):
    A, B = room.results.get("A", {}), room.results.get("B", {})
    if not A.get("ok") or not B.get("ok"):
        return {"bug": False, "headline": "Kịch bản không chạy trọn vẹn, xem bảng thời gian.", "explain": [], "fix": []}
    t0 = room.t0e or 0
    ph = phase(B["t_attempt"], B["t_commit"], A["t_read1"], A["t_read2"])
    attempt_at = B["t_attempt"] - t0
    commit_at = B["t_commit"] - t0
    read2_at = A["t_read2"] - t0
    ids1, ids2 = A["ids1"], A["ids2"]
    new_ids = [i for i in ids2 if i not in ids1]

    if new_ids:
        return {
            "bug": True,
            "headline": f"PHANTOM READ: báo cáo lần 1 có {len(ids1)} hóa đơn ({vnd(A['sum1'])}), lần 2 có {len(ids2)} hóa đơn ({vnd(A['sum2'])}).",
            "explain": [
                f"Quản lý chạy cùng một truy vấn hai lần trong một giao dịch. Giữa hai lần (giây thứ {commit_at:.1f}), thu ngân INSERT hóa đơn #{B['id']} ({vnd(B['total'])}) và COMMIT.",
                "Ở mức READ COMMITTED, mỗi câu truy vấn lấy snapshot MỚI, nên lần 2 thấy thêm một dòng mà lần 1 không có. Đó là dòng 'ma'.",
                "Khác unrepeatable read ở chỗ không phải dòng cũ đổi giá trị mà là tập kết quả có thêm dòng. Dòng chưa tồn tại thì không thể khóa từng dòng được.",
                "Vị trí lỗi: trong function sp_ph_manager (mở trong pgAdmin), hai câu SELECT báo cáo không có khóa nào ngăn người khác INSERT.",
            ],
            "fix": [
                "Mở file sql/m4_phantom_read.sql trong pgAdmin, kéo tới '>>> SỬA TẠI ĐÂY <<<': bật dòng [SỬA] bằng Ctrl+/ (LOCK TABLE orders IN SHARE MODE, thu ngân phải chờ quản lý xong mới INSERT được), bấm F5, rồi quay lại bấm ▶ Chạy lại demo.",
                "Cách khác: dùng REPEATABLE READ hoặc SERIALIZABLE (snapshot cố định). PostgreSQL chặn phantom ngay ở REPEATABLE READ, mạnh hơn chuẩn SQL. Cuối file m4 có kịch bản chạy tay trong 2 tab pgAdmin.",
            ],
        }
    if ph == "blocked":
        return {"bug": False,
                "headline": f"Không có phantom: hai lần đều ra {len(ids1)} hóa đơn.",
                "explain": [f"Thu ngân định INSERT hóa đơn ở giây thứ {attempt_at:.1f} (giữa hai lần xuất) nhưng bị CHẶN vì quản lý đã khóa bảng orders (LOCK TABLE ... SHARE MODE) đến hết giao dịch.",
                            f"Quản lý xuất xong lần 2 ở giây thứ {read2_at:.1f} và COMMIT, thu ngân mới được ghi (COMMIT ở giây thứ {commit_at:.1f}). Vì vậy báo cáo nhất quán.",
                            "Đây là cách giữ khóa: bên ghi phải chờ bên đọc. Bảng thời gian cho thấy thu ngân bị trễ."],
                "fix": []}
    if ph == "before":
        return {"bug": False,
                "headline": f"Không có phantom: hai lần đều ra {len(ids1)} hóa đơn.",
                "explain": [f"Hóa đơn #{B['id']} được COMMIT ở giây thứ {commit_at:.1f}, TRƯỚC khi quản lý bắt đầu báo cáo, nên cả hai lần đều đã có nó.",
                            "Phantom chỉ xảy ra khi hóa đơn mới xuất hiện GIỮA hai lần xuất báo cáo. Hãy tăng 'Thu ngân tạo sau' lên khoảng 1,5 giây."],
                "fix": []}
    if ph == "after":
        return {"bug": False,
                "headline": f"Không có phantom: hai lần đều ra {len(ids1)} hóa đơn.",
                "explain": [f"Quản lý đã xuất xong lần 2 ở giây thứ {read2_at:.1f}, còn thu ngân chỉ bắt đầu tạo hóa đơn ở giây thứ {attempt_at:.1f} (sau đó).",
                            "Hãy cho thu ngân tạo hóa đơn SỚM hơn (nhỏ hơn thời gian quản lý xem báo cáo) để nó rơi vào giữa hai lần xuất."],
                "fix": []}
    return {"bug": False,
            "headline": f"Không có phantom: hai lần đều ra {len(ids1)} hóa đơn.",
            "explain": [f"Hóa đơn mới ({vnd(B['total'])}) nhỏ hơn mức lọc {vnd(A['min_total'])} nên không thỏa điều kiện WHERE của báo cáo, không lọt vào kết quả.",
                        "Hãy tăng tổng tiền của hóa đơn mới lên cao hơn mức lọc để thấy dòng 'ma'."],
            "fix": []}


room = Room(works={"run": work}, judge=judge, snapshot=snapshot, prepare=prepare, default_mode="run")
router = make_router("/phantom-read", "Module 4 - Phantom Read", room)
