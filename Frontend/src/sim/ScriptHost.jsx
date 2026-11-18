import { useEffect, useState } from "react";
import { get, post, errText } from "../shared";

const NEED_VERSION = 6;

const BADGE = {
  waiting: ["⏳ ĐANG CHỜ (bị khóa chặn)", "#fef3c7", "#b45309"],
  running: ["⚙ đang chạy…", "#dbeafe", "#1d4ed8"],
  queued: ["⏳ xếp hàng", "#fef3c7", "#b45309"],
  error: ["✘ có lỗi", "#fee2e2", "#b91c1c"],
};

function Sql({ lines }) {
  return (
    <div style={{ fontFamily: "Consolas, 'Courier New', monospace", fontSize: 12.5, lineHeight: 1.5 }}>
      {lines.map((l, i) => {
        const t = l.trim();
        const bug = /--.*LỖI/.test(l), fix = /--.*SỬA/.test(l), com = t.startsWith("--");
        return (
          <div key={i} style={{
            whiteSpace: "pre-wrap", padding: "0 6px", borderRadius: 3,
            background: bug ? "#fee2e2" : fix ? "#dcfce7" : "transparent",
            color: bug ? "#991b1b" : fix ? "#166534" : com ? "#64748b" : "#0f172a",
            fontStyle: com ? "italic" : "normal",
          }}>{l || " "}</div>
        );
      })}
    </div>
  );
}

function Cell({ step }) {
  const b = BADGE[step.status];
  const waitedDone = step.waited && step.status === "done";
  return (
    <div>
      {b && <span style={{ background: b[1], color: b[2], borderRadius: 999, padding: "1px 10px", fontSize: 12, fontWeight: 700 }}>{b[0]}</span>}
      {waitedDone && <span style={{ background: "#fef3c7", color: "#b45309", borderRadius: 999, padding: "1px 10px", fontSize: 12, fontWeight: 700 }}>✔ xong (đã phải CHỜ khóa)</span>}
      <Sql lines={step.lines} />
      {step.results.length > 0 && (
        <div style={{ background: "#0f172a", color: "#e2e8f0", borderRadius: 6, padding: "4px 8px", marginTop: 4,
                      fontFamily: "Consolas, monospace", fontSize: 12 }}>
          {step.results.map((r, i) => (
            <div key={i} style={{ color: r.error ? "#fca5a5" : "#e2e8f0" }}>{r.text}</div>
          ))}
        </div>
      )}
    </div>
  );
}

// Gom các câu SQL của một giao tác (T1 hoặc T2) theo thứ tự thời gian, để chép sang tab pgAdmin
function sqlOf(steps, who) {
  return (steps || []).filter((s) => s.who === who)
    .map((s) => `-- ${s.time}\n` + s.lines.join("\n")).join("\n\n");
}

