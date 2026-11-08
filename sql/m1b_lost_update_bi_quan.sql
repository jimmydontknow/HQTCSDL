-- =====================================================================
-- MODULE 1B - LOST UPDATE (cách khắc phục: KHÓA BI QUAN hoặc UPDATE NGUYÊN TỬ)
--
-- CÁCH DÙNG (chỉ cần đúng 1 file này)
--   1) Bấm F5 để cài function. Mặc định function đang bị LỖI.
--   2) Vào web, tab "1B", bấm  ▶ Chạy demo   ->  thấy LOST UPDATE.
--   3) ĐỂ HẾT LỖI, chọn MỘT trong hai cách (kéo xuống chỗ  >>> SỬA TẠI ĐÂY <<<):
--        CÁCH 1 - KHÓA BI QUAN (FOR UPDATE):
--            bôi đen dòng [LỖI-1] -> Ctrl+/ (tắt)   và   dòng [SỬA-1] -> Ctrl+/ (bật)
--        CÁCH 2 - UPDATE NGUYÊN TỬ:
--            bôi đen dòng [LỖI-2] -> Ctrl+/ (tắt)   và   các dòng [SỬA-2] -> Ctrl+/ (bật)
--      sau đó bấm F5.
--   4) Quay lại web, bấm  ▶ Chạy lại demo  ->  hết lỗi.
--   (Muốn đổi cách khác: trả cách cũ về như ban đầu rồi làm cách mới.)
-- =====================================================================

-- ---- Chuẩn bị dữ liệu (chạy nhiều lần vẫn an toàn) ----
CREATE TABLE IF NOT EXISTS foods (
    id SERIAL PRIMARY KEY, name VARCHAR(100) NOT NULL,
    price INT NOT NULL CHECK (price >= 0), quantity INT NOT NULL CHECK (quantity >= 0),
    version INT NOT NULL DEFAULT 0
);
INSERT INTO foods (name, price, quantity)
SELECT 'Lẩu thái', 250000, 10 WHERE NOT EXISTS (SELECT 1 FROM foods WHERE name = 'Lẩu thái');

CREATE OR REPLACE FUNCTION demo_log(p_kind text, p_msg text) RETURNS void LANGUAGE plpgsql AS $$
BEGIN
  RAISE NOTICE '%|%|%', (extract(epoch from clock_timestamp()))::double precision, p_kind, p_msg;
END $$;

-- ---- Function đặt món ----
CREATE OR REPLACE FUNCTION sp_lu2_order(
    p_who text, p_qty int, p_process double precision, p_wait double precision)
RETURNS jsonb LANGUAGE plpgsql AS $$
DECLARE
    v_seen int;
BEGIN
    IF p_wait > 0 THEN PERFORM pg_sleep(p_wait); END IF;

    -- (1) ĐỌC tồn kho
    -- >>> SỬA TẠI ĐÂY (CÁCH 1) <<<
    SELECT quantity INTO v_seen FROM foods WHERE name = 'Lẩu thái';                                      -- [LỖI-1] đọc mà không khóa dòng
    -- SELECT quantity INTO v_seen FROM foods WHERE name = 'Lẩu thái' FOR UPDATE;                         -- [SỬA-1] khóa dòng, bên kia phải chờ
    PERFORM demo_log('info', format('Đọc: còn %s suất', v_seen));

    PERFORM pg_sleep(p_process);       -- mô phỏng thời gian xử lý thanh toán

    IF v_seen < p_qty THEN
        PERFORM demo_log('warn', format('Hết món (chỉ còn %s) → từ chối', v_seen));
        RETURN jsonb_build_object('ok', false, 'seen', v_seen, 'qty', p_qty);
    END IF;

    -- (2) GHI tồn kho mới
    -- >>> SỬA TẠI ĐÂY (CÁCH 2) <<<
    UPDATE foods SET quantity = v_seen - p_qty WHERE name = 'Lẩu thái';                                  -- [LỖI-2] ghi đè bằng số CŨ đã đọc
    -- UPDATE foods SET quantity = quantity - p_qty                                                       -- [SỬA-2] trừ ngay trong database
    --  WHERE name = 'Lẩu thái' AND quantity >= p_qty;                                                    -- [SỬA-2] kiểm tra đủ hàng trong cùng câu lệnh
    -- IF NOT FOUND THEN                                                                                  -- [SỬA-2]
    --     PERFORM demo_log('warn', 'Không còn đủ hàng (0 dòng khớp) → từ chối');                         -- [SỬA-2]
    --     RETURN jsonb_build_object('ok', false, 'seen', v_seen, 'qty', p_qty);                          -- [SỬA-2]
    -- END IF;                                                                                            -- [SỬA-2]

    PERFORM demo_log('ok', 'Ghi xong → đặt món thành công');
    RETURN jsonb_build_object('ok', true, 'seen', v_seen, 'qty', p_qty);
END $$;
