import { useEffect, useRef, useState } from "react";
import { get, errText } from "../shared";

// Lấy trạng thái phòng demo từ server, cập nhật liên tục
export function useRoomState(prefix, ms = 800) {
  const [st, setSt] = useState(null);
  const [err, setErr] = useState(null);
  const inflight = useRef(false);

  const reload = async () => {
    if (inflight.current) return;
    inflight.current = true;
    const r = await get(`${prefix}/state`);
    inflight.current = false;
    if (r.ok) { setSt(r.data); setErr(null); } else setErr(errText(r.data));
  };

  useEffect(() => {
    reload();
    const t = setInterval(reload, ms);
    return () => clearInterval(t);
  }, [prefix]);   // eslint-disable-line

  return { st, err, reload };
}

// Bảng thời gian 2 cột: bên trái là A, bên phải là B, hàng trên xảy ra trước
export function Timeline({ events, nameA, nameB }) {
  if (!events || events.length === 0) {
    return (
      <div className="terminal">
        <div className="empty">Chưa có kết quả. Bấm ▶ Chạy demo ở trên…</div>
      </div>
    );
  }
  return (
    <div style={{ overflowX: "auto" }}>
      <table className="timeline">
        <thead>
          <tr><th style={{ width: 80 }}>Giây thứ</th><th>{nameA}</th><th>{nameB}</th></tr>
        </thead>
        <tbody>
          {events.map((e, i) => (
            <tr key={i}>
              <td className="t">{(e.t / 1000).toFixed(1)}s</td>
              <td>{e.who === "A" && <span className={"ev " + e.kind}>{e.text}</span>}</td>
              <td>{e.who === "B" && <span className={"ev " + e.kind}>{e.text}</span>}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
