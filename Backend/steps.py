"""Bộ chạy KỊCH BẢN GIAO TÁC T1/T2 (bản nháp, chưa thử trên PostgreSQL thật).
Đọc file Backend/scripts/*.sql (định dạng === / ---), chạy từng bước trên 2 phiên (T1, T2) + SYS."""
import datetime
import decimal
import queue
import re
import threading
import time
from pathlib import Path

import psycopg2
from fastapi import APIRouter, Body, HTTPException

from demo_utils import new_conn, ensure_schema

VERSION = 7                      # web dùng số này để biết backend có đúng bản mới không
WAIT = 1.3                       # giây chờ một bước trước khi coi là "đang chờ khóa"
SCRIPT_DIR = Path(__file__).parent / "scripts"

SCN_RE = re.compile(r"^===\s*([A-Za-z0-9_]+)\s*\|\s*([^|]*?)\s*(?:\|\s*(.*?))?\s*$")
HDR_RE = re.compile(r"^---\s+([^|]+?)\s*\|\s*(T1|T2|SYS)\s*(?:\|\s*([A-Za-z0-9_]+))?\s*$")


def parse_script(path):
    """=== key | tiêu đề | ghi chú   mở một kịch bản.
       --- t1 | T1 | id                mở một bước (thời điểm | phiên | id tùy chọn).
       --- setup | SYS / --- cleanup | SYS: chuẩn bị / dọn dữ liệu (không hiện trong bảng)."""
    text = Path(path).read_text(encoding="utf-8")
    scenarios, cur, step = [], None, None
    for raw in text.splitlines():
        m = SCN_RE.match(raw)
        if m:
            cur = {"key": m.group(1), "title": m.group(2), "note": m.group(3) or "",
                   "setup": [], "cleanup": [], "steps": [], "sim": m.group(1).startswith("sim_")}
            scenarios.append(cur)
            step = None
            continue
        h = HDR_RE.match(raw)
        if h and cur is not None:
            t, who, sid = h.group(1).strip(), h.group(2), h.group(3)
            step = {"time": t, "who": who, "id": sid, "lines": []}
            (cur["setup"] if t == "setup" else cur["cleanup"] if t == "cleanup" else cur["steps"]).append(step)
            continue
        if step is not None:
            step["lines"].append(raw.rstrip())
    for sc in scenarios:
        for st in sc["setup"] + sc["cleanup"] + sc["steps"]:
            while st["lines"] and not st["lines"][-1].strip():
                st["lines"].pop()
            while st["lines"] and not st["lines"][0].strip():
                st["lines"].pop(0)
    return scenarios


def split_statements(lines):
    code = "\n".join(re.sub(r"--.*$", "", l) for l in lines)
    return [s.strip() for s in code.split(";") if s.strip()]


def sim_statements(lines):
    """Kịch bản mô phỏng (key bắt đầu bằng sim_): mỗi câu lệnh có thể kèm dòng '--> kết quả' ghi sẵn ngay dưới nó.
    '--> price = 50000' sẽ thành một dòng kết quả có cột price = 50000 để hàm judge đọc được."""
    out = []
    for l in lines:
        t = l.strip()
        if t.startswith("-->"):
            if out:
                out[-1][1] = t[3:].strip()
            continue
        code = re.sub(r"--.*$", "", l).strip()
        if code:
            out.append([code.rstrip(";").strip(), ""])
    return out


def jv(v):
    if isinstance(v, decimal.Decimal):
        return int(v) if v == v.to_integral() else float(v)
    if isinstance(v, (datetime.date, datetime.datetime, datetime.time)):
        return str(v)
    return v


def run_sql_now(stmts):
    """Chạy các câu lệnh chuẩn bị/dọn dẹp trên một kết nối riêng (autocommit)."""
    conn = new_conn()
    try:
        conn.autocommit = True
        cur = conn.cursor()
        for s in stmts:
            cur.execute(s)
    finally:
        conn.close()


