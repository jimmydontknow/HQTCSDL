import { useEffect, useState } from "react";
import { get, post, errText, money, EventLog, useLog } from "./shared";

const LEVELS = [
  ["read_committed", "READ COMMITTED"],
  ["repeatable_read", "REPEATABLE READ"],
  ["serializable", "SERIALIZABLE"],
];

export default function UnrepeatableRead() {
  const [db, setDb] = useState(null);
  const [level, setLevel] = useState("read_committed");
  const [price, setPrice] = useState(150000);
  const [reads, setReads] = useState(null);   // { first, second, iso }
  const [note, setNote] = useState(null);
  const { log, add, clear } = useLog();

  const refresh = async () => {
    const r = await get("/unrepeatable-read/state");
    if (r.ok) setDb(r.data);
  };

  const reset = async () => {
    const r = await post("/unrepeatable-read/reset");
    if (r.ok) setDb(r.data);
    setReads(null);
    setNote(null);
    clear();
  };

  useEffect(() => {
    reset();
    return () => { post("/unrepeatable-read/reset"); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fail = (r) => setNote({ type: "err", text: `✘ ${errText(r.data)}` });

  const read1 = async () => {
    const r = await post("/unrepeatable-read/a/read1", { level });
    if (!r.ok) return fail(r);
    setNote(null);
    setReads({ first: r.data.first, second: null, iso: r.data.iso });
    add("A", `BEGIN [${r.data.iso}]; đọc phụ thu lần 1 = ${money(r.data.first)}`);
    refresh();
  };

  const read2 = async () => {
    const r = await post("/unrepeatable-read/a/read2");
    if (!r.ok) return fail(r);
    setNote(null);
    setReads((p) => ({ ...p, second: r.data.second }));
    add("A", `Đọc phụ thu lần 2 (cùng transaction) = ${money(r.data.second)}`);
    refresh();
  };

  const bUpdate = async () => {
    const r = await post("/unrepeatable-read/b/update", { new_surcharge: Number(price) });
    if (!r.ok) return fail(r);
    setNote(null);
    setDb(r.data);
    add("B", `UPDATE phụ thu = ${money(Number(price))}; COMMIT (đã lưu thật vào database)`);
  };

  const commitA = async () => {
    const r = await post("/unrepeatable-read/a/commit");
    if (!r.ok) return fail(r);
    setNote(null);
    setDb(r.data);
    add("A", "COMMIT (kết thúc transaction của A)");
  };

  const done = reads && reads.second !== null;
  const changed = done && reads.first !== reads.second;

  return (
    <div>
      <h2>Module 3: Unrepeatable Read (đọc lặp lại không nhất quán)</h2>
      <p>
        <b>{db?.table_name ?? "Bàn 3"}</b> (sân vườn) đang có phụ thu gốc <b>{money(50000)}</b>.
        Khách A xem báo giá hai lần trong cùng một transaction (lúc đặt và lúc thanh toán).
        Giữa hai lần xem, Quản lý B đổi giá và lưu luôn. Nếu hai lần A thấy khác nhau thì đó là <b>unrepeatable read</b>.
      </p>

      <div className="guide">
        <b>Cách gây lỗi:</b> chọn READ COMMITTED → bấm <b> A xem lần 1</b> → để B nhập <b>150000</b>, bấm <b> B sửa giá</b> → bấm <b> A xem lần 2</b>.<br />
        <b>Cách không lỗi:</b> (a) chọn <b>REPEATABLE READ</b> và làm đúng thứ tự trên, hoặc (b) giữ READ COMMITTED nhưng B nhập đúng <b>50000</b> (giá không đổi), hoặc (c) bấm  trước khi B sửa.
      </div>

      <div className="grid2">
        <div className="panel">
          <h3 className="panel-title">Khách A (đọc 2 lần)</h3>
          <div>
            {LEVELS.map(([key, label]) => (
              <label key={key}>
                <input type="radio" checked={level === key} disabled={db?.a_open}
                       onChange={() => setLevel(key)} />
                {label}
              </label>
            ))}
          </div>
          <div className="btn-row">
            <button onClick={read1} disabled={db?.a_open}> A xem phụ thu lần 1</button>
            <button onClick={read2} disabled={!db?.a_open}> A xem phụ thu lần 2</button>
          </div>
          <div className="btn-row" style={{ marginTop: 8 }}>
            <button className="secondary" onClick={commitA} disabled={!db?.a_open}> A COMMIT (kết thúc)</button>
          </div>
        </div>

        <div className="panel">
          <h3 className="panel-title">Quản lý B (sửa giá)</h3>
          <label className="field">Phụ thu mới của Bàn 3 (đồng)
            <input type="number" min="0" step="1000" value={price} onChange={(e) => setPrice(e.target.value)} />
          </label>
          <div className="btn-row">
            <button onClick={bUpdate}> B sửa giá + COMMIT</button>
          </div>
        </div>
      </div>

      <div className="panel" style={{ marginTop: 16 }}>
        <h3 className="panel-title">Số liệu</h3>
        <div className="stats">
          <div><span>Phụ thu hiện tại trong DB</span><b>{db ? money(db.surcharge) : "…"}</b></div>
          <div><span>A đọc lần 1</span><b>{reads ? money(reads.first) : "—"}</b></div>
          <div><span>A đọc lần 2</span><b>{done ? money(reads.second) : "—"}</b></div>
        </div>
      </div>

      {note && <div className={"note big " + note.type}>{note.text}</div>}

      {done && (changed ? (
        <div className="note err big">
          ✘ UNREPEATABLE READ: cùng một transaction nhưng lần 1 = {money(reads.first)}, lần 2 = {money(reads.second)}.
          Khách được báo phụ thu {money(reads.first)} nhưng lúc thanh toán bị tính {money(reads.second)}.
        </div>
      ) : (
        <div className="note ok big">
          ✔ Hai lần đọc nhất quán: cùng = {money(reads.first)}.
          {db && db.surcharge !== reads.second
            ? ` Dù DB hiện đã là ${money(db.surcharge)}, A vẫn thấy giá cũ vì mức ${reads.iso} dùng một snapshot cố định cho cả transaction.`
            : " Trong lúc A đọc, không có thay đổi nào được commit (hoặc giá mới trùng giá cũ)."}
        </div>
      ))}

      <EventLog items={log} />
      <button className="secondary" onClick={reset}>🔄 Làm lại từ đầu</button>
    </div>
  );
}