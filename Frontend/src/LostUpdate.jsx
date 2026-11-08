import { useEffect, useState } from "react";
import { get, post, errText, money } from "./shared";

const blank = (qty) => ({ qty, seen: null, msg: null, confirmed: 0 });

export default function LostUpdate() {
  const [mode, setMode] = useState("unsafe");
  const [stock, setStock] = useState(1);
  const [start, setStart] = useState(1);
  const [food, setFood] = useState(null);
  const [loadError, setLoadError] = useState(null);
  const [p, setP] = useState({ A: blank(1), B: blank(1) });

  const set = (who, patch) => setP((s) => ({ ...s, [who]: { ...s[who], ...patch } }));

  const refresh = async () => {
    const r = await get("/lost-update/food");
    if (!r.ok) { setLoadError(errText(r.data)); return null; }
    setLoadError(null);
    setFood(r.data);
    return r.data;
  };

  const reset = async (s = stock) => {
    const r = await post("/lost-update/reset", { stock: Number(s) });
    if (!r.ok) { setLoadError(errText(r.data)); return; }
    setLoadError(null);
    setFood(r.data);
    setStart(r.data.quantity);
    setP((prev) => ({ A: blank(prev.A.qty), B: blank(prev.B.qty) }));
  };

  useEffect(() => { reset(1); }, []);   // eslint-disable-line

  const changeMode = async (m) => { setMode(m); await reset(); };

  const see = async (who) => {
    const d = await refresh();
    if (!d) {
      set(who, { msg: { type: "err", text: "✘ Không đọc được dữ liệu món ăn (xem khung đỏ phía trên)." } });
      return;
    }
    set(who, {
      seen: { qty: d.quantity, version: d.version },
      msg: { type: "info", text: `Khách ${who} xem: ${d.name} còn ${d.quantity} suất (phiên bản dữ liệu v${d.version}).` },
    });
  };

  const confirm = async (who) => {
    if (p[who].seen === null) {
      set(who, { msg: { type: "warn", text: "Hãy bấm Xem món trước." } });
      return;
    }
    const qty = Number(p[who].qty);
    const res = mode === "unsafe"
      ? await post("/lost-update/order/unsafe", { seen_qty: p[who].seen.qty, qty })
      : await post("/lost-update/order/safe", { seen_version: p[who].seen.version, qty });
    if (res.ok) {
      set(who, { confirmed: p[who].confirmed + qty, msg: { type: "ok", text: `✔ Đặt món thành công cho khách ${who} (${qty} suất).` } });
    } else {
      set(who, { msg: { type: "err", text: `✘ Bị từ chối: ${errText(res.data)}` } });
    }
    refresh();
  };

  const total = p.A.confirmed + p.B.confirmed;
  const sold = food ? start - food.quantity : 0;
  const lost = food && total !== sold;
  const oversold = total > start;

  const renderPanel = (who) => (
    <div className="panel">
      <h3 className="panel-title">Khách {who}</h3>
      <label className="field">Số suất muốn đặt
        <input type="number" min="1" value={p[who].qty} onChange={(e) => set(who, { qty: e.target.value })} />
      </label>
      <div className="btn-row">
        <button onClick={() => see(who)}>Xem món</button>
        <button onClick={() => confirm(who)}>Đặt món</button>
      </div>
      {p[who].msg && <div className={"note " + p[who].msg.type}>{p[who].msg.text}</div>}
    </div>
  );

  return (
    <div>
      <h2>Module 1: Lost Update (mất dữ liệu cập nhật)</h2>
      <p>
        Món <b>{food?.name ?? "Gà đặc biệt"}</b> ({food ? money(food.price) : "…"}) chỉ còn <b>{start} suất</b> trong kho.
        Hai khách A và B cùng đặt. Bạn đóng vai cả hai: tự bấm các nút theo thứ tự.
      </p>

      {loadError && (
        <div className="note err big">
          ✘ Không tải được dữ liệu món ăn: {loadError}
          <br />Kiểm tra: backend đã chạy bản mới chưa, bảng <b>foods</b> đã được tạo chưa (xem Bước 1 và 3 hướng dẫn).
          <br /><button className="secondary" onClick={() => reset()}>Thử tải lại</button>
        </div>
      )}

      <div>
        <label>
          <input type="radio" checked={mode === "unsafe"} onChange={() => changeMode("unsafe")} />
          ❌ Không an toàn (đọc rồi ghi đè)
        </label>
        <label>
          <input type="radio" checked={mode === "safe"} onChange={() => changeMode("safe")} />
          ✅ An toàn (Optimistic Locking bằng version)
        </label>
      </div>

      <div className="guide">
        {mode === "unsafe" ? (
          <>
            <b>Cách gây lỗi:</b> tồn kho = 1, mỗi khách đặt 1 suất. Bấm <b>A Xem món → B Xem món → A Đặt món → B Đặt món</b>.
            Cả hai cùng thấy "còn 1 suất" nên cả hai đặt thành công: bán 2 suất trong khi kho chỉ có 1.<br />
            <b>Cách không lỗi:</b> bấm <b>A Xem → A Đặt → B Xem → B Đặt</b>. B xem sau khi A đặt xong nên thấy "còn 0 suất" và bị từ chối đúng.
          </>
        ) : (
          <>
            <b>Chế độ an toàn:</b> thử lại đúng kịch bản trên (A Xem → B Xem → A Đặt → B Đặt). Cả hai cùng đọc version v0.
            A đặt xong thì version tăng lên v1, B gửi version cũ v0 nên bị từ chối:
            "Món ăn đã hết hoặc dữ liệu đã thay đổi. Vui lòng tải lại". Bấm Xem món lần nữa sẽ thấy hết hàng.<br />
            Thử tồn kho = 2: B bị từ chối lần đầu (version cũ) nhưng bấm <b>Xem món</b> rồi <b>Đặt món</b> lại thì đặt được.
          </>
        )}
      </div>

      <div className="panel">
        <label className="field">Tồn kho ban đầu của Gà đặc biệt (suất)
          <input type="number" min="1" max="50" value={stock} onChange={(e) => setStock(e.target.value)} />
        </label>
        <button className="secondary" onClick={() => reset()}>Đặt lại tồn kho</button>
      </div>

      <div className="grid2">
        {renderPanel("A")}
        {renderPanel("B")}
      </div>

      <div className="panel" style={{ marginTop: 16 }}>
        <h3 className="panel-title">Thực tế trong database</h3>
        <div className="stats">
          <div><span>Tồn kho hiện tại</span><b>{food ? food.quantity : "…"}</b></div>
          <div><span>Kho đã giảm</span><b>{sold}</b></div>
          <div><span>Số suất đã báo thành công cho khách</span><b>{total}</b></div>
        </div>
        {total > 0 && (
          <div className={"note big " + (lost || oversold ? "err" : "ok")}>
            {lost || oversold
              ? `✘ LOST UPDATE: đã báo thành công ${total} suất nhưng kho chỉ giảm ${sold}${oversold ? `, trong khi tồn kho ban đầu chỉ có ${start}` : ""}. Món bị bán vượt số lượng!`
              : "✔ Số liệu khớp: số suất đã bán bằng đúng số kho đã giảm."}
          </div>
        )}
        <button className="secondary" onClick={() => reset()}>🔄 Làm lại từ đầu</button>
      </div>
    </div>
  );
}