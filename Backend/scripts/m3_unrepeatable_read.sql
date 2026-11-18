-- =====================================================================
-- MODULE 3 - UNREPEATABLE READ (đọc không lặp lại)
-- Giỏ hàng tổng 500.000đ. T1 (khách) đọc tổng tiền 2 lần trong cùng một giao dịch.
-- Giữa hai lần đọc, T2 (thu ngân) thêm phí dịch vụ 50.000đ và COMMIT. Khách thấy 500.000đ rồi 550.000đ.
-- =====================================================================

=== loi | Gây lỗi: READ COMMITTED (mặc định) | T1 đọc 2 lần ra 2 giá trị khác nhau vì T2 COMMIT ở giữa.
--- setup | SYS
UPDATE orders SET service_fee = 0, discount = 0 WHERE customer_name = 'CART-DEMO';
--- t1 | T1 | r1
BEGIN;
SELECT total FROM orders WHERE customer_name = 'CART-DEMO';        -- lần đọc 1: 500000
--- t2 | T2 | fee
BEGIN;
UPDATE orders SET service_fee = 50000 WHERE customer_name = 'CART-DEMO';
COMMIT;                                                            -- thay đổi đã COMMIT thật
--- t3 | T1 | r2
SELECT total FROM orders WHERE customer_name = 'CART-DEMO';        -- LỖI: lần đọc 2 (cùng giao dịch) ra 550000
COMMIT;
--- t4 | SYS | final
SELECT total FROM orders WHERE customer_name = 'CART-DEMO';
--- cleanup | SYS
UPDATE orders SET service_fee = 0, discount = 0 WHERE customer_name = 'CART-DEMO';

=== sua_rr | Sửa 1: REPEATABLE READ | T1 dùng snapshot cố định của lúc bắt đầu nên đọc lại vẫn 500000. T2 không bị chặn.
--- setup | SYS
UPDATE orders SET service_fee = 0, discount = 0 WHERE customer_name = 'CART-DEMO';
--- t1 | T1 | r1
BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ;                 -- SỬA: mức cô lập snapshot cố định
SELECT total FROM orders WHERE customer_name = 'CART-DEMO';        -- lần đọc 1: 500000
--- t2 | T2 | fee
BEGIN;
UPDATE orders SET service_fee = 50000 WHERE customer_name = 'CART-DEMO';
COMMIT;
--- t3 | T1 | r2
SELECT total FROM orders WHERE customer_name = 'CART-DEMO';        -- lần đọc 2: VẪN 500000
COMMIT;
--- t4 | SYS | final
SELECT total FROM orders WHERE customer_name = 'CART-DEMO';
--- cleanup | SYS
UPDATE orders SET service_fee = 0, discount = 0 WHERE customer_name = 'CART-DEMO';

=== sua_share | Sửa 2: khóa dòng FOR SHARE | T1 khóa dòng lúc đọc lần 1; T2 phải CHỜ đến khi T1 xong mới sửa được (cách của SQL Server).
--- setup | SYS
UPDATE orders SET service_fee = 0, discount = 0 WHERE customer_name = 'CART-DEMO';
--- t1 | T1 | r1
BEGIN;
SELECT total FROM orders WHERE customer_name = 'CART-DEMO' FOR SHARE;   -- SỬA: khóa dòng đến hết giao dịch
--- t2 | T2 | fee
BEGIN;
UPDATE orders SET service_fee = 50000 WHERE customer_name = 'CART-DEMO';   -- T2 bị CHỜ vì T1 đang khóa dòng
--- t3 | T1 | r2
SELECT total FROM orders WHERE customer_name = 'CART-DEMO';        -- lần đọc 2: VẪN 500000
--- t4 | T1 | t1_end
COMMIT;                                                            -- nhả khóa: T2 được chạy tiếp
--- t5 | T2 | t2_end
COMMIT;
--- t6 | SYS | final
SELECT total FROM orders WHERE customer_name = 'CART-DEMO';
--- cleanup | SYS
UPDATE orders SET service_fee = 0, discount = 0 WHERE customer_name = 'CART-DEMO';
