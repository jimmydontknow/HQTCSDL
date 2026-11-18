-- =====================================================================
-- MODULE 4 - PHANTOM READ (đọc dòng ma)
-- T1 (quản lý) xuất báo cáo doanh thu hôm nay 2 lần trong cùng một giao dịch (5 hóa đơn, 1.300.000đ).
-- Giữa hai lần, T2 (thu ngân) tạo thêm hóa đơn 200.000đ và COMMIT. Báo cáo lần 2 có 6 hóa đơn.
-- =====================================================================

=== loi | Gây lỗi: READ COMMITTED (mặc định) | Truy vấn lần 2 thấy thêm một dòng "ma" mà lần 1 không có.
--- setup | SYS
DELETE FROM orders WHERE customer_name = 'DEMO-PHANTOM';
UPDATE orders SET order_date = CURRENT_DATE WHERE customer_name = 'SEED';
--- t1 | T1 | c1
BEGIN;
SELECT count(*) AS so_hoa_don, sum(total) AS doanh_thu
  FROM orders WHERE order_date = CURRENT_DATE AND status = 'paid';   -- báo cáo lần 1: 5 hóa đơn
--- t2 | T2 | ins
BEGIN;
INSERT INTO orders (customer_name, subtotal, status) VALUES ('DEMO-PHANTOM', 200000, 'paid');
COMMIT;                                                            -- hóa đơn mới đã COMMIT thật
--- t3 | T1 | c2
SELECT count(*) AS so_hoa_don, sum(total) AS doanh_thu
  FROM orders WHERE order_date = CURRENT_DATE AND status = 'paid';   -- LỖI: báo cáo lần 2 ra 6 hóa đơn
COMMIT;
--- cleanup | SYS
DELETE FROM orders WHERE customer_name = 'DEMO-PHANTOM';

=== sua_rr | Sửa 1: REPEATABLE READ | Snapshot cố định nên báo cáo lần 2 vẫn 5 hóa đơn. (PostgreSQL chặn phantom ngay ở mức này.)
--- setup | SYS
DELETE FROM orders WHERE customer_name = 'DEMO-PHANTOM';
UPDATE orders SET order_date = CURRENT_DATE WHERE customer_name = 'SEED';
--- t1 | T1 | c1
BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ;                 -- SỬA: snapshot cố định cho cả giao dịch
SELECT count(*) AS so_hoa_don, sum(total) AS doanh_thu
  FROM orders WHERE order_date = CURRENT_DATE AND status = 'paid';
--- t2 | T2 | ins
BEGIN;
INSERT INTO orders (customer_name, subtotal, status) VALUES ('DEMO-PHANTOM', 200000, 'paid');
COMMIT;
--- t3 | T1 | c2
SELECT count(*) AS so_hoa_don, sum(total) AS doanh_thu
  FROM orders WHERE order_date = CURRENT_DATE AND status = 'paid';   -- VẪN 5 hóa đơn
COMMIT;
--- cleanup | SYS
DELETE FROM orders WHERE customer_name = 'DEMO-PHANTOM';

=== sua_lock | Sửa 2: khóa bảng LOCK TABLE ... SHARE MODE | T1 khóa cả bảng; T2 phải CHỜ đến khi T1 xong mới INSERT được.
--- setup | SYS
DELETE FROM orders WHERE customer_name = 'DEMO-PHANTOM';
UPDATE orders SET order_date = CURRENT_DATE WHERE customer_name = 'SEED';
--- t1 | T1 | c1
BEGIN;
LOCK TABLE orders IN SHARE MODE;                                   -- SỬA: chặn INSERT/UPDATE/DELETE của người khác
SELECT count(*) AS so_hoa_don, sum(total) AS doanh_thu
  FROM orders WHERE order_date = CURRENT_DATE AND status = 'paid';
--- t2 | T2 | ins
BEGIN;
INSERT INTO orders (customer_name, subtotal, status) VALUES ('DEMO-PHANTOM', 200000, 'paid');   -- T2 bị CHỜ
--- t3 | T1 | c2
SELECT count(*) AS so_hoa_don, sum(total) AS doanh_thu
  FROM orders WHERE order_date = CURRENT_DATE AND status = 'paid';   -- VẪN 5 hóa đơn
--- t4 | T1 | t1_end
COMMIT;                                                            -- nhả khóa: T2 được chạy tiếp
--- t5 | T2 | t2_end
COMMIT;
--- cleanup | SYS
DELETE FROM orders WHERE customer_name = 'DEMO-PHANTOM';
