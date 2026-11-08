import re
import threading
import time

import psycopg2
from fastapi import APIRouter, Body, HTTPException
from psycopg2 import errors

from demo_utils import new_conn

VERSION = 5      # giao diện dùng số này để biết backend có đúng bản mới không


def to_int(v, default, lo, hi):
    try:
        n = int(v)
    except (TypeError, ValueError):
        n = default
    return max(lo, min(hi, n))


def to_float(v, default, lo, hi):
    try:
        n = float(v)
    except (TypeError, ValueError):
        n = default
    return max(lo, min(hi, n))


def vnd(n):
    return f"{int(n):,}".replace(",", ".") + "đ"


def phase(attempt, commit, read1, read2):
    """Thao tác ghi của bên kia (bắt đầu lúc 'attempt', COMMIT lúc 'commit')
    rơi vào đâu so với 2 lần đọc của giao tác kia (read1, read2)?"""
    if attempt < read1:
        return "before"        # ghi xong trước khi bên kia bắt đầu đọc
    if attempt > read2:
        return "after"         # bên kia đã đọc xong lần 2 rồi mới ghi
    if commit > read2:
        return "blocked"       # định ghi ở giữa nhưng bị CHẶN, đến sau lần đọc 2 mới được ghi
    return "between"           # ghi và COMMIT ngay giữa 2 lần đọc


# Nhật ký do function SQL gửi về có dạng:  <epoch>|<loại>|<nội dung>
NOTICE_RE = re.compile(r"(\d{9,}(?:\.\d+)?)\|([a-z]+)\|(.*)", re.S)


def call_sp(ctx, log, sql, args, name, hint, level=None):
    """Gọi 1 function SQL trong 1 giao dịch riêng (1 'người dùng' riêng).
    Trả về dict: res (kết quả jsonb), t_commit (epoch lúc COMMIT), error, fatal."""
    out = {"res": None, "t_commit": None, "error": None, "fatal": None}
    conn = new_conn(level)
    try:
        cur = conn.cursor()
        cur.execute("SET lock_timeout = '20s'")
        try:
            cur.execute(sql, args)
            row = cur.fetchone()
            out["res"] = row["r"] if row else None
            conn.commit()
            out["t_commit"] = time.time()
        except errors.UndefinedFunction as e:
            conn.rollback()
            out["fatal"] = (f"Chưa có function {name} trong database (hoặc sai kiểu tham số): "
                            f"{(e.diag.message_primary or '').strip()}. "
                            f"Hãy mở pgAdmin và chạy file {hint}.")
        except psycopg2.Error as e:
            conn.rollback()
            out["error"] = (e.diag.message_primary or str(e)).strip()
        # đưa nhật ký của function (RAISE NOTICE) lên bảng thời gian
        for n in list(conn.notices):
            m = NOTICE_RE.search(n)
            if m:
                ctx["log_at"](float(m.group(1)), m.group(3).strip(), m.group(2))
    finally:
        conn.close()
    return out


