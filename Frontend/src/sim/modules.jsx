import { useEffect, useState } from "react";
import BookingPicker from "../BookingPicker";
import { get, money } from "../shared";

const Stat = ({ label, value }) => <div><span>{label}</span><b>{value}</b></div>;
const Field = ({ label, children }) => <label className="field">{label}{children}</label>;

// Ô nhập số dùng chung (thời gian tính bằng giây)
const Num = ({ label, name, params, set, disabled, min = 0, max = 10, step = 0.5, hint }) => (
  <Field label={label}>
    <input type="number" min={min} max={max} step={step} value={params[name] ?? ""} disabled={disabled}
           onChange={(e) => set({ [name]: e.target.value })} />
    {hint && <small style={{ color: "var(--muted)" }}>{hint}</small>}
  </Field>
);

const Cmd = ({ children }) => <code style={{ fontWeight: 700 }}>{children}</code>;

// Cách thao tác chung trong pgAdmin
const HowToggle = ({ children }) => (
  <ol style={{ margin: "0 0 8px 18px", padding: 0 }}>
    <li>Trong pgAdmin, kéo xuống chỗ <Cmd>{">>> SỬA TẠI ĐÂY <<<"}</Cmd>.</li>
    {children}
    <li>Bấm <b>F5</b>, quay lại đây bấm <b>▶ Chạy lại demo</b>.</li>
  </ol>
);

// ---------- Module 1A, 1B ----------
const CustomerInput = ({ params, set, disabled }) => (
  <>
    <Field label="Số suất muốn đặt">
      <input type="number" min="1" value={params.qty ?? 1} disabled={disabled} onChange={(e) => set({ qty: e.target.value })} />
    </Field>
    <Num label="Thời gian xử lý thanh toán (giây)" name="process" min={0} max={6}
         params={params} set={set} disabled={disabled}
         hint="Khoảng giữa lúc đọc tồn kho và lúc ghi lại" />
    <Num label="Bấm Đặt món sau (giây)" name="start_after" min={0} max={6}
         params={params} set={set} disabled={disabled}
         hint="0 = bấm cùng lúc với bên kia" />
  </>
);

const lostModule = ({ key, tab, prefix, food, title, story, file, fixStep, fixHow }) => ({
  key, tab, prefix, title, story, file, fixStep, fixHow,
  roles: { A: "Khách A", B: "Khách B" },
  defaults: { A: { qty: 1, process: 1.5, start_after: 0 }, B: { qty: 1, process: 1.5, start_after: 0 } },
  reset: {
    defaults: { stock: 1 },
    Inputs: ({ value, set }) => (
      <Field label={`Tồn kho ban đầu của ${food} (suất). Bấm "Đặt lại dữ liệu demo" để áp dụng`}>
        <input type="number" min="1" max="50" value={value.stock} onChange={(e) => set({ stock: e.target.value })} />
      </Field>
    ),
  },
  Inputs: { A: CustomerInput, B: CustomerInput },
  Data: ({ data }) => data ? (
    <div className="stats">
      <Stat label="Món" value={data.name} />
      <Stat label="Tồn kho hiện tại" value={data.quantity} />
      <Stat label="Phiên bản dữ liệu (version)" value={"v" + data.version} />
    </div>
  ) : null,
});

// ---------- Module 2 ----------
const TablePick = ({ params, set, disabled }) => {
  const [tables, setTables] = useState([]);
  useEffect(() => { get("/tables").then((r) => { if (r.ok) setTables(r.data); }); }, []);
  return (
    <Field label="Khách muốn xem bàn nào?">
      <select value={params.table_id ?? ""} disabled={disabled} onChange={(e) => set({ table_id: e.target.value })}>
        <option value="">Giống bàn nhân viên đang đặt</option>
        {tables.map((t) => <option key={t.id} value={t.id}>{t.name} - {t.capacity} người</option>)}
      </select>
    </Field>
  );
};

