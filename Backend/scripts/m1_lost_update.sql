-- =====================================================================
-- MODULE 1 - LOST UPDATE (mất dữ liệu cập nhật)
-- Món "Gà đặc biệt" còn 1 suất. T1 và T2 là hai khách cùng đặt món.
-- Mỗi kịch bản là một bảng thời gian t1, t2, t3...: mỗi bước là câu SQL thật của T1 hoặc T2.
-- Định dạng file:  "=== khóa | tiêu đề | ghi chú" mở kịch bản,  "--- thời điểm | T1/T2/SYS | id" mở một bước.
-- Chạy tay trong pgAdmin: mở 2 tab Query Tool, chép khối T1 vào tab 1, khối T2 vào tab 2, chạy đúng thứ tự thời gian.
-- =====================================================================

=== loi | Gây lỗi: đọc rồi ghi đè | Cả hai cùng đọc "còn 1 suất" rồi cùng ghi đè kết quả của nhau: bán 2 suất nhưng kho chỉ giảm 1.
--- setup | SYS
UPDATE foods SET quantity = 1, version = 0 WHERE name = 'Gà đặc biệt';
--- t1 | T1 | a_read
BEGIN;
SELECT quantity FROM foods WHERE name = 'Gà đặc biệt';          -- T1 thấy còn 1 suất
--- t2 | T2 | b_read
BEGIN;
SELECT quantity FROM foods WHERE name = 'Gà đặc biệt';          -- T2 cũng thấy còn 1 suất
--- t3 | T1 | a_write
-- ứng dụng của T1 tính: 1 - 1 = 0
UPDATE foods SET quantity = 0 WHERE name = 'Gà đặc biệt';       -- LỖI: ghi đè bằng số CŨ đã đọc
COMMIT;
--- t4 | T2 | b_write
-- ứng dụng của T2 cũng tính trên số cũ: 1 - 1 = 0
UPDATE foods SET quantity = 0 WHERE name = 'Gà đặc biệt';       -- LỖI: ghi đè kết quả của T1
COMMIT;
--- t5 | SYS | final
SELECT quantity FROM foods WHERE name = 'Gà đặc biệt';
--- cleanup | SYS
UPDATE foods SET quantity = 1, version = 0 WHERE name = 'Gà đặc biệt';

=== sua_version | Sửa 1: khóa lạc quan (cột version) | Chỉ ghi nếu version vẫn là version đã đọc. Bên ghi sau thấy 0 dòng bị ảnh hưởng nên bị từ chối.
--- setup | SYS
UPDATE foods SET quantity = 1, version = 0 WHERE name = 'Gà đặc biệt';
--- t1 | T1 | a_read
BEGIN;
SELECT quantity, version FROM foods WHERE name = 'Gà đặc biệt';   -- SỬA: đọc thêm cột version (0)
--- t2 | T2 | b_read
BEGIN;
SELECT quantity, version FROM foods WHERE name = 'Gà đặc biệt';   -- T2 cũng thấy version 0
--- t3 | T1 | a_write
UPDATE foods SET quantity = 0, version = version + 1
 WHERE name = 'Gà đặc biệt' AND version = 0;                       -- SỬA: chỉ ghi nếu version vẫn là 0
COMMIT;
--- t4 | T2 | b_write
UPDATE foods SET quantity = 0, version = version + 1
 WHERE name = 'Gà đặc biệt' AND version = 0;                       -- SỬA: version đã là 1 nên 0 dòng khớp
ROLLBACK;                                                          -- ứng dụng thấy 0 dòng => từ chối đặt món
--- t5 | SYS | final
SELECT quantity FROM foods WHERE name = 'Gà đặc biệt';
--- cleanup | SYS
UPDATE foods SET quantity = 1, version = 0 WHERE name = 'Gà đặc biệt';

=== sua_for_update | Sửa 2: khóa bi quan (FOR UPDATE) | Khóa dòng ngay lúc đọc. T2 phải chờ T1 COMMIT rồi mới đọc được, và đọc ra số đã cập nhật.
--- setup | SYS
UPDATE foods SET quantity = 1, version = 0 WHERE name = 'Gà đặc biệt';
--- t1 | T1 | a_read
BEGIN;
SELECT quantity FROM foods WHERE name = 'Gà đặc biệt' FOR UPDATE;  -- SỬA: khóa dòng khi đọc
--- t2 | T2 | b_read
BEGIN;
SELECT quantity FROM foods WHERE name = 'Gà đặc biệt' FOR UPDATE;  -- SỬA: T2 bị CHỜ vì T1 đang giữ khóa
--- t3 | T1 | a_write
UPDATE foods SET quantity = 0 WHERE name = 'Gà đặc biệt';
--- t4 | T1 | a_commit
COMMIT;                                                            -- nhả khóa: T2 được chạy tiếp và đọc ra 0
--- t5 | T2 | b_end
ROLLBACK;                                                          -- T2 thấy hết món nên không ghi gì
--- t6 | SYS | final
SELECT quantity FROM foods WHERE name = 'Gà đặc biệt';
--- cleanup | SYS
UPDATE foods SET quantity = 1, version = 0 WHERE name = 'Gà đặc biệt';

=== sua_atomic | Sửa 3: UPDATE nguyên tử | Trừ kho và kiểm tra đủ hàng trong MỘT câu UPDATE, tính trên số mới nhất trong database.
--- setup | SYS
UPDATE foods SET quantity = 1, version = 0 WHERE name = 'Gà đặc biệt';
--- t1 | T1 | a_read
BEGIN;
SELECT quantity FROM foods WHERE name = 'Gà đặc biệt';            -- T1 thấy còn 1 suất
--- t2 | T2 | b_read
BEGIN;
SELECT quantity FROM foods WHERE name = 'Gà đặc biệt';            -- T2 cũng thấy còn 1 suất
--- t3 | T1 | a_write
UPDATE foods SET quantity = quantity - 1
 WHERE name = 'Gà đặc biệt' AND quantity >= 1;                      -- SỬA: trừ ngay trong database + kiểm tra đủ hàng
--- t4 | T2 | b_write
UPDATE foods SET quantity = quantity - 1
 WHERE name = 'Gà đặc biệt' AND quantity >= 1;                      -- SỬA: T2 phải CHỜ T1 COMMIT
--- t5 | T1 | a_commit
COMMIT;                                                            -- T2 chạy lại điều kiện: quantity đã là 0 => 0 dòng
--- t6 | T2 | b_end
ROLLBACK;                                                          -- 0 dòng => ứng dụng từ chối đặt món
--- t7 | SYS | final
SELECT quantity FROM foods WHERE name = 'Gà đặc biệt';
--- cleanup | SYS
UPDATE foods SET quantity = 1, version = 0 WHERE name = 'Gà đặc biệt';