class Room:
    """Một 'phòng demo' có 2 giao tác A, B. Hai giao tác chỉ bắt đầu khi CẢ HAI đã sẵn sàng,
    rồi được thả chạy CÙNG MỘT LÚC (threading.Barrier)."""

    def __init__(self, works, judge, snapshot, prepare, default_mode, validate=None):
        self.works = works          # {mode: hàm work(who, params, log, ctx)}
        self.judge = judge          # (room) -> dict kết luận
        self.snapshot = snapshot    # () -> dữ liệu DB hiện tại
        self.prepare = prepare      # đặt lại dữ liệu demo
        self.validate = validate
        self.mode = default_mode
        self.lock = threading.Lock()
        self.gen = 0
        self._clear()

    def _new_barrier(self):
        return threading.Barrier(2, action=self._start)

    def _start(self):
        # chạy đúng 1 lần, khi CẢ HAI giao tác đã sẵn sàng
        self.t0e = time.time()
        self.status["A"] = "running"
        self.status["B"] = "running"

    def _clear(self):
        with self.lock:
            self.gen += 1
            self.status = {"A": "idle", "B": "idle"}
            self.params = {}
            self.results = {}
            self.events = []
            self.verdict = None
            self.t0e = None
            old = getattr(self, "barrier", None)
            self.barrier = self._new_barrier()
        if old is not None:
            try:
                old.abort()
            except Exception:
                pass

    def running(self):
        return any(s == "running" for s in self.status.values())

    def reset(self, args=None):
        """Luôn được phép: hủy mọi thứ đang chạy rồi đặt lại dữ liệu demo."""
        self._clear()
        self.prepare(**(args or {}))

    def set_mode(self, mode, args=None):
        if mode not in self.works:
            raise HTTPException(400, "Chế độ không hợp lệ")
        self.mode = mode
        self.reset(args)

    def log_at(self, who, epoch, text, kind="info", gen=None):
        with self.lock:
            if gen is not None and gen != self.gen:
                return                       # nhật ký của lần chạy cũ đã bị hủy
            t = 0 if self.t0e is None else max(0, round((epoch - self.t0e) * 1000))
            self.events.append({"t": t, "who": who, "text": text, "kind": kind})

    def log(self, who, text, kind="info", gen=None):
        self.log_at(who, time.time(), text, kind, gen)

    def cancel(self):
        with self.lock:
            old = self.barrier
            self.barrier = self._new_barrier()
            for w in ("A", "B"):
                if self.status[w] == "waiting":
                    self.status[w] = "idle"
        try:
            old.abort()
        except Exception:
            pass

    # ----- MỘT NÚT chạy cả hai: thông tin của A và B đi kèm trong yêu cầu -----
    def run_both(self, mode, args, plans):
        if mode not in self.works:
            raise HTTPException(400, "Chế độ không hợp lệ")
        plans = {w: dict((plans or {}).get(w) or {}) for w in ("A", "B")}
        if self.validate:
            for w in ("A", "B"):
                self.validate(w, plans[w])
        self.mode = mode
        self.reset(args)                     # đặt lại sạch sẽ trước mỗi lần chạy

        def go(w):
            try:
                self.run(w, plans[w])
            except HTTPException:
                pass
            except Exception as e:
                self.log(w, f"Lỗi: {e}", "err")

        for w in ("A", "B"):
            threading.Thread(target=go, args=(w,), daemon=True).start()

    # ----- Mỗi giao tác tự chạy (dùng khi 2 người bấm ở 2 cửa sổ riêng) -----
    def run(self, who, params):
        if who not in ("A", "B"):
            raise HTTPException(400, "who phải là A hoặc B")
        if self.validate:
            self.validate(who, params)
        with self.lock:
            if self.status[who] != "idle":
                raise HTTPException(409, "Màn hình này đã bấm rồi, hãy bấm 'Làm lại' trước.")
            self.status[who] = "waiting"
            self.params[who] = params
            gen, barrier, mode = self.gen, self.barrier, self.mode

        try:
            barrier.wait(timeout=60)          # chờ giao tác còn lại sẵn sàng
        except threading.BrokenBarrierError:
            with self.lock:
                if self.gen == gen:
                    if self.barrier is barrier:
                        self.barrier = self._new_barrier()
                    self.status[who] = "idle"
            raise HTTPException(409, "Chưa đủ 2 giao tác cùng bấm (hết 60 giây hoặc đã hủy chờ). Hãy bấm lại.")

        def log(text, kind="info"):
            self.log(who, text, kind, gen)

        def log_at(epoch, text, kind="info"):
            self.log_at(who, epoch, text, kind, gen)

        ctx = {"mode": mode, "all": dict(self.params), "log_at": log_at}

        try:
            result = self.works[mode](who, params, log, ctx)
        except Exception as e:
            log(f"Lỗi: {e}", "err")
            result = {"ok": False, "error": str(e)}

        with self.lock:
            if self.gen != gen:
                return {"cancelled": True}
            self.results[who] = result
            self.status[who] = "done"
            last = all(s == "done" for s in self.status.values())
            results = dict(self.results)
        if last:
            fatal = [r.get("fatal") for r in results.values() if r.get("fatal")]
            if fatal:
                verdict = {
                    "bug": False,
                    "headline": "Không chạy được: " + fatal[0],
                    "explain": ["Logic của demo nằm trong function SQL do bạn cài bằng pgAdmin. Chưa có function (hoặc sai tên, sai tham số) thì demo không chạy được."],
                    "fix": ["Mở pgAdmin (Query Tool của restaurant_db), mở file SQL của module này (tên file ghi ở đầu trang) rồi bấm F5."],
                }
            else:
                try:
                    verdict = self.judge(self)
                except Exception as e:
                    verdict = {"bug": False, "headline": f"Không phân tích được kết quả: {e}",
                               "explain": [], "fix": []}
            with self.lock:
                if self.gen == gen:
                    self.verdict = verdict
        return {"ok": True}

    def state(self):
        with self.lock:
            s = {
                "v": VERSION,
                "mode": self.mode,
                "status": dict(self.status),
                "events": sorted(self.events, key=lambda e: e["t"]),
                "results": dict(self.results),
                "verdict": self.verdict,
                "done": self.verdict is not None,
            }
        try:
            s["data"] = self.snapshot()
            s["data_error"] = None
        except Exception as e:
            s["data"] = None
            s["data_error"] = str(e)
        return s


def guard(fn, *args, **kw):
    """Biến mọi lỗi bất ngờ thành thông báo đọc được thay vì 'Internal Server Error'."""
    try:
        return fn(*args, **kw)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Lỗi phía server: {e}")


def make_router(prefix, tag, room):
    r = APIRouter(prefix=prefix, tags=[tag])

    @r.get("/state")
    def state():
        return room.state()

    @r.post("/mode")
    def set_mode(body: dict = Body(default={})):
        guard(room.set_mode, body.get("mode"), body.get("args"))
        return room.state()

    @r.post("/reset")
    def reset(body: dict = Body(default={})):
        guard(room.reset, body)
        return room.state()

    @r.post("/run-both")
    def run_both(body: dict = Body(default={})):
        guard(room.run_both, body.get("mode") or room.mode, body.get("args"),
              {"A": body.get("A"), "B": body.get("B")})
        return {"started": True}

    @r.post("/run/{who}")
    def run(who: str, body: dict = Body(default={})):
        return guard(room.run, who, body)

    @r.post("/cancel")
    def cancel():
        room.cancel()
        return room.state()

    return r
