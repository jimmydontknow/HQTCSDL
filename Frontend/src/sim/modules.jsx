export const MODULES = {
  lost: {
    key: "lost", tab: "1. Lost Update", prefix: "/lost-update",
    title: "Module 1: Lost Update - mất dữ liệu cập nhật",
    story: "Món Gà đặc biệt còn 1 suất. T1 và T2 là hai khách cùng đặt món. Cả hai đọc 'còn 1 suất' rồi cùng ghi đè nên bán 2 suất nhưng kho chỉ giảm 1. Có 3 kịch bản sửa lỗi để so sánh.",
  },
  dirty: {
    key: "dirty", tab: "2. Dirty Read", prefix: "/dirty-read",
    title: "Module 2: Dirty Read - đọc dữ liệu rác",
    story: "Bò lúc lắc giá 100.000đ. T1 (Admin) đổi sang 50.000đ nhưng chưa COMMIT; T2 (khách) xem giá; rồi T1 ROLLBACK. PostgreSQL không bao giờ cho T2 thấy 50.000đ.",
    reference: {
      title: "Mẫu kinh điển trên SQL Server (dirty read xảy ra thật, KHÔNG chạy được trên PostgreSQL)",
      note: "Bản chất: T2 đọc được dữ liệu T1 đang sửa khi T1 chưa COMMIT. Sau đó T1 ROLLBACK nên số T2 đã đọc là dữ liệu 'ảo'.",
      rows: [
        { t: "t1", t1: "BEGIN TRANSACTION;\nUPDATE TaiKhoan SET SoDu = 500 WHERE ID = 1;\n-- (chưa COMMIT)", t2: "" },
        { t: "t2", t1: "", t2: "SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;\nBEGIN TRANSACTION;\nSELECT SoDu FROM TaiKhoan WHERE ID = 1;\n-- T2 đọc được 500 (dirty read)\nCOMMIT;" },
        { t: "t3", t1: "ROLLBACK;\n-- SoDu quay về 1000", t2: "-- T2 đã dùng số 500 sai lệch để xử lý nghiệp vụ" },
      ],
    },
  },
  unrep: {
    key: "unrep", tab: "3. Unrepeatable Read", prefix: "/unrepeatable-read",
    title: "Module 3: Unrepeatable Read - đọc không lặp lại",
    story: "Giỏ hàng 500.000đ. T1 (khách) đọc tổng tiền 2 lần trong cùng một giao dịch; giữa hai lần T2 (thu ngân) thêm phí dịch vụ 50.000đ và COMMIT.",
  },
  phantom: {
    key: "phantom", tab: "4. Phantom Read", prefix: "/phantom-read",
    title: "Module 4: Phantom Read - đọc dòng ma",
    story: "T1 (quản lý) xuất báo cáo doanh thu hôm nay 2 lần trong cùng một giao dịch; giữa hai lần T2 (thu ngân) tạo thêm một hóa đơn và COMMIT.",
  },
};