class Session:
    """Một 'cửa sổ truy vấn' thật (như 1 tab pgAdmin): 1 kết nối riêng, chạy lần lượt từng bước."""

    def __init__(self, name):
        self.name = name
        self.conn = new_conn()
        self.conn.autocommit = True          # để BEGIN / COMMIT / ROLLBACK trong kịch bản có hiệu lực thật
        self.conn.cursor().execute("SET lock_timeout = '30s'")
        self.q = queue.Queue()
        self.t = threading.Thread(target=self._loop, daemon=True)
        self.t.start()

    def _loop(self):
        while True:
            job = self.q.get()
            if job is None:
                return
            step, stmts = job
            if step["status"] != "waiting":
                step["status"] = "running"
            self._exec(step, stmts)
            step["status"] = "error" if step.get("error") else "done"
            step["event"].set()

    def _sim(self, step):
        """Không chạy SQL: hiện kết quả ghi sẵn (hành vi của SQL Server) cho từng câu lệnh."""
        for stmt, canned in sim_statements(step["lines"]):
            e = {"stmt": " ".join(stmt.split()), "text": canned or "OK", "error": None, "rows": None, "status": None}
            m = re.match(r"^(\w+)\s*=\s*(-?\d+)$", canned)
            if m:
                e["rows"] = [{m.group(1): int(m.group(2))}]
                e["text"] = f"→ {m.group(1)} = {m.group(2)}"
            time.sleep(0.15)
            step["results"].append(e)

    def _exec(self, step, stmts):
        if step.get("sim"):
            return self._sim(step)
        cur = self.conn.cursor()
        for s in stmts:
            e = {"stmt": " ".join(s.split()), "text": "", "error": None, "rows": None, "status": None}
            try:
                cur.execute(s)
                e["status"] = cur.statusmessage
                if cur.description:
                    rows = [{k: jv(v) for k, v in r.items()} for r in cur.fetchall()]
                    e["rows"] = rows
                    e["text"] = ("→ " + " | ".join(", ".join(f"{k} = {v}" for k, v in r.items()) for r in rows[:6])
                                 if rows else "→ (không có dòng nào)")
                else:
                    e["text"] = e["status"] or ""
            except psycopg2.Error as ex:
                e["error"] = (ex.diag.message_primary or str(ex)).strip()
                e["text"] = "LỖI: " + e["error"]
                step["error"] = True
                step["results"].append(e)
                try:                                   # giao tác lỗi: hủy luôn để nhả khóa (giống khi PostgreSQL báo lỗi)
                    if self.conn.get_transaction_status() != 0:
                        cur.execute("ROLLBACK")
                        step["results"].append({"stmt": "ROLLBACK", "text": "ROLLBACK (giao tác bị hủy do lỗi ở trên)",
                                                "error": None, "rows": None, "status": "ROLLBACK"})
                except Exception:
                    pass
                break
            step["results"].append(e)

    def submit(self, step):
        step["event"] = threading.Event()
        step["status"] = "queued"
        self.q.put((step, split_statements(step["lines"])))

    def close(self):
        try:
            self.conn.cancel()               # hủy lệnh đang chờ khóa (nếu có)
        except Exception:
            pass
        self.q.put(None)
        self.t.join(timeout=3)
        try:
            self.conn.close()                # đóng kết nối = tự ROLLBACK giao dịch đang mở, nhả khóa
        except Exception:
            pass


def collect(steps):
    """Gom kết quả theo id bước để hàm judge của từng module đọc."""
    R = {}
    for st in steps:
        if not st["id"]:
            continue
        rows, rc, err = None, None, None
        for r in st["results"]:
            if r.get("rows") is not None:
                rows = r["rows"]
            m = re.match(r"(UPDATE|INSERT|DELETE)\s+(?:\d+\s+)?(\d+)", r.get("status") or "")
            if m:
                rc = int(m.group(2))
            if r.get("error"):
                err = r["error"]
        R[st["id"]] = {"rows": rows, "rowcount": rc, "waited": st["waited"], "error": err,
                       "done": st["status"] in ("done", "error")}
    return R


def val(R, sid, col=None):
    """Giá trị ô đầu tiên (hoặc cột col) của dòng đầu tiên trong kết quả bước sid."""
    r = (R.get(sid) or {}).get("rows")
    if not r:
        return None
    row = r[0]
    return row[col] if col else next(iter(row.values()))


