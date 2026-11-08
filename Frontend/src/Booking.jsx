import { useEffect, useState } from "react";
import { API, get, post, errText, money } from "./shared";

const MAX_DAYS_AHEAD = 60;
const isoDay = (d) => d.toLocaleDateString("en-CA");          // YYYY-MM-DD theo giờ máy
const todayStr = () => isoDay(new Date());
const maxDateStr = () => isoDay(new Date(Date.now() + MAX_DAYS_AHEAD * 86400000));

const DRAFT_KEY = "booking_draft";
const loadDraft = () => {
  try { return JSON.parse(localStorage.getItem(DRAFT_KEY)) || {}; } catch { return {}; }
};

export default function Booking({ active = true }) {
  const draft = loadDraft();
  const [day, setDay] = useState(draft.day && draft.day >= todayStr() ? draft.day : todayStr());
  const [tables, setTables] = useState([]);
  const [slots, setSlots] = useState([]);
  const [reservations, setReservations] = useState([]);
  const [msg, setMsg] = useState(null);
  const [loadError, setLoadError] = useState(null);
  const [form, setForm] = useState({
    customer_name: draft.customer_name || "",
    phone: draft.phone || "",
    table_id: "",
    slot_id: "",
    party_size: draft.party_size || 2,
  });

  // lưu nháp (tên, SĐT, ngày, số người) để mở lại vẫn còn
  useEffect(() => {
    try {
      localStorage.setItem(DRAFT_KEY, JSON.stringify({
        day, customer_name: form.customer_name, phone: form.phone, party_size: form.party_size,
      }));
    } catch { /* trình duyệt không cho lưu thì bỏ qua */ }
  }, [day, form.customer_name, form.phone, form.party_size]);

  const loadStatic = async () => {
    const [t, r] = await Promise.all([get("/tables"), get("/reservations")]);
    if (!t.ok || !r.ok) {
      setLoadError(errText((!t.ok ? t : r).data) +
        " (kiểm tra backend uvicorn và dịch vụ PostgreSQL đã chạy chưa)");
      return false;
    }
    setTables(t.data);
    setReservations(r.data);
    return true;
  };

  const loadSlots = async (d) => {
    const s = await get(`/slots?d=${d}`);
    if (!s.ok) { setLoadError(errText(s.data)); return false; }
    setSlots(s.data);
    return true;
  };

  const loadAll = async (d = day) => {
    const ok1 = await loadStatic();
    const ok2 = await loadSlots(d);
    if (ok1 && ok2) setLoadError(null);
  };

    useEffect(() => { if (active) loadAll(day); }, [active]);   // eslint-disable-line

  const changeDay = (d) => {
    if (!d) return;
    setDay(d);
    setForm((f) => ({ ...f, slot_id: "", table_id: "" }));
    setMsg(null);
    loadSlots(d).then((ok) => { if (ok) setLoadError(null); });
  };

  const change = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  const chosenTable = tables.find((t) => String(t.id) === String(form.table_id));

  // bàn đã có người đặt (confirmed) ở khung giờ đang chọn
  const takenTables = new Set(
    reservations
      .filter((r) => String(r.slot_id) === String(form.slot_id) && r.status === "confirmed")
      .map((r) => r.table_id)
  );

  // khung giờ đã qua trong hôm nay
  const nowHM = new Date().toTimeString().slice(0, 5);
  const isPast = (s) => day === todayStr() && s.slot_time.slice(0, 5) <= nowHM;

  const submit = async (e) => {
    e.preventDefault();
    const res = await post("/reservations", {
      ...form,
      table_id: Number(form.table_id),
      slot_id: Number(form.slot_id),
      party_size: Number(form.party_size),
    });
    if (res.ok) {
      setMsg({ type: "ok", text: "✔ " + res.data.message });
      setForm((f) => ({ ...f, customer_name: "", phone: "", table_id: "", slot_id: "" }));
    } else {
      setMsg({ type: "err", text: "✘ " + errText(res.data) });
    }
    loadAll(day);
  };

  const cancel = async (id) => {
    const r = await fetch(`${API}/reservations/${id}`, { method: "DELETE" });
    let data = null;
    try { data = await r.json(); } catch { /* không có nội dung */ }
    setMsg(r.ok
      ? { type: "ok", text: "✔ " + data.message }
      : { type: "err", text: "✘ " + errText(data) });
    loadAll(day);
  };

  return (
    <div>
      <h2>Đặt bàn mới</h2>

      {loadError && (
        <div className="note err big">
          ✘ Không tải được dữ liệu: {loadError}
          <br /><button className="secondary" onClick={() => loadAll(day)}>Thử tải lại</button>
        </div>
      )}
      {msg && <div className={"note big " + msg.type}>{msg.text}</div>}

      <form onSubmit={submit} style={{ display: "grid", gap: 12, maxWidth: 520, marginTop: 12 }}>
        <label className="field">Tên khách
          <input name="customer_name" placeholder="Ví dụ: Trịnh Trần Phương Tuấn" required
                 value={form.customer_name} onChange={change} />
        </label>

        <label className="field">Số điện thoại
          <input name="phone" placeholder="Ví dụ: 0901234567" required
                 value={form.phone} onChange={change} />
        </label>

        <label className="field">Ngày đặt (đặt trước tối đa {MAX_DAYS_AHEAD} ngày)
          <input type="date" value={day} min={todayStr()} max={maxDateStr()}
                 onChange={(e) => changeDay(e.target.value)} required />
        </label>

        <label className="field">Khung giờ
          <select name="slot_id" required value={form.slot_id} onChange={change}>
            <option value="" disabled>-- Chọn khung giờ --</option>
            {slots.map((s) => {
              const left = s.max_seats - s.booked_seats;
              const past = isPast(s);
              return (
                <option key={s.id} value={s.id} disabled={past || left <= 0}>
                  {s.slot_time.slice(0, 5)} (còn {left} chỗ)
                  {past ? " - đã qua" : left <= 0 ? " - hết chỗ" : ""}
                </option>
              );
            })}
          </select>
        </label>

        <label className="field">Bàn
          <select name="table_id" required value={form.table_id} onChange={change}>
            <option value="" disabled>-- Chọn bàn --</option>
            {tables.map((t) => {
              const taken = takenTables.has(t.id);
              return (
                <option key={t.id} value={t.id} disabled={taken}>
                  {t.name} - {t.capacity} người - {t.area}
                  {t.surcharge > 0 ? ` (phụ thu ${money(t.surcharge)})` : ""}
                  {taken ? " - đã đặt" : ""}
                </option>
              );
            })}
          </select>
        </label>

        <label className="field">Số lượng người
          <input name="party_size" type="number" min="1"
                 max={chosenTable ? chosenTable.capacity : undefined}
                 value={form.party_size} onChange={change} />
          {chosenTable && (
            <small style={{ color: "var(--muted)" }}>
              {chosenTable.name} chứa tối đa {chosenTable.capacity} người
            </small>
          )}
        </label>

        <button type="submit">Đặt bàn</button>
      </form>

      <h2 style={{ marginTop: 36 }}>Danh sách đặt bàn</h2>
      <table>
        <thead>
          <tr>
            <th>#</th><th>Khách</th><th>SĐT</th><th>Bàn</th><th>Ngày</th>
            <th>Giờ</th><th>Số người</th><th>Trạng thái</th><th></th>
          </tr>
        </thead>
        <tbody>
          {reservations.length === 0 && (
            <tr><td colSpan="9" style={{ color: "var(--muted)" }}>Chưa có đơn đặt bàn nào.</td></tr>
          )}
          {reservations.map((r) => (
            <tr key={r.id}>
              <td>{r.id}</td><td>{r.customer_name}</td><td>{r.phone}</td>
              <td>{r.table_name}</td><td>{r.slot_date}</td><td>{r.slot_time.slice(0, 5)}</td>
              <td>{r.party_size}</td><td>{r.status}</td>
              <td>{r.status === "confirmed" && <button onClick={() => cancel(r.id)}>Hủy</button>}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}