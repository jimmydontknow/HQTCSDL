"""Module 3: Unrepeatable Read. Logic nằm trong function sp_ur_customer / sp_ur_cashier (sql/m3_*.sql)."""
from demo_utils import run_once, ensure_schema
from sim import Room, make_router, to_int, to_float, vnd, call_sp, phase

CART = "CART-DEMO"
BUG_FILE = "sql/m3_unrepeatable_read.sql"


def prepare(**_):
    ensure_schema()
    run_once("UPDATE orders SET service_fee=0, discount=0 WHERE customer_name=%s", (CART,))


def snapshot():
    ensure_schema()
    return run_once("SELECT subtotal, service_fee, discount, total FROM orders WHERE customer_name=%s LIMIT 1",
                    (CART,), fetch=True)[0]


def customer(params, log, ctx):
    view = to_float(params.get("view_secs"), 3, 1, 8)
    log(f"Gọi sp_ur_customer(xem giỏ hàng {view:g}s rồi mới xác nhận)")
    out = call_sp(ctx, log, "SELECT sp_ur_customer(%s) AS r", (view,),
                  name="sp_ur_customer", hint=BUG_FILE)
    if out["fatal"]:
        return {"ok": False, "fatal": out["fatal"]}
    if out["error"]:
        log(f"Lỗi từ database: {out['error']}", "err")
        return {"ok": False, "error": out["error"]}
    return dict(out["res"] or {})


def cashier(params, log, ctx):
    kind = "discount" if params.get("kind") == "discount" else "fee"
    amount = to_int(params.get("amount"), 50000, 0, 1_000_000)
    after = to_float(params.get("after"), 1.5, 0, 10)
    log(f"Gọi sp_ur_cashier({'phí dịch vụ' if kind == 'fee' else 'giảm giá'} {vnd(amount)}, sửa sau {after:g}s)")
    out = call_sp(ctx, log, "SELECT sp_ur_cashier(%s, %s, %s) AS r", (kind, amount, after),
                  name="sp_ur_cashier", hint=BUG_FILE)
    if out["fatal"]:
        return {"ok": False, "fatal": out["fatal"]}
    if out["error"]:
        log(f"Lỗi từ database: {out['error']}", "err")
        return {"ok": False, "error": out["error"]}
    r = dict(out["res"] or {})
    r["t_commit"] = out["t_commit"]
    log("COMMIT → thay đổi đã lưu thật vào hóa đơn", "ok")
    return r


def work(who, params, log, ctx):
    return customer(params, log, ctx) if who == "A" else cashier(params, log, ctx)


def judge(room):
    A, B = room.results.get("A", {}), room.results.get("B", {})
    if not A.get("ok") or not B.get("ok"):
        return {"bug": False, "headline": "Kịch bản không chạy trọn vẹn, xem bảng thời gian.", "explain": [], "fix": []}
    first, second = A["first"], A["second"]
    t0 = room.t0e or 0
    ph = phase(B["t_attempt"], B["t_commit"], A["t_read1"], A["t_read2"])
    attempt_at = B["t_attempt"] - t0
    commit_at = B["t_commit"] - t0
    read2_at = A["t_read2"] - t0

    if first != second:
        return {
            "bug": True,
            "headline": f"UNREPEATABLE READ: cùng một giao dịch nhưng lần 1 = {vnd(first)}, lần 2 = {vnd(second)}.",
            "explain": [
                f"Khách đọc tổng tiền lần 1 = {vnd(first)}. Thu ngân sửa hóa đơn và COMMIT ở giây thứ {commit_at:.1f}, nằm giữa hai lần đọc của khách (lần 2 ở giây thứ {read2_at:.1f}).",
                "Ở mức READ COMMITTED (mặc định của PostgreSQL), mỗi câu SELECT lấy một snapshot MỚI, nên lần đọc 2 thấy dữ liệu thu ngân vừa commit.",
                f"Một dòng được đọc hai lần trong cùng giao dịch cho hai giá trị khác nhau. Khách được báo {vnd(first)} nhưng lúc thanh toán bị tính {vnd(second)}.",
                "Vị trí lỗi: trong function sp_ur_customer (mở trong pgAdmin), câu SELECT đọc lần 1 không giữ khóa gì (dòng đánh dấu [LỖI]), nên thu ngân sửa được dòng đó ở giữa.",
            ],
            "fix": [
                "Mở file sql/m3_unrepeatable_read.sql trong pgAdmin, kéo tới '>>> SỬA TẠI ĐÂY <<<': tắt dòng [LỖI] và bật dòng [SỬA] bằng Ctrl+/ (thêm FOR SHARE để khóa dòng đến hết giao dịch), bấm F5, rồi quay lại bấm ▶ Chạy lại demo.",
                "Cách khác: dùng mức cô lập REPEATABLE READ (snapshot cố định cho cả giao dịch). Cách này phải đặt khi mở giao dịch nên không sửa trong function được; cuối file m3 có kịch bản chạy tay trong 2 tab pgAdmin.",
            ],
        }
    if ph == "blocked":
        return {
            "bug": False,
            "headline": f"Không có lỗi: hai lần đọc đều = {vnd(first)}.",
            "explain": [
                f"Thu ngân định sửa hóa đơn ở giây thứ {attempt_at:.1f} (giữa hai lần đọc của khách) nhưng bị CHẶN: lần đọc 1 của khách đã khóa dòng (FOR SHARE) đến hết giao dịch.",
                f"Khách đọc xong lần 2 ở giây thứ {read2_at:.1f} và COMMIT, thu ngân mới được ghi (COMMIT ở giây thứ {commit_at:.1f}). Vì vậy khách thấy cùng một giá trị ở cả hai lần.",
                "Đây là cách giữ khóa (lock-based): bên ghi phải chờ bên đọc. Bảng thời gian cho thấy thu ngân bị trễ.",
            ],
            "fix": [],
        }
    if ph == "before":
        return {"bug": False,
                "headline": f"Không có lỗi: hai lần đọc đều = {vnd(first)}.",
                "explain": [f"Thu ngân đã COMMIT ở giây thứ {commit_at:.1f}, TRƯỚC khi khách bắt đầu đọc, nên cả hai lần khách đều thấy giá mới.",
                            "Lỗi chỉ xảy ra khi thay đổi được commit GIỮA hai lần đọc. Hãy tăng 'Thu ngân sửa sau' lên khoảng 1,5 giây."],
                "fix": []}
    if ph == "after":
        return {"bug": False,
                "headline": f"Không có lỗi: hai lần đọc đều = {vnd(first)}.",
                "explain": [f"Khách đã đọc xong lần 2 ở giây thứ {read2_at:.1f}, còn thu ngân chỉ bắt đầu sửa ở giây thứ {attempt_at:.1f} (sau đó).",
                            "Hãy cho thu ngân sửa SỚM hơn (nhỏ hơn thời gian khách xem giỏ hàng) để thay đổi rơi vào giữa hai lần đọc."],
                "fix": []}
    return {"bug": False,
            "headline": f"Lần này hai lần đọc đều = {vnd(first)}.",
            "explain": ["Thu ngân đã COMMIT giữa hai lần đọc nhưng không làm đổi tổng tiền (số tiền nhập là 0 hoặc trùng giá trị cũ). Hãy nhập phí khác 0 để thấy lỗi."],
            "fix": []}


room = Room(works={"run": work}, judge=judge, snapshot=snapshot, prepare=prepare, default_mode="run")
router = make_router("/unrepeatable-read", "Module 3 - Unrepeatable Read", room)
