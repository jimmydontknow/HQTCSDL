import { useState, useCallback } from "react";

export const API = "http://localhost:8000";

export function errText(data) {
  if (!data) return "Lỗi không xác định";
  if (typeof data.detail === "string") return data.detail;
  if (Array.isArray(data.detail)) return "Dữ liệu nhập chưa hợp lệ, hãy kiểm tra lại các ô nhập.";
  return "Lỗi không xác định";
}

async function request(path, options) {
  try {
    const r = await fetch(API + path, options);
    let data = null;
    try { data = await r.json(); } catch { /* không có nội dung */ }
    return { ok: r.ok, data };
  } catch {
    return { ok: false, data: { detail: "Không kết nối được backend. Hãy kiểm tra uvicorn đã chạy chưa." } };
  }
}

export const get = (path) => request(path);

export const post = (path, body) =>
  request(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body ?? {}),
  });

export const money = (n) => (n ?? 0).toLocaleString("vi-VN") + "đ";

export function useLog() {
  const [log, setLog] = useState([]);
  const add = useCallback((who, text) => setLog((l) => [...l, { who, text }]), []);
  const clear = useCallback(() => setLog([]), []);
  return { log, add, clear };
}

export function EventLog({ items }) {
  return (
    <div className="terminal">
      {items.length === 0 && <div className="empty">Chưa có thao tác nào. Hãy bấm các nút theo hướng dẫn ở trên…</div>}
      {items.map((it, i) => (
        <div className="line" key={i}>
          <span className={"tag " + it.who}>{it.who}</span>
          {it.text}
        </div>
      ))}
    </div>
  );
}