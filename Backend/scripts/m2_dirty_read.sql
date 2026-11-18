-- =====================================================================
-- MODULE 2 - DIRTY READ (đọc dữ liệu rác)
-- Món "Bò lúc lắc" giá 100.000đ. T1 (Admin) đổi sang giá Flash Sale 50.000đ nhưng CHƯA COMMIT.
-- T2 (khách) xem giá. Nếu T2 thấy 50.000đ rồi T1 ROLLBACK thì T2 đã đọc một giá "ma".
-- LƯU Ý: PostgreSQL KHÔNG có dirty read (READ UNCOMMITTED chạy như READ COMMITTED nhờ MVCC),
-- nên kết quả luôn là T2 thấy 100000. Đoạn T-SQL tham khảo cho SQL Server ở cuối file.
-- =====================================================================

=== sim_sqlserver | Gây lỗi (MÔ PHỎNG SQL Server): T2 đọc dữ liệu chưa COMMIT | Mô phỏng theo SQL Server: T2 dùng READ UNCOMMITTED nên đọc được giá chưa COMMIT của T1, rồi T1 ROLLBACK. Các câu T-SQL này KHÔNG chạy trên PostgreSQL.
--- t1 | T1
BEGIN TRANSACTION;
--> BEGIN TRANSACTION
UPDATE foods SET price = 50000 WHERE name = N'Bò lúc lắc';        -- LỖI: T1 sửa giá nhưng CHƯA COMMIT
--> (1 row affected)
--- t2 | T2 | t2_read
SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;                  -- LỖI: cho phép đọc dữ liệu chưa COMMIT
--> Commands completed successfully.
BEGIN TRANSACTION;
--> BEGIN TRANSACTION
SELECT price FROM foods WHERE name = N'Bò lúc lắc';                -- LỖI: đọc được 50000 (giá chưa COMMIT)
--> price = 50000
COMMIT;
--> COMMIT
--- t3 | T1
ROLLBACK;                                                          -- T1 hủy: giá quay về 100000
--> ROLLBACK (giá thật vẫn là 100000)
--- t4 | T2
-- T2 đã dùng số 50000 (không tồn tại) để tính tiền cho khách: dữ liệu ảo.

=== ru | Chạy thật PostgreSQL, sửa lỗi: T2 dùng READ UNCOMMITTED, T1 ROLLBACK | T2 yêu cầu mức thấp nhất nhưng PostgreSQL vẫn không cho đọc dữ liệu chưa COMMIT.
--- setup | SYS
UPDATE foods SET price = 100000 WHERE name = 'Bò lúc lắc';
--- t1 | T1
BEGIN;
UPDATE foods SET price = 50000 WHERE name = 'Bò lúc lắc';          -- chưa COMMIT
--- t2 | T2 | t2_read
BEGIN TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;                -- (SQL Server: SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED)
SHOW transaction_isolation;
SELECT price FROM foods WHERE name = 'Bò lúc lắc';                 -- SQL Server sẽ đọc được 50000; PostgreSQL vẫn đọc 100000
COMMIT;
--- t3 | T1
ROLLBACK;                                                          -- T1 hủy, giá quay về 100000
--- t4 | SYS | final
SELECT price FROM foods WHERE name = 'Bò lúc lắc';
--- cleanup | SYS
UPDATE foods SET price = 100000 WHERE name = 'Bò lúc lắc';

=== rc | Chạy thật PostgreSQL, sửa lỗi: T2 dùng READ COMMITTED (mặc định) | Kết quả giống kịch bản trên: PostgreSQL không bao giờ cho dirty read.
--- setup | SYS
UPDATE foods SET price = 100000 WHERE name = 'Bò lúc lắc';
--- t1 | T1
BEGIN;
UPDATE foods SET price = 50000 WHERE name = 'Bò lúc lắc';          -- chưa COMMIT
--- t2 | T2 | t2_read
BEGIN TRANSACTION ISOLATION LEVEL READ COMMITTED;
SHOW transaction_isolation;
SELECT price FROM foods WHERE name = 'Bò lúc lắc';
COMMIT;
--- t3 | T1
ROLLBACK;
--- t4 | SYS | final
SELECT price FROM foods WHERE name = 'Bò lúc lắc';
--- cleanup | SYS
UPDATE foods SET price = 100000 WHERE name = 'Bò lúc lắc';

=== commit | Chạy thật PostgreSQL, đối chiếu: T1 COMMIT (đối chiếu) | T2 chỉ thấy giá mới SAU KHI T1 COMMIT. Đây là hành vi đúng của PostgreSQL.
--- setup | SYS
UPDATE foods SET price = 100000 WHERE name = 'Bò lúc lắc';
--- t1 | T1
BEGIN;
UPDATE foods SET price = 50000 WHERE name = 'Bò lúc lắc';          -- chưa COMMIT
--- t2 | T2 | t2_read
BEGIN TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
SELECT price FROM foods WHERE name = 'Bò lúc lắc';                 -- vẫn 100000
COMMIT;
--- t3 | T1
COMMIT;                                                            -- giá mới 50000 được lưu thật
--- t4 | T2 | t4_read
BEGIN TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
SELECT price FROM foods WHERE name = 'Bò lúc lắc';                 -- bây giờ mới thấy 50000
COMMIT;
--- cleanup | SYS
UPDATE foods SET price = 100000 WHERE name = 'Bò lúc lắc';

-- =====================================================================
-- THAM KHẢO (SQL Server, KHÔNG chạy trên PostgreSQL) - dirty read xảy ra thật:
--   [T1] BEGIN TRAN; UPDATE foods SET price = 50000 WHERE name = N'Bò lúc lắc';
--   [T2] SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED; BEGIN TRAN;
--        SELECT price FROM foods WHERE name = N'Bò lúc lắc';   -- đọc được 50000 (hoặc ... WITH (NOLOCK))
--        COMMIT;
--   [T1] ROLLBACK;   -- giá về 100000, T2 đã dùng số 50000 "ảo" để xử lý nghiệp vụ
-- =====================================================================