export const MODULES = {
  lost1: lostModule({
    key: "lost1", tab: "1A. Lost Update (khóa lạc quan)", prefix: "/lost-update-1", food: "Gà đặc biệt",
    title: "Module 1A: Lost Update - sửa bằng khóa lạc quan (version)",
    story: "Món Gà đặc biệt chỉ còn 1 suất. Hai khách A và B đặt cùng lúc. Cả hai đều đọc 'còn 1 suất' rồi cùng ghi đè kết quả của nhau, nên nhà hàng bán 2 suất trong khi chỉ có 1.",
    file: "sql/m1a_lost_update_lac_quan.sql",
    fixStep: <>Để hết lỗi: trong file SQL, <b>tắt dòng [LỖI]</b> và <b>bật các dòng [SỬA]</b> bằng <b>Ctrl+/</b>, rồi <b>F5</b> (xem khung "Cách sửa" bên dưới).</>,
    fixHow: (
      <HowToggle>
        <li>Bôi đen <b>1 dòng có [LỖI]</b> ở cuối → nhấn <b>Ctrl+/</b> (tắt dòng đó).</li>
        <li>Bôi đen <b>các dòng có [SỬA]</b> ở cuối → nhấn <b>Ctrl+/</b> (bật các dòng đó).</li>
      </HowToggle>
    ),
  }),
  lost2: lostModule({
    key: "lost2", tab: "1B. Lost Update (khóa bi quan)", prefix: "/lost-update-2", food: "Lẩu thái",
    title: "Module 1B: Lost Update - sửa bằng khóa bi quan hoặc UPDATE nguyên tử",
    story: "Kịch bản giống 1A nhưng với món Lẩu thái. Hai cách sửa: FOR UPDATE (khóa dòng ngay lúc đọc, bên đến sau phải chờ) hoặc UPDATE nguyên tử (trừ kho và kiểm tra trong một câu lệnh).",
    file: "sql/m1b_lost_update_bi_quan.sql",
    fixStep: <>Để hết lỗi: trong file SQL, chọn <b>CÁCH 1</b> hoặc <b>CÁCH 2</b> (tắt dòng [LỖI], bật dòng [SỬA] bằng <b>Ctrl+/</b>), rồi <b>F5</b>.</>,
    fixHow: (
      <HowToggle>
        <li><b>CÁCH 1 (FOR UPDATE):</b> dòng <Cmd>[LỖI-1]</Cmd> → Ctrl+/ (tắt) và dòng <Cmd>[SỬA-1]</Cmd> → Ctrl+/ (bật). Bên đến sau sẽ <b>chờ</b> (xem bảng thời gian) rồi thấy hết món.</li>
        <li><b>CÁCH 2 (UPDATE nguyên tử):</b> dòng <Cmd>[LỖI-2]</Cmd> → Ctrl+/ (tắt) và các dòng <Cmd>[SỬA-2]</Cmd> → Ctrl+/ (bật). Phép trừ và kiểm tra nằm trong một câu UPDATE.</li>
        <li>Chỉ làm <b>một trong hai</b> cách. Muốn thử cách kia thì trả cách cũ về như ban đầu.</li>
      </HowToggle>
    ),
  }),

  dirty: {
    key: "dirty", tab: "2. Dirty Read", prefix: "/dirty-read",
    title: "Module 2: Dirty Read - đọc dữ liệu chưa commit",
    story: "Nhân viên (A) nhập một đơn đặt bàn nhưng chưa lưu rồi hủy. Cùng lúc, khách (B) xem khung giờ còn bao nhiêu chỗ. Nếu khách thấy số liệu của đơn chưa lưu thì đó là dirty read. PostgreSQL không bao giờ cho dirty read nên kết quả luôn là KHÔNG lỗi.",
    file: "sql/m2_dirty_read.sql",
    fixStep: <>Module này <b>không có lỗi để sửa</b> vì PostgreSQL chặn dirty read. Hãy đổi mức cô lập của khách bên dưới và chạy lại để thấy kết quả không đổi.</>,
    fixHow: (
      <p style={{ margin: "0 0 8px" }}>
        Không có chỗ nào cần sửa: PostgreSQL xử lý <b>READ UNCOMMITTED</b> như <b>READ COMMITTED</b> (nhờ MVCC) nên khách luôn thấy dữ liệu đã commit.
        Cuối file SQL có kịch bản chạy tay trong 2 tab pgAdmin và đoạn T-SQL tham khảo cho SQL Server, nơi dirty read xảy ra thật.
        Muốn thử "chưa kịp xem": đặt <b>Khách mở trang xem sau</b> = 6 giây (sau khi nhân viên đã hủy).
      </p>
    ),
    modes: [
      { key: "read_uncommitted", label: "Khách dùng READ UNCOMMITTED" },
      { key: "read_committed", label: "Khách dùng READ COMMITTED" },
    ],
    roles: { A: "Nhân viên nhập đơn", B: "Khách xem khung giờ" },
    defaults: { A: { hold: 3.5 }, B: { after: 1.5, table_id: "" } },
    Inputs: {
      A: ({ params, set, disabled }) => (
        <>
          <BookingPicker onChange={set} disabled={disabled} />
          <Num label="Nhân viên giữ chưa COMMIT trong (giây) rồi mới hủy" name="hold" min={1} max={8}
               params={params} set={set} disabled={disabled} />
        </>
      ),
      B: ({ params, set, disabled }) => (
        <>
          <TablePick params={params} set={set} disabled={disabled} />
          <Num label="Khách mở trang xem sau (giây)" name="after" min={0.3} max={10}
               params={params} set={set} disabled={disabled}
               hint="Nhỏ hơn thời gian nhân viên giữ thì khách xem đúng lúc chưa COMMIT" />
        </>
      ),
    },
    Data: ({ data }) => data ? (
      <div className="stats"><Stat label="Số đơn đặt bàn đang có hiệu lực (không đổi sau khi hủy)" value={data.confirmed} /></div>
    ) : null,
  },

  unrep: {
    key: "unrep", tab: "3. Unrepeatable Read", prefix: "/unrepeatable-read",
    title: "Module 3: Unrepeatable Read - đọc cùng một dòng 2 lần ra 2 giá trị",
    story: "Khách (A) mở giỏ hàng tổng 500.000đ, xem một lúc rồi mới xác nhận (đọc 2 lần trong cùng một giao dịch). Giữa hai lần đọc, thu ngân (B) thêm phí dịch vụ 50.000đ. Khách thấy 500.000đ rồi 550.000đ.",
    file: "sql/m3_unrepeatable_read.sql",
    fixStep: <>Để hết lỗi: trong file SQL, <b>tắt dòng [LỖI]</b> và <b>bật dòng [SỬA]</b> bằng <b>Ctrl+/</b>, rồi <b>F5</b>.</>,
    fixHow: (
      <HowToggle>
        <li>Bôi đen dòng <Cmd>[LỖI]</Cmd> (câu SELECT đọc lần 1) → <b>Ctrl+/</b> (tắt).</li>
        <li>Bôi đen dòng <Cmd>[SỬA]</Cmd> (cùng câu SELECT nhưng thêm <Cmd>FOR SHARE</Cmd>) → <b>Ctrl+/</b> (bật). Dòng bị khóa đến hết giao dịch nên thu ngân phải chờ khách xong.</li>
      </HowToggle>
    ),
    roles: { A: "Khách xem giỏ hàng 2 lần", B: "Thu ngân sửa hóa đơn" },
    defaults: { A: { view_secs: 3 }, B: { kind: "fee", amount: 50000, after: 1.5 } },
    Inputs: {
      A: ({ params, set, disabled }) => (
        <Num label="Khách xem giỏ hàng trong (giây) rồi mới xác nhận" name="view_secs" min={1} max={8}
             params={params} set={set} disabled={disabled}
             hint="Lần đọc 1 lúc mở giỏ, lần đọc 2 sau khoảng thời gian này" />
      ),
      B: ({ params, set, disabled }) => (
        <>
          <Field label="Loại điều chỉnh">
            <select value={params.kind} disabled={disabled} onChange={(e) => set({ kind: e.target.value })}>
              <option value="fee">Phí dịch vụ (cộng thêm)</option>
              <option value="discount">Mã giảm giá (trừ đi)</option>
            </select>
          </Field>
          <Field label="Số tiền (đồng)">
            <input type="number" min="0" step="1000" value={params.amount} disabled={disabled}
                   onChange={(e) => set({ amount: e.target.value })} />
          </Field>
          <Num label="Thu ngân sửa hóa đơn sau (giây)" name="after" min={0} max={10}
               params={params} set={set} disabled={disabled}
               hint="Nhỏ hơn thời gian khách xem thì thay đổi rơi vào giữa hai lần đọc" />
        </>
      ),
    },
    Data: ({ data }) => data ? (
      <div className="stats">
        <Stat label="Tạm tính" value={money(data.subtotal)} />
        <Stat label="Phí dịch vụ" value={money(data.service_fee)} />
        <Stat label="Giảm giá" value={money(data.discount)} />
        <Stat label="Tổng thực tế" value={money(data.total)} />
      </div>
    ) : null,
  },

  phantom: {
    key: "phantom", tab: "4. Phantom Read", prefix: "/phantom-read",
    title: "Module 4: Phantom Read - xuất hiện thêm dòng 'ma'",
    story: "Quản lý (A) xuất báo cáo doanh thu cuối ngày 2 lần trong cùng một giao dịch. Giữa hai lần, thu ngân (B) tạo thêm một hóa đơn mới. Báo cáo lần 2 có thêm một hóa đơn mà lần 1 không có.",
    file: "sql/m4_phantom_read.sql",
    fixStep: <>Để hết lỗi: trong file SQL, <b>bật dòng [SỬA]</b> bằng <b>Ctrl+/</b>, rồi <b>F5</b>.</>,
    fixHow: (
      <HowToggle>
        <li>Bôi đen dòng <Cmd>[SỬA]</Cmd> (<Cmd>LOCK TABLE orders IN SHARE MODE</Cmd>) → <b>Ctrl+/</b> (bật). Không có dòng [LỖI] nào cần tắt.</li>
        <li>Bảng bị khóa đến hết giao dịch của quản lý, nên thu ngân phải chờ rồi mới tạo được hóa đơn.</li>
      </HowToggle>
    ),
    roles: { A: "Quản lý xuất báo cáo 2 lần", B: "Thu ngân tạo hóa đơn" },
    defaults: { A: { min_total: 0, view_secs: 3 }, B: { total: 200000, after: 1.5 } },
    Inputs: {
      A: ({ params, set, disabled }) => (
        <>
          <Field label="Chỉ tính hóa đơn có tổng từ (đồng)">
            <input type="number" min="0" step="10000" value={params.min_total} disabled={disabled}
                   onChange={(e) => set({ min_total: e.target.value })} />
          </Field>
          <Num label="Quản lý xem báo cáo trong (giây) rồi mới xuất lại" name="view_secs" min={1} max={8}
               params={params} set={set} disabled={disabled} />
        </>
      ),
      B: ({ params, set, disabled }) => (
        <>
          <Field label="Tổng tiền hóa đơn mới (đồng)">
            <input type="number" min="1000" step="10000" value={params.total} disabled={disabled}
                   onChange={(e) => set({ total: e.target.value })} />
          </Field>
          <Num label="Thu ngân tạo hóa đơn sau (giây)" name="after" min={0} max={10}
               params={params} set={set} disabled={disabled}
               hint="Nhỏ hơn thời gian quản lý xem thì hóa đơn rơi vào giữa hai lần xuất" />
        </>
      ),
    },
    Data: ({ data }) => data ? (
      <div className="chips">
        {data.orders.map((o) => (
          <span key={o.id} className="chip">#{o.id} {o.customer_name === "DEMO-PHANTOM" ? "(demo) " : ""}{money(o.total)}</span>
        ))}
      </div>
    ) : null,
  },
};
