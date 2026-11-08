-- =====================================================================
-- MODULE 4 - PHANTOM READ
--
-- CÁCH DÙNG (chỉ cần đúng 1 file này)
--   1) Bấm F5 để cài 2 function. Mặc định đang bị LỖI.
--   2) Vào web, tab "4", bấm  ▶ Chạy demo   ->  thấy PHANTOM READ.
--   3) ĐỂ HẾT LỖI: kéo xuống chỗ  >>> SỬA TẠI ĐÂY <<<  rồi
--      bôi đen dòng có [SỬA] ở cuối -> nhấn Ctrl+/ (bật dòng đó), sau đó bấm F5.
--   4) Quay lại web, bấm  ▶ Chạy lại demo  ->  hết lỗi (thu ngân bị chặn đến khi quản lý xong).
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
SELECT 'SEED', v.s, 'paid'
FROM (VALUES (120000), (180000), (250000), (300000), (450000)) AS v(s)
WHERE NOT EXISTS (SELECT 1 FROM orders WHERE customer_name = 'SEED');

CREATE OR REPLACE FUNCTION demo_log(p_kind text, p_msg text) RETURNS void LANGUAGE plpgsql AS $$
BEGIN
  RAISE NOTICE '%|%|%', (extract(epoch from clock_timestamp()))::double precision, p_kind, p_msg;
END $$;

-- ---- A: quản lý xuất báo cáo doanh thu 2 lần trong CÙNG một giao dịch ----
CREATE OR REPLACE FUNCTION sp_ph_manager(p_min int, p_view double precision)
RETURNS jsonb LANGUAGE plpgsql AS $$
DECLARE
    v_ids1 jsonb;  v_ids2 jsonb;
    v_sum1 bigint; v_sum2 bigint;
    v_t1 double precision;  v_t2 double precision;
BEGIN
    -- >>> SỬA TẠI ĐÂY <<<   (bật dòng dưới là hết lỗi; không có dòng [LỖI] nào cần tắt)
    -- LOCK TABLE orders IN SHARE MODE;                                                                -- [SỬA] khóa bảng: người khác chỉ đọc được, không INSERT được

    v_t1 := extract(epoch from clock_timestamp());
    SELECT COALESCE(jsonb_agg(id ORDER BY id), '[]'::jsonb), COALESCE(SUM(total), 0)
      INTO v_ids1, v_sum1
      FROM orders
     WHERE order_date = CURRENT_DATE AND status = 'paid' AND total >= p_min;
    PERFORM demo_log('info', format('Báo cáo lần 1 (hóa đơn từ %s đ) → %s hóa đơn, doanh thu %s đ',
                                    p_min, jsonb_array_length(v_ids1), v_sum1));

    PERFORM pg_sleep(p_view);          -- quản lý đang xem báo cáo

    v_t2 := extract(epoch from clock_timestamp());
    SELECT COALESCE(jsonb_agg(id ORDER BY id), '[]'::jsonb), COALESCE(SUM(total), 0)
      INTO v_ids2, v_sum2
      FROM orders
     WHERE order_date = CURRENT_DATE AND status = 'paid' AND total >= p_min;
    PERFORM demo_log(CASE WHEN v_ids2 <> v_ids1 THEN 'err' ELSE 'ok' END,
                     format('Báo cáo lần 2 (cùng giao dịch) → %s hóa đơn, doanh thu %s đ',
                            jsonb_array_length(v_ids2), v_sum2));

    RETURN jsonb_build_object('ok', true, 'ids1', v_ids1, 'ids2', v_ids2,
                              'sum1', v_sum1, 'sum2', v_sum2, 't_read1', v_t1, 't_read2', v_t2);
END $$;

-- ---- B: thu ngân tạo hóa đơn mới, không cần sửa gì ở function này ----
CREATE OR REPLACE FUNCTION sp_ph_cashier(p_total int, p_after double precision)
RETURNS jsonb LANGUAGE plpgsql AS $$
DECLARE
    v_t double precision;
    v_id int;
BEGIN
    IF p_after > 0 THEN PERFORM pg_sleep(p_after); END IF;
    v_t := extract(epoch from clock_timestamp());      -- lúc thu ngân BẮT ĐẦU tạo hóa đơn

    PERFORM demo_log('info', format('Tạo hóa đơn mới %s đ (nếu bảng đang bị khóa thì CHỜ)…', p_total));
    INSERT INTO orders (customer_name, subtotal, status)
    VALUES ('DEMO-PHANTOM', p_total, 'paid') RETURNING id INTO v_id;

    PERFORM demo_log('ok', format('Đã tạo hóa đơn #%s (chờ COMMIT)', v_id));
    RETURN jsonb_build_object('ok', true, 'id', v_id, 'total', p_total, 't_attempt', v_t);
END $$;

-- ---------------------------------------------------------------------
-- CÁCH SỬA THỨ HAI (chạy tay trong 2 tab pgAdmin, dùng mức REPEATABLE READ):
-- [Tab 1 - quản lý] BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ;
--                   SELECT count(*) FROM orders WHERE order_date = CURRENT_DATE AND status = 'paid';   -- 5
-- [Tab 2 - thu ngân] INSERT INTO orders (customer_name, subtotal, status) VALUES ('DEMO-PHANTOM', 200000, 'paid');
-- [Tab 1]           SELECT count(*) FROM orders WHERE order_date = CURRENT_DATE AND status = 'paid';   -- VẪN 5
--                   COMMIT;
-- (Đổi dòng đầu thành READ COMMITTED rồi làm lại: lần 2 ra 6 => phantom read.)
-- Dọn dẹp sau khi thử:  DELETE FROM orders WHERE customer_name = 'DEMO-PHANTOM';
-- ---------------------------------------------------------------------