class Runner:
    def __init__(self, file, judge):
        self.file, self.judge = file, judge
        self.sessions, self.scenarios = {}, []
        self.key, self.steps, self.setup_lines = None, [], []
        self.cursor, self.verdict, self.auto, self.error = 0, None, False, None
        self.mut = threading.RLock()
        self.gen = 0

    @staticmethod
    def _fresh(st):
        return {**st, "status": "pending", "results": [], "waited": False, "error": False, "event": None}

    def _scn(self):
        return next((s for s in self.scenarios if s["key"] == self.key), None)

    def _close_sessions(self):
        for s in self.sessions.values():
            s.close()
        self.sessions = {}

    def reset(self, key=None):
        with self.mut:
            self.gen += 1
            self.auto = False
            self._close_sessions()
            try:
                ensure_schema()
                self.scenarios = parse_script(SCRIPT_DIR / self.file)     # đọc lại file mỗi lần: sửa file có hiệu lực ngay
                self.error = None
            except Exception as e:
                self.scenarios, self.error = [], f"Không đọc được file {self.file}: {e}"
            if key:
                self.key = key
            if self.scenarios and self.key not in [s["key"] for s in self.scenarios]:
                self.key = self.scenarios[0]["key"]
            sc = self._scn()
            self.steps, self.cursor, self.verdict, self.setup_lines = [], 0, None, []
            if not sc:
                return
            self.steps = [self._fresh({**s, "sim": sc.get("sim", False)}) for s in sc["steps"]]
            self.setup_lines = [l for s in sc["setup"] for l in s["lines"]]
            try:
                for s in sc["cleanup"] + sc["setup"]:
                    run_sql_now(split_statements(s["lines"]))
                self.sessions = {n: Session(n) for n in ("T1", "T2", "SYS")}
            except Exception as e:
                self.error = f"Lỗi khi chuẩn bị dữ liệu: {e}"

    def next(self):
        with self.mut:
            if self.cursor >= len(self.steps) or not self.sessions:
                return
            step = self.steps[self.cursor]
            self.cursor += 1
        sess = self.sessions[step["who"]]
        behind = any(p["who"] == step["who"] and p["status"] in ("waiting", "running", "queued")
                     for p in self.steps[:self.cursor - 1])   # cùng phiên còn một bước chưa xong (đang chờ khóa)
        sess.submit(step)
        if behind:
            return                                     # chỉ xếp hàng phía sau, chạy khi bước trước xong
        if not step["event"].wait(WAIT):               # quá WAIT giây chưa xong => đang bị khóa chặn
            step["waited"] = True
            if not step["event"].is_set():
                step["status"] = "waiting"

    def run_all(self):
        with self.mut:
            if self.auto:
                return
            self.auto, gen = True, self.gen

        def loop():
            while True:
                with self.mut:
                    if gen != self.gen or self.cursor >= len(self.steps):
                        break
                self.next()
                time.sleep(0.6)
            t0 = time.time()
            while gen == self.gen and time.time() - t0 < 40 and not self._all_done():
                time.sleep(0.2)
            if gen == self.gen:
                self.auto = False

        threading.Thread(target=loop, daemon=True).start()

    def _all_done(self):
        return bool(self.steps) and all(s["status"] in ("done", "error") for s in self.steps)

    def _maybe_finish(self):
        if self.verdict is None and self.cursor >= len(self.steps) and self._all_done():
            try:
                self.verdict = self.judge(self.key, collect(self.steps))
            except Exception as e:
                self.verdict = {"bug": False, "headline": f"Không phân tích được kết quả: {e}", "explain": [], "fix": []}

    def state(self):
        self._maybe_finish()
        sc = self._scn()
        return {
            "v": VERSION, "file": self.file, "error": self.error,
            "scenarios": [{"key": s["key"], "title": s["title"], "sim": s.get("sim", False)} for s in self.scenarios],
            "sim": bool(sc and sc.get("sim")),
            "scenario": self.key, "note": sc["note"] if sc else "",
            "setup": self.setup_lines, "cursor": self.cursor, "total": len(self.steps), "auto": self.auto,
            "steps": [{"idx": i, "time": s["time"], "who": s["who"], "id": s["id"], "lines": [l for l in s["lines"] if not l.strip().startswith("-->")],
                       "status": s["status"], "waited": s["waited"],
                       "results": [{"text": r["text"], "error": r["error"]} for r in list(s["results"])]}
                      for i, s in enumerate(self.steps)],
            "verdict": self.verdict,
        }


def make_router(prefix, tag, runner):
    r = APIRouter(prefix=prefix, tags=[tag])

    def guard(fn, *a):
        try:
            return fn(*a)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(500, f"Lỗi phía server: {e}")

    @r.get("/state")
    def state():
        return guard(runner.state)

    @r.post("/select")
    def select(body: dict = Body(default={})):
        guard(runner.reset, body.get("scenario"))
        return runner.state()

    @r.post("/reset")
    def reset():
        guard(runner.reset, runner.key)
        return runner.state()

    @r.post("/next")
    def nxt():
        guard(runner.next)
        return runner.state()

    @r.post("/all")
    def all_():
        guard(runner.run_all)
        return runner.state()

    return r