export default function ScriptHost({ cfg }) {
  const [copied, setCopied] = useState("");
  const copy = async (who) => {
    try { await navigator.clipboard.writeText(sqlOf(st?.steps, who)); setCopied(who); setTimeout(() => setCopied(""), 1800); }
    catch { setCopied("lỗi"); }
  };
  const [st, setSt] = useState(null);
  const [err, setErr] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = async () => {
    const r = await get(`${cfg.prefix}/state`);
    if (r.ok) { setSt(r.data); setErr(null); } else setErr(errText(r.data));
  };
  const act = async (path, body) => {
    setBusy(true);
    const r = await post(`${cfg.prefix}${path}`, body);
    if (r.ok) setSt(r.data); else setErr(errText(r.data));
    setBusy(false);
  };

  useEffect(() => {
    act("/reset");
    const t = setInterval(load, 700);
    return () => { clearInterval(t); post(`${cfg.prefix}/reset`); };   // rời tab: hủy giao dịch, nhả khóa
  }, []);   // eslint-disable-line

  const v = st?.verdict;
  const done = st && st.cursor >= st.total;

  return (
    <div>
      <h2>{cfg.title}</h2>
      <p>{cfg.story}</p>

      {err && <div className="note err big">✘ {err}</div>}
      {st && st.v !== NEED_VERSION && <div className="note err big">✘ Backend đang chạy bản cũ. Thay file Backend và chạy lại uvicorn.</div>}
      {st?.error && <div className="note err big">✘ {st.error}</div>}

      <div style={{ background: "#eef2ff", borderLeft: "5px solid #4f46e5", borderRadius: 8, padding: "10px 16px", margin: "12px 0" }}>
        <b>Cách dùng:</b> chọn một kịch bản → bấm <b>▶ Bước tiếp theo</b> để chạy từng bước (hoặc <b>⏩ Chạy tất cả</b>).
        Mỗi ô là câu SQL thật chạy trên một phiên riêng (T1 hoặc T2). Kịch bản nằm trong file <code>Backend/scripts/{st?.file}</code>.
      </div>

      <div>
        {(st?.scenarios || []).map((s) => (
          <label key={s.key}>
            <input type="radio" name={"scn-" + cfg.key} checked={st.scenario === s.key} disabled={busy}
                   onChange={() => act("/select", { scenario: s.key })} />
            {s.title}
          </label>
        ))}
      </div>
      {st?.note && <div className="guide">{st.note}</div>}

      <div className="btn-row" style={{ margin: "10px 0" }}>
        <button onClick={() => act("/next")} disabled={busy || done || st?.auto}>▶ Bước tiếp theo</button>
        <button onClick={() => act("/all")} disabled={busy || done || st?.auto}>⏩ Chạy tất cả</button>
        <button className="secondary" onClick={() => act("/reset")} disabled={busy}>🔄 Làm lại</button>
        <span style={{ alignSelf: "center", color: "var(--muted)" }}>Đã chạy {st?.cursor ?? 0}/{st?.total ?? 0} bước</span>
      </div>

      <table>
        <thead><tr><th style={{ width: 60 }}>Thời gian</th><th>Giao tác 1 (T1)</th><th>Giao tác 2 (T2)</th></tr></thead>
        <tbody>
          {(st?.steps || []).map((s) => {
            const future = s.idx >= st.cursor;
            const style = { opacity: future ? 0.5 : 1, background: s.idx === st.cursor ? "#fffbeb" : undefined };
            return (
              <tr key={s.idx} style={style}>
                <td><b>{s.time}</b></td>
                {s.who === "SYS" ? (
                  <td colSpan={2}><i style={{ color: "#64748b" }}>Kiểm tra (hệ thống)</i><Cell step={s} /></td>
                ) : (
                  <>
                    <td>{s.who === "T1" && <Cell step={s} />}</td>
                    <td>{s.who === "T2" && <Cell step={s} />}</td>
                  </>
                )}
              </tr>
            );
          })}
        </tbody>
      </table>

      {st?.setup?.length > 0 && (
        <details style={{ margin: "8px 0" }}>
          <summary style={{ cursor: "pointer", color: "#4f46e5", fontWeight: 600 }}>Chuẩn bị dữ liệu (hệ thống tự chạy trước)</summary>
          <Sql lines={st.setup} />
        </details>
      )}

      {v && (
        <>
          <div className={"note big " + (v.bug ? "err" : "ok")}>{v.bug ? "✘ " : "✔ "}{v.headline}</div>
          {v.explain?.length > 0 && (
            <div className="panel" style={{ marginTop: 12 }}>
              <h3 className="panel-title">Vì sao ra kết quả này?</h3>
              <ol>{v.explain.map((t, i) => <li key={i}>{t}</li>)}</ol>
            </div>
          )}
          {v.fix?.length > 0 && (
            <div className="panel" style={{ marginTop: 12 }}>
              <h3 className="panel-title">Cách sửa</h3>
              <ul>{v.fix.map((t, i) => <li key={i}>{t}</li>)}</ul>
            </div>
          )}
        </>
      )}

      {cfg.reference && (
        <details style={{ margin: "14px 0" }}>
          <summary style={{ cursor: "pointer", fontWeight: 600, color: "#4f46e5" }}>{cfg.reference.title}</summary>
          <p>{cfg.reference.note}</p>
          <table>
            <thead><tr><th style={{ width: 60 }}>Thời gian</th><th>Giao tác 1 (T1)</th><th>Giao tác 2 (T2)</th></tr></thead>
            <tbody>
              {cfg.reference.rows.map((r) => (
                <tr key={r.t}>
                  <td><b>{r.t}</b></td>
                  <td>{r.t1 && <Sql lines={r.t1.split("\n")} />}</td>
                  <td>{r.t2 && <Sql lines={r.t2.split("\n")} />}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </details>
      )}

      <div className="btn-row" style={{ marginTop: 16 }}>
        <button className="secondary" onClick={() => copy("T1")}>📋 Chép SQL của T1</button>
        <button className="secondary" onClick={() => copy("T2")}>📋 Chép SQL của T2</button>
        {copied && <span style={{ alignSelf: "center", color: copied === "lỗi" ? "#b91c1c" : "#047857" }}>
          {copied === "lỗi" ? "Trình duyệt không cho chép, hãy bôi đen và chép tay" : `Đã chép SQL của ${copied}`}
        </span>}
      </div>
      <div className="guide" style={{ marginTop: 8 }}>
        <b>Chạy tay trong pgAdmin:</b> mở 2 tab Query Tool. Chép các câu của T1 vào tab 1 và các câu của T2 vào tab 2, chạy đúng thứ tự
        thời gian t1, t2, t3... Bước nào bị khóa chặn thì tab đó sẽ đứng chờ đến khi tab kia COMMIT hoặc ROLLBACK.
      </div>
    </div>
  );
}
