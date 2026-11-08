-- =====================================================================
-- MODULE 3 - UNREPEATABLE READ
--
-- CÁCH DÙNG (chỉ cần đúng 1 file này)
--   1) Bấm F5 để cài 2 function. Mặc định đang bị LỖI.
--   2) Vào web, tab "3", bấm  ▶ Chạy demo   ->  thấy UNREPEATABLE READ.
--   3) ĐỂ HẾT LỖI: kéo xuống chỗ  >>> SỬA TẠI ĐÂY <<<  rồi
--        a) bôi đen dòng có [LỖI] ở cuối  -> nhấn Ctrl+/   (tắt)
--        b) bôi đen dòng có [SỬA] ở cuối  -> nhấn Ctrl+/   (bật)
--      sau đó bấm F5.
--   4) Quay lại web, bấm  ▶ Chạy lại demo  ->  hết lỗi (thu ngân bị chặn đến khi khách xong).
-- =====================================================================

-- ---- Chuẩn bị dữ liệu (chạy nhiều lần vẫn an toàn) ----
CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY, customer_name VARCHAR(100) NOT NULL,
    order_date DATE NOT NULL DEFAULT CURRENT_DATE,
    subtotal INT NOT NULL DEFAULT 0, service_fee INT NOT NULL DEFAULT 0, discount INT NOT NULL DEFAULT 0,
    total INT GENERATED ALWAYS AS (subtotal + service_fee - discount) STORED,
    status VARCHAR(20) NOT NULL DEFAULT 'open'
);
INSERT INTO orders (customer_name, subtotal, status)
SELECT 'CART-DEMO', 500000, 'open' WHERE NOT EXISTS (SELECT 1 FROM orders WHERE customer_name = 'CART-DEMO');

CREATE OR REPLACE FUNCTION demo_log(p_kind text, p_msg text) RETURNS void LANGUAGE plpgsql AS $$
BEGIN
  RAISE NOTICE '%|%|%', (extract(epoch from clock_timestamp()))::double precision, p_kind, p_msg;
END $$;

-- ---- A: khách mở giỏ hàng, đọc tổng tiền 2 lần trong CÙNG một giao dịch ----
CREATE OR REPLACE FUNCTION sp_ur_customer(p_view double precision)
RETURNS jsonb LANGUAGE plpgsql AS $$
DECLARE
    v_first int;  v_second int;
    v_t1 double precision;  v_t2 double precision;
BEGIN
    v_t1 := extract(epoch from clock_timestamp());

    -- Lần đọc 1
    -- >>> SỬA TẠI ĐÂY <<<
    SELECT total INTO v_first FROM orders WHERE customer_name = 'CART-DEMO' LIMIT 1;                     -- [LỖI] đọc mà không khóa dòng
    -- SELECT total INTO v_first FROM orders WHERE customer_name = 'CART-DEMO' LIMIT 1 FOR SHARE;        -- [SỬA] khóa dòng đến hết giao dịch
    PERFORM demo_log('info', format('Đọc tổng tiền lần 1 → %s đ', v_first));

    PERFORM pg_sleep(p_view);          -- khách đang xem giỏ hàng rồi mới xác nhận

    v_t2 := extract(epoch from clock_timestamp());
    SELECT total INTO v_second FROM orders WHERE customer_name = 'CART-DEMO' LIMIT 1;                    -- lần đọc 2, cùng giao dịch
    PERFORM demo_log(CASE WHEN v_second <> v_first THEN 'err' ELSE 'ok' END,
                     format('Đọc tổng tiền lần 2 (cùng giao dịch) → %s đ', v_second));

    RETURN jsonb_build_object('ok', true, 'first', v_first, 'second', v_second,
                              't_read1', v_t1, 't_read2', v_t2);
END $$;

-- ---- B: thu ngân sửa hóa đơn (phí dịch vụ hoặc giảm giá), không cần sửa gì ở function này ----
CREATE OR REPLACE FUNCTION sp_ur_cashier(p_kind text, p_amount int, p_after double precision)
RETURNS jsonb LANGUAGE plpgsql AS $$
DECLARE
    v_t double precision;
BEGIN
    IF p_after > 0 THEN PERFORM pg_sleep(p_after); END IF;
    v_t := extract(epoch from clock_timestamp());      -- lúc thu ngân BẮT ĐẦU sửa

    IF p_kind = 'discount' THEN
        PERFORM demo_log('info', format('Sửa giảm giá = %s đ (nếu dòng đang bị khóa thì CHỜ)…', p_amount));
        UPDATE orders SET discount = LEAST(p_amount, subtotal + service_fee) WHERE customer_name = 'CART-DEMO';
    ELSE
        PERFORM demo_log('info', format('Sửa phí dịch vụ = %s đ (nếu dòng đang bị khóa thì CHỜ)…', p_amount));
        UPDATE orders SET service_fee = p_amount WHERE customer_name = 'CART-DEMO';
    END IF;

    PERFORM demo_log('ok', 'Đã sửa xong (chờ COMMIT)');
    RETURN jsonb_build_object('ok', true, 't_attempt', v_t);
END $$;

-- ---------------------------------------------------------------------
-- CÁCH SỬA THỨ HAI (chạy tay trong 2 tab pgAdmin, dùng mức REPEATABLE READ):
-- [Tab 1 - khách]   BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ;
--                   SELECT total FROM orders WHERE customer_name = 'CART-DEMO';      -- 500000
-- [Tab 2 - thu ngân] UPDATE orders SET service_fee = 50000 WHERE customer_name = 'CART-DEMO';
-- [Tab 1]           SELECT total FROM orders WHERE customer_name = 'CART-DEMO';      -- VẪN 500000
--                   COMMIT;
-- (Đổi dòng đầu thành READ COMMITTED rồi làm lại: lần 2 ra 550000 => lỗi.)
-- Dọn dẹp sau khi thử:  UPDATE orders SET service_fee = 0 WHERE customer_name = 'CART-DEMO';
-- ---------------------------------------------------------------------
