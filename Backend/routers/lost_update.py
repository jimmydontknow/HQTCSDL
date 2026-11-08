"""Module 1 (chia cho 2 người): Lost Update.
   1A: khắc phục bằng khóa lạc quan (cột version)  -> function sp_lu1_order, món Gà đặc biệt
   1B: khắc phục bằng khóa bi quan / UPDATE nguyên tử -> function sp_lu2_order, món Lẩu thái
Logic thật nằm trong function SQL (sửa trực tiếp trong pgAdmin), file này chỉ gọi function đó."""
from demo_utils import run_once, ensure_schema
from sim import Room, make_router, to_int, to_float, call_sp


def make_module(prefix, tag, food, fn, file, how):
    START = {"stock": 1}

    def prepare(stock=1, **_):
        ensure_schema()
        START["stock"] = to_int(stock, 1, 1, 50)
        run_once("UPDATE foods SET quantity=%s, version=0 WHERE name=%s", (START["stock"], food))

    def snapshot():
        ensure_schema()
        return run_once("SELECT name, price, quantity, version FROM foods WHERE name=%s ORDER BY id LIMIT 1",
                        (food,), fetch=True)[0]

    def work(who, params, log, ctx):
        qty = to_int(params.get("qty"), 1, 1, 50)
        process = to_float(params.get("process"), 1.5, 0, 6)
        wait = to_float(params.get("start_after"), 0, 0, 6)
        log(f"Gọi {fn}(đặt {qty} suất, xử lý thanh toán {process:g}s, bấm sau {wait:g}s)")
        out = call_sp(ctx, log, f"SELECT {fn}(%s, %s, %s, %s) AS r",
                      (who, qty, process, wait), name=fn, hint=file)
        if out["fatal"]:
            return {"ok": False, "fatal": out["fatal"]}
        if out["error"]:
            log(f"Lỗi từ database: {out['error']}", "err")
            return {"ok": False, "qty": qty, "error": out["error"]}
        r = dict(out["res"] or {})
        r.setdefault("qty", qty)
        return r

    def judge(room):
        d = snapshot()
        start = START["stock"]
        res = room.results
        sold = sum(r.get("qty", 0) for r in res.values() if r.get("ok"))
        reduced = start - d["quantity"]
        seen = {w: res[w].get("seen") for w in res}
        bug = sold != reduced or sold > start

        if bug:
            return {
                "bug": True,
                "headline": f"LOST UPDATE: đã báo thành công {sold} suất nhưng kho chỉ giảm {reduced} (tồn kho ban đầu {start}).",
                "explain": [
                    f"Trong bảng thời gian, A và B cùng ĐỌC tồn kho (A thấy {seen.get('A')}, B thấy {seen.get('B')}) trước khi bên nào kịp ghi.",
                    "Mỗi bên xử lý thanh toán một lúc (thời gian xử lý bạn nhập), rồi tự tính tồn kho mới = số đã đọc − số suất đặt, trên con số CŨ.",
                    "Hai lệnh UPDATE đều gán một giá trị tuyệt đối (quantity = ...). Lệnh chạy sau ghi đè kết quả của lệnh chạy trước, nên một lượt đặt bị mất khỏi sổ sách.",
                    f"Vị trí lỗi: trong function {fn} (mở trong pgAdmin), dòng đánh dấu [LỖI]: câu UPDATE gán thẳng quantity = (số đã đọc − số suất), tính trên số cũ.",
                ],
                "fix": [f"Mở file {file} trong pgAdmin, kéo tới chỗ '>>> SỬA TẠI ĐÂY <<<' và làm theo ghi chú ({how}), bấm F5, rồi quay lại bấm ▶ Chạy lại demo."],
            }
        conflicts = [w for w, r in res.items() if r.get("conflict")]
        rejected = [w for w, r in res.items() if not r.get("ok")]
        if conflicts:
            why = (f"Màn hình {', '.join(conflicts)} bị từ chối đúng như thiết kế: câu UPDATE có điều kiện WHERE version = <version đã đọc>, "
                   "bên UPDATE trước đã tăng version nên bên sau không còn dòng nào khớp (0 dòng bị ảnh hưởng).")
        elif rejected:
            why = (f"Màn hình {', '.join(rejected)} bị từ chối vì thấy kho đã hết: bên kia đã ghi xong trước khi bên này đọc hoặc kiểm tra điều kiện, "
                   "nên không còn ghi đè nữa.")
        else:
            why = ("Hai bên không chồng lên nhau: bên đọc sau đã thấy kho đã giảm nên không ghi đè. "
                   "Lỗi chỉ xảy ra khi hai bên ĐỌC trước rồi mới GHI. Hãy để 'Bấm sau' của cả hai bằng 0, tồn kho = 1 và chạy bản function gây lỗi.")
        return {
            "bug": False,
            "headline": f"Không mất dữ liệu: đã bán {sold} suất và kho giảm đúng {reduced}.",
            "explain": [
                why,
            ],
            "fix": ["Bên bị từ chối cần đọc lại dữ liệu rồi đặt lại (retry). Thử tăng tồn kho lên 2 rồi bấm 'Làm lại từ đầu' để thấy bên bị từ chối đặt lại thành công."]
                   if conflicts else [],
        }

    room = Room(works={"run": work}, judge=judge, snapshot=snapshot, prepare=prepare, default_mode="run")
    return make_router(prefix, tag, room)


router_a = make_module(
    "/lost-update-1", "Module 1A - Lost Update (khóa lạc quan)",
    food="Gà đặc biệt", fn="sp_lu1_order",
    file="sql/m1a_lost_update_lac_quan.sql",
    how="tắt dòng [LỖI], bật các dòng [SỬA] bằng Ctrl+/",
)
router_b = make_module(
    "/lost-update-2", "Module 1B - Lost Update (khóa bi quan)",
    food="Lẩu thái", fn="sp_lu2_order",
    file="sql/m1b_lost_update_bi_quan.sql",
    how="chọn CÁCH 1 (FOR UPDATE) hoặc CÁCH 2 (UPDATE nguyên tử)",
)
