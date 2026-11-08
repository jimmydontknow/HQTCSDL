import { useEffect, useState } from "react";
import { post, errText } from "../shared";
import { useRoomState, Timeline } from "./parts";

const NEED_VERSION = 5;

const stepStyle = {
  background: "#eef2ff", borderLeft: "5px solid #4f46e5", borderRadius: 8,
  padding: "12px 18px", margin: "14px 0",
};

export default function SimHost({ cfg }) {
  const { st, err, reload } = useRoomState(cfg.prefix);
  const [modeKey, setModeKey] = useState(cfg.modes?.[0]?.key || "run");
  const [args, setArgs] = useState(cfg.reset?.defaults || {});
  const [params, setParams] = useState({ A: { ...cfg.defaults.A }, B: { ...cfg.defaults.B } });
  const [note, setNote] = useState(null);
  const [starting, setStarting] = useState(false);

  const setP = (who) => (patch) => setParams((p) => ({ ...p, [who]: { ...p[who], ...patch } }));

  const call = async (path, body) => {
    const r = await post(`${cfg.prefix}${path}`, body);
    setNote(r.ok ? null : { type: "err", text: errText(r.data) });
    setTimeout(reload, 150);
    return r;
  };

  // vào tab: đặt lại dữ liệu demo
  useEffect(() => { call("/mode", { mode: modeKey, args }); }, []);   // eslint-disable-line

  // MỘT NÚT: gửi thông tin của A và B, server tự đặt lại rồi chạy cả hai cùng lúc
  const runDemo = async () => {
    setStarting(true);
    setNote(null);
    const r = await post(`${cfg.prefix}/run-both`, { mode: modeKey, args, A: params.A, B: params.B });
    if (!r.ok) setNote({ type: "err", text: errText(r.data) });
    setStarting(false);
    reload();
    setTimeout(reload, 300);
  };

  const status = st?.status || {};
  const running = Object.values(status).includes("running") || starting;
  const anyUsed = Object.values(status).some((s) => s !== "idle");
  const v = st?.verdict;
  const oldBackend = st && st.v !== NEED_VERSION;
  const Data = cfg.Data;
  const InputsA = cfg.Inputs?.A;
  const InputsB = cfg.Inputs?.B;
  const ResetInputs = cfg.reset?.Inputs;

  return (
    <div>
      <h2>{cfg.title}</h2>
      <p>{cfg.story}</p>

      {err && (
        <div className="note err big">
          ✘ Không kết nối được backend ({err}). Kiểm tra uvicorn đang chạy, PostgreSQL đã bật.
        </div>
      )}
      {!err && oldBackend && (
        <div className="note err big">
          ✘ Backend đang chạy bản cũ. Hãy thay các file Backend theo HUONG_DAN.md rồi tắt uvicorn (Ctrl+C) và chạy lại.
        </div>
      )}
      {st?.data_error && <div className="note err">✘ Không đọc được dữ liệu database: {st.data_error}</div>}

      <div style={stepStyle}>
        <b>Làm theo 4 bước:</b>
        <ol style={{ margin: "6px 0 0 18px", padding: 0 }}>
          <li>Trong <b>pgAdmin</b>: mở file <code style={{ fontWeight: 700 }}>{cfg.file}</code> → bấm <b>F5</b> (chỉ cần làm một lần).</li>
          <li>Bấm <b>▶ Chạy demo</b> bên dưới → xem kết quả <b style={{ color: "#b91c1c" }}>LỖI</b>.</li>
          <li>{cfg.fixStep}</li>
          <li>Bấm <b>▶ Chạy lại demo</b> → kết quả <b style={{ color: "#15803d" }}>HẾT LỖI</b>.</li>
        </ol>
      </div>

      {cfg.modes && (
        <div>
          {cfg.modes.map((m) => (
            <label key={m.key}>
              <input type="radio" name={"mode-" + cfg.key} checked={modeKey === m.key}
                     onChange={() => { setModeKey(m.key); call("/mode", { mode: m.key, args }); }} />
              {m.label}
            </label>
          ))}
        </div>
      )}

      <details style={{ margin: "10px 0" }}>
        <summary style={{ cursor: "pointer", fontWeight: 600, color: "#4f46e5" }}>
          Tùy chỉnh thông tin (không bắt buộc, có sẵn giá trị mặc định)
        </summary>
        <div className="grid2">
          <div className="panel">
            <h3 className="panel-title">{cfg.roles.A}</h3>
            {InputsA && <InputsA params={params.A} set={setP("A")} disabled={running} />}
          </div>
          <div className="panel">
            <h3 className="panel-title">{cfg.roles.B}</h3>
            {InputsB && <InputsB params={params.B} set={setP("B")} disabled={running} />}
          </div>
        </div>
        {ResetInputs && (
          <div className="panel" style={{ marginTop: 12 }}>
            <ResetInputs value={args} set={(p) => setArgs((a) => ({ ...a, ...p }))} />
          </div>
        )}
      </details>

      <div style={{ textAlign: "center", margin: "18px 0" }}>
        <button
          onClick={runDemo}
          disabled={running}
          style={{
            fontSize: 20, padding: "16px 44px", borderRadius: 14,
            background: running ? "#86efac" : "linear-gradient(135deg, #16a34a, #15803d)",
            boxShadow: running ? "none" : "0 6px 16px rgba(22,163,74,.35)",
          }}
        >
          {running ? "⚙ Đang chạy…" : anyUsed ? "▶ Chạy lại demo" : "▶ Chạy demo"}
        </button>
        <div style={{ color: "var(--muted)", fontSize: 13, marginTop: 8 }}>
          A và B được chạy <b>cùng một lúc</b> (mỗi bên là một kết nối database riêng, như hai người thật).
        </div>
        {note && <div className="note err">✘ {note.text}</div>}
      </div>

      {v && (
        <div className={"note big " + (v.bug ? "err" : "ok")} style={{ fontSize: 18 }}>
          {v.bug ? "✘ " : "✔ "}{v.headline}
        </div>
      )}

      <div className="panel" style={{ marginTop: 16 }}>
        <h3 className="panel-title">Diễn biến (đọc từ trên xuống, giây thứ mấy xảy ra việc gì)</h3>
        <Timeline events={st?.events} nameA={cfg.roles.A} nameB={cfg.roles.B} />
      </div>

      {v?.explain?.length > 0 && (
        <div className="panel" style={{ marginTop: 16 }}>
          <h3 className="panel-title">Vì sao ra kết quả này?</h3>
          <ol>{v.explain.map((t, i) => <li key={i}>{t}</li>)}</ol>
        </div>
      )}

      <div className="panel" style={{ marginTop: 16 }}>
        <h3 className="panel-title">Cách sửa lỗi (trong file {cfg.file})</h3>
        {cfg.fixHow}
        {v?.fix?.length > 0 && <ul>{v.fix.map((t, i) => <li key={i}>{t}</li>)}</ul>}
      </div>

      <div className="panel" style={{ marginTop: 16 }}>
        <h3 className="panel-title">Dữ liệu thật trong database</h3>
        {Data && <Data data={st?.data} />}
        <button className="secondary" onClick={() => call("/mode", { mode: modeKey, args })} disabled={running}>
          🔄 Đặt lại dữ liệu demo
        </button>
      </div>
    </div>
  );
}
