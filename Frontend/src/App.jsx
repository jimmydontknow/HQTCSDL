import { useState } from "react";
import Booking from "./Booking";
import SimHost from "./sim/SimHost";
import { MODULES } from "./sim/modules";

const TABS = [
  { key: "booking", label: "🍽️ Đặt bàn" },
  ...Object.values(MODULES).map((m) => ({ key: m.key, label: m.tab })),
];

export default function App() {
  const [tab, setTab] = useState("booking");
  return (
    <>
      <div className="topbar">
        <h1>Hệ thống đặt bàn nhà hàng</h1>
        <p>Demo xử lý xung đột dữ liệu trong PostgreSQL · FastAPI · React</p>
        <div className="tabs">
          {TABS.map((t) => (
            <button key={t.key} className={"tab" + (tab === t.key ? " active" : "")} onClick={() => setTab(t.key)}>
              {t.label}
            </button>
          ))}
        </div>
      </div>

      <div className="page">
        {/* Trang Đặt bàn luôn tồn tại, chỉ ẩn đi: giữ nguyên mọi thứ đã nhập */}
        <div style={{ display: tab === "booking" ? "block" : "none" }}>
          <Booking active={tab === "booking"} />
        </div>
        {tab !== "booking" && <SimHost key={tab} cfg={MODULES[tab]} />}
      </div>
    </>
  );
}
