import { useEffect, useState } from "react";
import { get, post, errText, EventLog, useLog } from "./shared";

const MAX_DAYS_AHEAD = 60;
const isoDay = (d) => d.toLocaleDateString("en-CA");
const todayStr = () => isoDay(new Date());
const maxDateStr = () => isoDay(new Date(Date.now() + MAX_DAYS_AHEAD * 86400000));

const LEVELS = [
  ["read_uncommitted", "READ UNCOMMITTED"],
  ["read_committed", "READ COMMITTED"],
];

// lấy thông tin đang nhập dở ở trang Đặt bàn
const loadDraft = () => {
  try { return JSON.parse(localStorage.getItem("booking_draft")) || {}; } catch { return {}; }
};

export default function DirtyRead() {
  const draft = loadDraft();
  const [day, setDay] = useState(draft.day && draft.day >= todayStr() ? draft.day : todayStr());
  const [tables, setTables] = useState([]);
  const [slots, setSlots] = useState([]);
  const [reservations, setReservations] = useState([]);
  const [t1, setT1] = useState({ t1_open: false });
  const [form, setForm] = useState({
    name: draft.customer_name || "",
    phone: draft.phone || "",
    slot_id: "",
    table_id: "",
    size: draft.party_size || 2,
  });
  const [pick, setPick] = useState("");
  const [level, setLevel] = useState("read_uncommitted");
  const [t2, setT2] = useState(null);
  const [note, setNote] = useState(null);
  const [loadError, setLoadError] = useState(null);
  const { log, add, clear } = useLog();

  const loadAll = async (d = day) => {
    const [tb, sl, rs, st] = await Promise.all([
      get("/tables"), get(`/slots?d=${d}`), get("/reservations"), get("/dirty-read/state"),
    ]);
    const bad = [tb, sl, rs, st].find((x) => !x.ok);
    if (bad) {
      setLoadError(errText(bad.data) + " (kiểm tra backend uvicorn và PostgreSQL đã chạy chưa)");
      return;
    }
    setLoadError(null);
    setTables(tb.data); setSlots(sl.data); setReservations(rs.data); setT1(st.data);
  };

  useEffect(() => {
    post("/dirty-read/reset").then(() => loadAll(day));
    return () => { post("/dirty-read/reset"); };   // rời tab thì tự ROLLBACK, nhả khóa
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const change = (e) => { setForm({ ...form, [e.target.name]: e.target.value }); setPick(""); };

  const changeDay = (d) => {
    if (!d) return;
    setDay(d);
    setPick("");
    setForm((f) => ({ ...f, slot_id: "", table_id: "" }));
    setT2(null);
    loadAll(d);
  };

  const slot = slots.find((s) => String(s.id) === String(form.slot_id));
  const table = tables.find((t) => String(t.id) === String(form.table_id));
  const takenTables = new Set(
    reservations
      .filter((r) => String(r.slot_id) === String(form.slot_id) && r.status === "confirmed")
      .map((r) => r.table_id)
  );
  const nowHM = () => new Date().toTimeString().slice(0, 5);
  const pastOn = (d, s) => d === todayStr() && s.slot_time.slice(0, 5) <= nowHM();
  const isPast = (s) => pastOn(day, s);
  const left = (s) => s.max_seats - s.booked_seats;

  const fail = (r) => setNote({ type: "err", text: `✘ ${errText(r.data)}` });

  // Chọn khung giờ và bàn còn trống phù hợp nhất (ưu tiên khung giờ / bàn của đơn gốc nếu còn dùng được)
  const chooseFree = (slotsList, resList, tableList, d, size, prefSlotId, prefTableId) => {
    const okSlot = (s) => !pastOn(d, s) && s.max_seats - s.booked_seats >= size;
    const s = slotsList.find((x) => x.id === prefSlotId && okSlot(x)) || slotsList.find(okSlot);
    if (!s) return { slot: null, table: null };
    const taken = new Set(resList.filter((r) => r.slot_id === s.id && r.status === "confirmed").map((r) => r.table_id));
    const free = tableList
      .filter((t) => !taken.has(t.id) && t.capacity >= size)
      .sort((a, b) => a.capacity - b.capacity || a.id - b.id);
    const t = free.find((x) => x.id === prefTableId) || free[0] || null;
    return { slot: s, table: t };
  };

  // ----- Điền nhanh từ thông tin đã nhập ở trang Đặt bàn -----
  const applyPick = async (key) => {
    setPick(key);
    if (!key) return;
    setT2(null);

    const [rs, tb] = await Promise.all([get("/reservations"), get("/tables")]);
    if (!rs.ok || !tb.ok) { setNote({ type: "err", text: `✘ ${errText((!rs.ok ? rs : tb).data)}` }); return; }
    setReservations(rs.data); setTables(tb.data);

    let nd = todayStr();
    let name = "", phone = "", size = 2, prefSlot = null, prefTable = null, source = "";

    if (key === "draft") {
      const d = loadDraft();
      nd = d.day && d.day >= todayStr() ? d.day : todayStr();
      name = d.customer_name || ""; phone = d.phone || ""; size = Number(d.party_size) || 2;
      source = "phần đang nhập dở ở trang Đặt bàn";
    } else {
      const r = rs.data.find((x) => String(x.id) === key);
      if (!r) return;
      name = r.customer_name; phone = r.phone; size = r.party_size;
      source = `đơn #${r.id}`;
      if (r.slot_date >= todayStr()) { nd = r.slot_date; prefSlot = r.slot_id; prefTable = r.table_id; }
    }

    const sl = await get(`/slots?d=${nd}`);
    if (!sl.ok) { setNote({ type: "err", text: `✘ ${errText(sl.data)}` }); return; }

    const { slot: s, table: t } = chooseFree(sl.data, rs.data, tb.data, nd, size, prefSlot, prefTable);

    setDay(nd);
    setSlots(sl.data);
    setForm({
      name, phone, size,
      slot_id: s ? String(s.id) : "",
      table_id: t ? String(t.id) : "",
    });

    if (!s) {
      setNote({ type: "warn", text: `Đã điền thông tin từ ${source}, nhưng ngày ${nd} không còn khung giờ nào đủ ${size} chỗ. Hãy chọn ngày khác.` });
    } else if (!t) {
      setNote({ type: "warn", text: `Đã điền thông tin từ ${source}, khung giờ ${s.slot_time.slice(0, 5)} nhưng không còn bàn trống đủ ${size} người. Hãy chọn khung giờ khác.` });
    } else {
      const same = prefTable === t.id;
      setNote({
        type: "info",
        text: `Đã điền đủ thông tin từ ${source}: ${nd}, ${s.slot_time.slice(0, 5)}, ${t.name}` +
          (key !== "draft" && !same ? ` (bàn gốc đang được giữ nên tự chọn ${t.name} còn trống, bạn có thể đổi lại)` : "") +
          ". Bấm Nhân viên bấm Đặt bàn để bắt đầu.",
      });
    }
  };

  const start = async () => {
    const r = await post("/dirty-read/t1/start", {
      slot_id: Number(form.slot_id), table_id: Number(form.table_id),
      customer_name: form.name, phone: form.phone, party_size: Number(form.size),
    });
    if (!r.ok) return fail(r);
    setNote(null); setT2(null);
    add("T1", `Nhân viên: BEGIN; INSERT đơn của "${form.name}" (${form.size} người, ${r.data.table_name}, ${day} ${slot.slot_time.slice(0, 5)}); ` +
      `UPDATE chỗ đã đặt ${r.data.base_seats} → ${r.data.t1_seats} (CHƯA COMMIT)`);
    loadAll();
  };

  const read = async () => {
    const r = await post("/dirty-read/t2/read", {
      slot_id: Number(form.slot_id), table_id: Number(form.table_id), level,
    });
    if (!r.ok) return fail(r);
    setNote(null); setT2(r.data);
    add("T2", `Khách [${r.data.iso}]: xem khung giờ → còn ${r.data.seen_left} chỗ, ${table.name} ${r.data.seen_taken ? "đã được đặt" : "còn trống"}` +
      (r.data.t1_open ? ` (lúc này nhân viên đang giữ số liệu chưa commit: còn ${r.data.theory_left} chỗ)` : ""));
  };

  const finish = async (action) => {
    if (action === "commit" &&
        !window.confirm("COMMIT sẽ lưu THẬT một đơn đặt bàn vào database (bạn sẽ thấy nó ở tab Đặt bàn, và số chỗ của khung giờ bị giảm). Tiếp tục?")) {
      return;
    }
    const r = await post("/dirty-read/t1/finish", { action });
    if (!r.ok) return fail(r);
    setNote(action === "commit"
      ? { type: "ok", text: `✔ Đã COMMIT: đơn #${r.data.res_id} được lưu thật. Có thể hủy ở tab Đặt bàn nếu không muốn giữ.` }
      : { type: "info", text: "Đã ROLLBACK: đơn chưa từng tồn tại, dữ liệu thật không thay đổi." });
    add("T1", action === "commit"
      ? `Nhân viên: COMMIT → đơn #${r.data.res_id} chính thức được lưu`
      : "Nhân viên: ROLLBACK → hủy đơn và số chỗ, mọi thứ quay về như cũ");
    setT2(null);
    loadAll();
  };

  const open = t1.t1_open;
  const ready = form.slot_id && form.table_id && form.name && form.phone && Number(form.size) > 0;
  const hasDraft = !!(draft.customer_name || draft.phone);

  return (
    <div>
      <h2>Module 2: Dirty Read (đọc dữ liệu chưa commit)</h2>
      <p>
        Nhân viên (T1) đang nhập một đơn đặt bàn nhưng <b>chưa bấm lưu</b>. Cùng lúc, Khách (T2) mở trang xem
        khung giờ đó còn bao nhiêu chỗ và bàn có trống không. Nếu khách nhìn thấy số liệu của đơn chưa lưu,
        đó là <b>dirty read</b>. Dữ liệu ở đây là dữ liệu thật của trang Đặt bàn.
      </p>

      {loadError && (
        <div className="note err big">
          ✘ Không tải được dữ liệu: {loadError}
          <br /><button className="secondary" onClick={() => loadAll()}>Thử tải lại</button>
        </div>
      )}

      <div className="guide">
        <b>Cách thử:</b> ở khung T1, chọn <b>"Điền nhanh từ thông tin đã nhập ở trang Đặt bàn"</b> (tên, SĐT, ngày, khung giờ,
        bàn, số người được điền đủ, bàn trống được tự chọn) → bấm <b>Nhân viên bấm Đặt bàn (chưa commit)</b> → chọn READ UNCOMMITTED →
        bấm <b>Khách xem chỗ trống và bàn</b> → bấm <b>ROLLBACK</b>.<br />
        <b>Hệ quản trị cho phép dirty read</b> (ví dụ SQL Server với NOLOCK): khách thấy khung giờ ít chỗ hơn và bàn đã bị đặt,
        nhưng đó là con số ma vì nhân viên đã hủy.<br />
        <b>PostgreSQL:</b> khách luôn thấy dữ liệu đã commit, dù chọn mức nào. ROLLBACK không làm đổi dữ liệu thật.
        COMMIT thì <b>tạo một đơn thật</b> (có hộp thoại xác nhận).<br />
        <b>Lưu ý:</b> trong lúc nhân viên chưa kết thúc, khung giờ này bị khóa. Hãy bấm ROLLBACK hoặc COMMIT trước khi sang tab Đặt bàn.
      </div>

      <div className="grid2">
        <div className="panel">
          <h3 className="panel-title">T1: Nhân viên nhập đơn (người ghi)</h3>

          <label className="field">Điền nhanh từ thông tin đã nhập ở trang Đặt bàn
            <select value={pick} disabled={open} onChange={(e) => applyPick(e.target.value)}>
              <option value="">-- Chọn để tự động điền --</option>
              {hasDraft && (
                <option value="draft">
                  Đang nhập dở: {draft.customer_name || "(chưa có tên)"} - {draft.phone || "(chưa có SĐT)"}
                </option>
              )}
              {reservations.slice(0, 30).map((r) => (
                <option key={r.id} value={r.id}>
                  #{r.id} {r.customer_name} - {r.phone} - {r.party_size} người - {r.slot_date} {r.slot_time.slice(0, 5)} - {r.table_name}
                  {r.status !== "confirmed" ? " (đã hủy)" : ""}
                </option>
              ))}
            </select>
          </label>
          {!hasDraft && reservations.length === 0 && (
            <div className="note warn">Chưa có thông tin nào ở trang Đặt bàn. Hãy nhập thủ công bên dưới hoặc đặt thử một đơn trước.</div>
          )}

          <label className="field">Tên khách
            <input name="name" value={form.name} disabled={open} onChange={change} />
          </label>
          <label className="field">Số điện thoại
            <input name="phone" value={form.phone} disabled={open} onChange={change} />
          </label>
          <label className="field">Ngày đặt
            <input type="date" value={day} min={todayStr()} max={maxDateStr()} disabled={open}
                   onChange={(e) => changeDay(e.target.value)} />
          </label>
          <label className="field">Khung giờ
            <select name="slot_id" value={form.slot_id} disabled={open} onChange={change}>
              <option value="" disabled>-- Chọn khung giờ --</option>
              {slots.map((s) => (
                <option key={s.id} value={s.id} disabled={isPast(s) || left(s) <= 0}>
                  {s.slot_time.slice(0, 5)} (còn {left(s)} chỗ){isPast(s) ? " - đã qua" : left(s) <= 0 ? " - hết chỗ" : ""}
                </option>
              ))}
            </select>
          </label>
          <label className="field">Bàn
            <select name="table_id" value={form.table_id} disabled={open} onChange={change}>
              <option value="" disabled>-- Chọn bàn --</option>
              {tables.map((t) => (
                <option key={t.id} value={t.id} disabled={takenTables.has(t.id)}>
                  {t.name} - {t.capacity} người - {t.area}{takenTables.has(t.id) ? " - đã đặt" : ""}
                </option>
              ))}
            </select>
          </label>
          <label className="field">Số lượng người
            <input name="size" type="number" min="1" max={table ? table.capacity : undefined}
                   value={form.size} disabled={open} onChange={change} />
          </label>
          <div className="btn-row">
            <button onClick={start} disabled={open || !ready}>Nhân viên bấm Đặt bàn (chưa commit)</button>
          </div>
          {!open && !ready && (
            <div className="note warn">
              Cần đủ: tên, SĐT, khung giờ, bàn và số người thì mới bấm được. Thiếu: {" "}
              {[!form.name && "tên", !form.phone && "SĐT", !form.slot_id && "khung giờ", !form.table_id && "bàn"].filter(Boolean).join(", ") || "số người"}.
            </div>
          )}
          <div className="btn-row" style={{ marginTop: 8 }}>
            <button className="secondary" onClick={() => finish("rollback")} disabled={!open}>ROLLBACK (không đổi dữ liệu)</button>
            <button className="secondary" onClick={() => finish("commit")} disabled={!open}>COMMIT (tạo đơn thật)</button>
          </div>
        </div>

        <div className="panel">
          <h3 className="panel-title">T2: Khách xem khung giờ (người đọc)</h3>
          <p style={{ margin: "0 0 10px" }}>
            Khách xem đúng khung giờ và bàn mà nhân viên đang chọn ở bên trái.
          </p>
          <div>
            {LEVELS.map(([key, label]) => (
              <label key={key}>
                <input type="radio" checked={level === key} onChange={() => setLevel(key)} />
                {label}
              </label>
            ))}
          </div>
          <div className="btn-row">
            <button onClick={read} disabled={!form.slot_id || !form.table_id}>Khách xem chỗ trống và bàn</button>
          </div>
        </div>
      </div>

      <div className="panel" style={{ marginTop: 16 }}>
        <h3 className="panel-title">Thực tế trong database (khung giờ đang chọn)</h3>
        <div className="stats">
          <div>
            <span>Chỗ còn lại, dữ liệu đã COMMIT</span>
            <b>{slot ? `${left(slot)} / ${slot.max_seats}` : "—"}</b>
          </div>
          <div>
            <span>Nhân viên đang giữ (chưa commit)</span>
            <b>{open && t1.max_seats != null ? `${t1.max_seats - t1.t1_seats} / ${t1.max_seats}` : "—"}</b>
          </div>
        </div>
      </div>

      {note && <div className={"note big " + note.type}>{note.text}</div>}

      {t2 && (
        <>
          {t2.dirty ? (
            <div className="note err big">
              ✘ DIRTY READ: khách đọc được số liệu chưa commit của nhân viên.
            </div>
          ) : t2.t1_open ? (
            <div className="note ok big">
              ✔ KHÔNG có dirty read: khách thấy còn {t2.seen_left} chỗ và {table?.name} {t2.seen_taken ? "đã đặt" : "còn trống"} (dữ liệu đã commit),
              không thấy đơn chưa lưu của nhân viên. Mức cô lập báo về là "{t2.iso}", vì PostgreSQL xử lý READ UNCOMMITTED như READ COMMITTED.
            </div>
          ) : (
            <div className="note info big">
              Nhân viên chưa có giao dịch nào đang mở nên khách chỉ đọc dữ liệu đã commit: còn {t2.seen_left} chỗ,
              {" "}{table?.name} {t2.seen_taken ? "đã đặt" : "còn trống"}.
            </div>
          )}

          {t2.t1_open && (
            <div className="compare">
              <div>
                <small>PostgreSQL (kết quả thật)</small>
                <b>còn {t2.seen_left} chỗ</b>
                <small>{table?.name}: {t2.seen_taken ? "đã đặt" : "còn trống"}</small>
              </div>
              <div className="theory">
                <small>Lý thuyết READ UNCOMMITTED chuẩn (không chạy thật)</small>
                <b>còn {t2.theory_left} chỗ</b>
                <small>{table?.name}: đã đặt. Nếu nhân viên ROLLBACK, đơn này chưa từng tồn tại, đó là dữ liệu "bẩn".</small>
              </div>
            </div>
          )}
        </>
      )}

      <EventLog items={log} />
      <button className="secondary" onClick={async () => { await post("/dirty-read/reset"); setT2(null); setNote(null); setPick(""); clear(); loadAll(); }}>
        🔄 Làm lại từ đầu (ROLLBACK nếu đang mở)
      </button>
    </div>
  );
}