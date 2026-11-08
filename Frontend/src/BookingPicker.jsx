import { useEffect, useRef, useState } from "react";
import { get, errText } from "./shared";

const MAX_DAYS_AHEAD = 60;
const isoDay = (d) => d.toLocaleDateString("en-CA");
const todayStr = () => isoDay(new Date());
const maxDateStr = () => isoDay(new Date(Date.now() + MAX_DAYS_AHEAD * 86400000));
const nowHM = () => new Date().toTimeString().slice(0, 5);
const loadDraft = () => {
  try { return JSON.parse(localStorage.getItem("booking_draft")) || {}; } catch { return {}; }
};
const pastOn = (d, s) => d === todayStr() && s.slot_time.slice(0, 5) <= nowHM();
const left = (s) => s.max_seats - s.booked_seats;

export default function BookingPicker({ onChange, disabled }) {
  const draft = loadDraft();
  const [day, setDay] = useState(draft.day && draft.day >= todayStr() ? draft.day : todayStr());
  const [tables, setTables] = useState([]);
  const [slots, setSlots] = useState([]);
  const [reservations, setReservations] = useState([]);
  const [form, setForm] = useState({
    name: draft.customer_name || "", phone: draft.phone || "",
    slot_id: "", table_id: "", size: draft.party_size || 2,
  });
  const [pick, setPick] = useState("");
  const [note, setNote] = useState(null);
  const cb = useRef(onChange);
  cb.current = onChange;

  // báo giá trị lên màn hình cha mỗi khi form đổi
  useEffect(() => {
    cb.current({
      slot_id: Number(form.slot_id) || 0, table_id: Number(form.table_id) || 0,
      customer_name: form.name, phone: form.phone, party_size: Number(form.size) || 0,
    });
  }, [form]);

  const load = async (d) => {
    const [tb, sl, rs] = await Promise.all([get("/tables"), get(`/slots?d=${d}`), get("/reservations")]);
    const bad = [tb, sl, rs].find((x) => !x.ok);
    if (bad) { setNote({ type: "err", text: "✘ " + errText(bad.data) }); return null; }
    setTables(tb.data); setSlots(sl.data); setReservations(rs.data);
    return { tb: tb.data, sl: sl.data, rs: rs.data };
  };
  useEffect(() => { load(day); }, []);   // eslint-disable-line

  const change = (e) => { setForm({ ...form, [e.target.name]: e.target.value }); setPick(""); };
  const changeDay = (d) => {
    if (!d) return;
    setDay(d); setPick("");
    setForm((f) => ({ ...f, slot_id: "", table_id: "" }));
    load(d);
  };

  const table = tables.find((t) => String(t.id) === String(form.table_id));
  const taken = new Set(
    reservations.filter((r) => String(r.slot_id) === String(form.slot_id) && r.status === "confirmed").map((r) => r.table_id)
  );

  const chooseFree = (slotsList, resList, tableList, d, size, prefSlot, prefTable) => {
    const ok = (s) => !pastOn(d, s) && left(s) >= size;
    const s = slotsList.find((x) => x.id === prefSlot && ok(x)) || slotsList.find(ok);
    if (!s) return { s: null, t: null };
    const used = new Set(resList.filter((r) => r.slot_id === s.id && r.status === "confirmed").map((r) => r.table_id));
    const free = tableList.filter((t) => !used.has(t.id) && t.capacity >= size)
      .sort((a, b) => a.capacity - b.capacity || a.id - b.id);
    return { s, t: free.find((x) => x.id === prefTable) || free[0] || null };
  };

  const applyPick = async (key) => {
    setPick(key);
    if (!key) return;
    const base = await load(day);
    if (!base) return;
    let nd = todayStr(), name = "", phone = "", size = 2, prefSlot = null, prefTable = null;
    if (key === "draft") {
      const d = loadDraft();
      nd = d.day && d.day >= todayStr() ? d.day : todayStr();
      name = d.customer_name || ""; phone = d.phone || ""; size = Number(d.party_size) || 2;
    } else {
      const r = base.rs.find((x) => String(x.id) === key);
      if (!r) return;
      name = r.customer_name; phone = r.phone; size = r.party_size;
      if (r.slot_date >= todayStr()) { nd = r.slot_date; prefSlot = r.slot_id; prefTable = r.table_id; }
    }
    const sl = await get(`/slots?d=${nd}`);
    if (!sl.ok) { setNote({ type: "err", text: "✘ " + errText(sl.data) }); return; }
    const { s, t } = chooseFree(sl.data, base.rs, base.tb, nd, size, prefSlot, prefTable);
    setDay(nd); setSlots(sl.data);
    setForm({ name, phone, size, slot_id: s ? String(s.id) : "", table_id: t ? String(t.id) : "" });
    setNote(!s || !t
      ? { type: "warn", text: "Đã điền thông tin nhưng không tìm được khung giờ hoặc bàn còn trống phù hợp, hãy chọn tay." }
      : { type: "info", text: `Đã điền đủ: ${nd}, ${s.slot_time.slice(0, 5)}, ${t.name}.` });
  };

  const hasDraft = !!(draft.customer_name || draft.phone);

  return (
    <div>
      <label className="field">Điền nhanh từ thông tin đã nhập ở trang Đặt bàn
        <select value={pick} disabled={disabled} onChange={(e) => applyPick(e.target.value)}>
          <option value="">-- Chọn để tự động điền --</option>
          {hasDraft && <option value="draft">Đang nhập dở: {draft.customer_name || "(chưa có tên)"} - {draft.phone || "(chưa có SĐT)"}</option>}
          {reservations.slice(0, 30).map((r) => (
            <option key={r.id} value={r.id}>
              #{r.id} {r.customer_name} - {r.party_size} người - {r.slot_date} {r.slot_time.slice(0, 5)} - {r.table_name}
              {r.status !== "confirmed" ? " (đã hủy)" : ""}
            </option>
          ))}
        </select>
      </label>
      {note && <div className={"note " + note.type}>{note.text}</div>}

      <label className="field">Tên khách
        <input name="name" value={form.name} disabled={disabled} onChange={change} />
      </label>
      <label className="field">Số điện thoại
        <input name="phone" value={form.phone} disabled={disabled} onChange={change} />
      </label>
      <label className="field">Ngày đặt
        <input type="date" value={day} min={todayStr()} max={maxDateStr()} disabled={disabled}
               onChange={(e) => changeDay(e.target.value)} />
      </label>
      <label className="field">Khung giờ
        <select name="slot_id" value={form.slot_id} disabled={disabled} onChange={change}>
          <option value="" disabled>-- Chọn khung giờ --</option>
          {slots.map((s) => (
            <option key={s.id} value={s.id} disabled={pastOn(day, s) || left(s) <= 0}>
              {s.slot_time.slice(0, 5)} (còn {left(s)} chỗ){pastOn(day, s) ? " - đã qua" : left(s) <= 0 ? " - hết chỗ" : ""}
            </option>
          ))}
        </select>
      </label>
      <label className="field">Bàn
        <select name="table_id" value={form.table_id} disabled={disabled} onChange={change}>
          <option value="" disabled>-- Chọn bàn --</option>
          {tables.map((t) => (
            <option key={t.id} value={t.id} disabled={taken.has(t.id)}>
              {t.name} - {t.capacity} người{taken.has(t.id) ? " - đã đặt" : ""}
            </option>
          ))}
        </select>
      </label>
      <label className="field">Số lượng người
        <input name="size" type="number" min="1" max={table ? table.capacity : undefined}
               value={form.size} disabled={disabled} onChange={change} />
      </label>
    </div>
  );
}