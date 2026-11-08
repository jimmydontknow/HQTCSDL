-- =====================================================================
-- MODULE 1A - LOST UPDATE (cách khắc phục: KHÓA LẠC QUAN bằng cột version)
--
-- CÁCH DÙNG (chỉ cần đúng 1 file này)
--   1) Bấm F5 để cài function. Mặc định function đang bị LỖI.
--   2) Vào web, tab "1A", bấm  ▶ Chạy demo   ->  thấy LOST UPDATE.
--   3) ĐỂ HẾT LỖI: kéo xuống chỗ  >>> SỬA TẠI ĐÂY <<<  rồi
--        a) bôi đen dòng có [LỖI] ở cuối  -> nhấn Ctrl+/   (tắt dòng đó)
--        b) bôi đen các dòng có [SỬA] ở cuối -> nhấn Ctrl+/ (bật các dòng đó)
--      sau đó bấm F5.
--   4) Quay lại web, bấm  ▶ Chạy lại demo  ->  hết lỗi.
--   (Muốn gây lỗi lại: làm ngược lại bước 3.)
-- =====================================================================

-- ---- Chuẩn bị dữ liệu (chạy nhiều lần vẫn an toàn) ----
CREATE TABLE IF NOT EXISTS foods (
    id SERIAL PRIMARY KEY, name VARCHAR(100) NOT NULL,
    price INT NOT NULL CHECK (price >= 0), quantity INT NOT NULL CHECK (quantity >= 0),
    version INT NOT NULL DEFAULT 0
);
INSERT INTO foods (name, price, quantity)
SELECT 'Gà đặc biệt', 150000, 1 WHERE NOT EXISTS (SELECT 1 FROM foods WHERE name = 'Gà đặc biệt');

CREATE OR REPLACE FUNCTION demo_log(p_kind text, p_msg text) RETURNS void LANGUAGE plpgsql AS $$
BEGIN
  RAISE NOTICE '%|%|%', (extract(epoch from clock_timestamp()))::double precision, p_kind, p_msg;
END $$;

-- ---- Function đặt món ----
CREATE OR REPLACE FUNCTION sp_lu1_order(
    p_who text, p_qty int, p_process double precision, p_wait double precision)
RETURNS jsonb LANGUAGE plpgsql AS $$
DECLARE
    v_seen int;
    v_ver  int;
BEGIN
    IF p_wait > 0 THEN PERFORM pg_sleep(p_wait); END IF;

    -- (1) ĐỌC tồn kho (và version của dòng)
    SELECT quantity, version INTO v_seen, v_ver FROM foods WHERE name = 'Gà đặc biệt';
    PERFORM demo_log('info', format('Đọc: còn %s suất (version v%s)', v_seen, v_ver));

    PERFORM pg_sleep(p_process);       -- mô phỏng thời gian xử lý thanh toán

    IF v_seen < p_qty THEN
        PERFORM demo_log('warn', format('Hết món (chỉ còn %s) → từ chối', v_seen));
        RETURN jsonb_build_object('ok', false, 'seen', v_seen, 'qty', p_qty);
    END IF;

    -- (2) GHI tồn kho mới
    -- >>> SỬA TẠI ĐÂY <<<
    UPDATE foods SET quantity = v_seen - p_qty WHERE name = 'Gà đặc biệt';                              -- [LỖI] ghi đè bằng số CŨ đã đọc
    -- UPDATE foods SET quantity = quantity - p_qty, version = version + 1                                -- [SỬA]
    --  WHERE name = 'Gà đặc biệt' AND version = v_ver AND quantity >= p_qty;                             -- [SỬA]
    -- IF NOT FOUND THEN                                                                                  -- [SỬA]
    --     PERFORM demo_log('warn', 'version đã đổi (bên kia ghi trước) → từ chối');                      -- [SỬA]
    --     RETURN jsonb_build_object('ok', false, 'seen', v_seen, 'qty', p_qty, 'conflict', true);        -- [SỬA]
    -- END IF;                                                                                            -- [SỬA]

    PERFORM demo_log('ok', 'Ghi xong → đặt món thành công');
    RETURN jsonb_build_object('ok', true, 'seen', v_seen, 'qty', p_qty);
END $$;
