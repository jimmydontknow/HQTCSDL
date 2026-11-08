import { useEffect, useState } from "react";
import { get, post, errText, EventLog, useLog } from "./shared";

const LEVELS = [
  ["read_committed", "READ COMMITTED"],
  ["repeatable_read", "REPEATABLE READ"],
  ["serializable", "SERIALIZABLE"],
];

export default function PhantomRead() {
  const [db, setDb] = useState(null);
  const [tables, setTables] = useState([]);
  const [level, setLevel] = useState("read_committed");
  const [minSize, setMinSize] = useState(1);
  const [form, setForm] = useState({ name: "Khách B", size: 2, table: 1 });
  const [r1, setR1] = useState(null);      // { rows, iso }
  const [r2, setR2] = useState(null);      // { rows, newIds, phantom }
  const [note, setNote] = useState(null);
  const { log, add, clear } = useLog();

  const refresh = async () => {
    const r = await get("/phantom-read/state");
    if (r.ok) setDb(r.data);
  };

  const reset = async () => {
    const r = await post("/phantom-read/reset");
    if (r.ok) setDb(r.data);
    setR1(null); setR2(null); setNote(null); clear();
  };

  useEffect(() => {
    get("/tables").then((r) => { if (r.ok) setTables(r.data); });
    reset();
    return () => { post("/phantom-read/reset"); };   // rời tab thì xóa đơn demo
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fail = (r) => setNote({ type: "err", text: `✘ ${errText(r.data)}` });

  const count1 = async () => {
    const r = await post("/phantom-read/a/count1", { level, min_size: Number(minSize) });
    if (!r.ok) return fail(r);
    setNote(null); setR2(null);
    setR1({ rows: r.data.rows, iso: r.data.iso });
    add("A", `BEGIN [${r.data.iso}]; đếm đơn có từ ${minSize} người trở lên → ${r.data.rows.length} đơn`);
    refresh();
  };

  const count2 = async () => {
    const r = await post("/phantom-read/a/count2");
    if (!r.ok) return fail(r);
    setNote(null);
    setR2({ rows: r.data.rows, newIds: r.data.new_ids, phantom: r.data.phantom });
    add("A", `Chạy lại đúng câu truy vấn đó (cùng transaction) → ${r.data.rows.length} đơn`);
    refresh();
  };

  const insert = async () => {
    const r = await post("/phantom-read/b/insert", {
      customer_name: form.name, party_size: Number(form.size), table_id: Number(form.table),
    });
    if (!r.ok) return fail(r);
    setNote(null);
    add("B", `INSERT đơn của "${form.name}" (${form.size} người, ${r.data.table_name}); COMMIT`);
    refresh();
  };

  const commitA = async () => {
    const r = await post("/phantom-read/a/commit");
    if (!r.ok) return fail(r);
    setNote(null); setDb(r.data);
    add("A", "COMMIT (kết thúc transaction của A)");
  };

  const renderRows = (rows, newIds = []) => (
    <div className="chips">
      {rows.length === 0 && <span className="chip empty">(không có đơn nào)</span>}
      {rows.map((x) => (
        <span key={x.id} className={"chip" + (newIds.includes(x.id) ? " ghost" : "")}>
          {newIds.includes(x.id) ? "👻 " : ""}#{x.id} {x.customer_name} ({x.party_size} người)
        </span>
      ))}
    </div>
  );

  return (
    <div>
      <h2>Module 4: Phantom Read (đọc dòng "ma")</h2>
      <p>
        Quản lý A lập báo cáo bằng cách đếm các đơn đặt bàn của khung giờ <b>{db?.slot_label ?? "…"}</b> (id = 3)
        có từ <b>N người</b> trở lên. Giữa hai lần đếm, khách B đặt thêm một bàn. Nếu lần đếm thứ hai
        xuất hiện thêm đơn mà lần đầu không có, đó là <b>phantom read</b>.
      </p>

      <div className="guide">
        <b>Cách gây lỗi:</b> READ COMMITTED, N = 1 → <b> A đếm lần 1</b> → B giữ nguyên (Bàn 1, 2 người), bấm <b> B đặt bàn</b> → <b> A đếm lần 2</b>.<br />
        <b>Cách không lỗi:</b> (a) chọn <b>REPEATABLE READ</b> rồi làm lại đúng thứ tự, hoặc (b) READ COMMITTED nhưng A nhập <b>N = 4</b> và B đặt <b>2 người</b>:
        đơn mới không thỏa điều kiện "từ 4 người" nên không lọt vào kết quả của A. Đổi B thành 4 người (Bàn 2) thì phantom xuất hiện lại.
      </div>

      <div className="grid2">
        <div className="panel">
          <h3 className="panel-title">Quản lý A (đếm 2 lần)</h3>
          <div>
            {LEVELS.map(([key, label]) => (
              <label key={key}>
                <input type="radio" checked={level === key} disabled={db?.a_open}
                       onChange={() => setLevel(key)} />
                {label}
              </label>
            ))}
          </div>
          <label className="field">Chỉ đếm đơn có từ N người trở lên (N =)
            <input type="number" min="1" max="20" value={minSize} disabled={db?.a_open}
                   onChange={(e) => setMinSize(e.target.value)} />
          </label>
          <div className="btn-row">
            <button onClick={count1} disabled={db?.a_open}> A đếm lần 1</button>
            <button onClick={count2} disabled={!db?.a_open}> A đếm lần 2</button>
          </div>
          <div className="btn-row" style={{ marginTop: 8 }}>
            <button className="secondary" onClick={commitA} disabled={!db?.a_open}> A COMMIT</button>
          </div>
        </div>

        <div className="panel">
          <h3 className="panel-title">Khách B (đặt bàn mới)</h3>
          <label className="field">Tên khách
            <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          </label>
          <div className="two-col">
            <label className="field">Số người
              <input type="number" min="1" max="20" value={form.size}
                     onChange={(e) => setForm({ ...form, size: e.target.value })} />
            </label>
            <label className="field">Bàn
              <select value={form.table} onChange={(e) => setForm({ ...form, table: e.target.value })}>
                {tables.map((t) => (
                  <option key={t.id} value={t.id}>{t.name} ({t.capacity} chỗ)</option>
                ))}
              </select>
            </label>
          </div>
          <div className="btn-row">
            <button onClick={insert}> B đặt bàn + COMMIT</button>
          </div>
        </div>
      </div>

      <div className="grid2">
        <div className="panel">
          <h3 className="panel-title">A đếm lần 1</h3>
          {r1 ? <>{renderRows(r1.rows)}<b>{r1.rows.length} đơn</b></> : <span className="chip empty">Chưa đếm</span>}
        </div>
        <div className="panel">
          <h3 className="panel-title">A đếm lần 2</h3>
          {r2 ? <>{renderRows(r2.rows, r2.newIds)}<b>{r2.rows.length} đơn</b></> : <span className="chip empty">Chưa đếm</span>}
        </div>
      </div>

      <div className="panel" style={{ marginTop: 16 }}>
        <h3 className="panel-title">Tất cả đơn thật trong database ở khung giờ này</h3>
        {renderRows(db?.rows_in_db ?? [])}
      </div>

      {note && <div className={"note big " + note.type}>{note.text}</div>}

      {r2 && (r2.phantom ? (
        <div className="note err big">
          ✘ PHANTOM READ: lần 1 có {r1.rows.length} đơn, lần 2 có {r2.rows.length} đơn.
          Dòng 👻 là dòng "ma" xuất hiện giữa hai lần truy vấn trong cùng một transaction.
        </div>
      ) : (
        <div className="note ok big">
          ✔ Không có phantom read: hai lần đếm đều ra {r2.rows.length} đơn.
          {db && db.rows_in_db.length > r2.rows.length
            ? " DB đã có thêm đơn mới, nhưng A không thấy vì đơn đó không thỏa điều kiện lọc hoặc A đang dùng snapshot cố định."
            : ""}
        </div>
      ))}

      <EventLog items={log} />
      <button className="secondary" onClick={reset}>🔄 Làm lại từ đầu (xóa đơn demo)</button>
    </div>
  );
}