-- =====================================================================
-- MODULE 2 - DIRTY READ
--
-- CÁCH DÙNG: bấm F5 để cài 2 function, rồi vào web tab "2" bấm ▶ Chạy demo.
--
-- LƯU Ý: PostgreSQL KHÔNG có dirty read (READ UNCOMMITTED vẫn chạy như READ COMMITTED nhờ MVCC),
-- nên module này không có "chỗ lỗi" để sửa. Kết quả luôn là KHÔNG có dirty read. Cuối file có
-- kịch bản chạy tay và đoạn T-SQL tham khảo cho SQL Server (nơi dirty read xảy ra thật).
-- =====================================================================

CREATE OR REPLACE FUNCTION demo_log(p_kind text, p_msg text) RETURNS void LANGUAGE plpgsql AS $$
BEGIN
  RAISE NOTICE '%|%|%', (extract(epoch from clock_timestamp()))::double precision, p_kind, p_msg;
END $$;

-- A: nhân viên nhập đơn (INSERT + UPDATE) nhưng CHƯA COMMIT, giữ một lúc rồi ROLLBACK.
-- Function không tự ROLLBACK được nên kết thúc bằng RAISE EXCEPTION (hủy toàn bộ giao dịch).
-- ĐỪNG xóa dòng RAISE EXCEPTION cuối function, nếu không đơn sẽ bị COMMIT thật.
CREATE OR REPLACE FUNCTION sp_dr_staff(
    p_slot int, p_table int, p_name text, p_phone text, p_size int, p_hold double precision)
RETURNS jsonb LANGUAGE plpgsql AS $$
DECLARE
    s record;  t record;
    v_new int; v_t double precision;
BEGIN
    PERFORM demo_log('info', 'Nhân viên bắt đầu nhập đơn (BEGIN)');

    SELECT booked_seats, max_seats, slot_date INTO s FROM time_slots WHERE id = p_slot FOR UPDATE;
    IF NOT FOUND THEN RETURN jsonb_build_object('ok', false, 'error', 'Không tìm thấy khung giờ'); END IF;
    IF s.slot_date < CURRENT_DATE THEN RETURN jsonb_build_object('ok', false, 'error', 'Không thể đặt bàn cho ngày đã qua'); END IF;
    IF s.booked_seats + p_size > s.max_seats THEN
        RETURN jsonb_build_object('ok', false, 'error', format('Khung giờ chỉ còn %s chỗ', s.max_seats - s.booked_seats));
    END IF;

    SELECT name, capacity INTO t FROM restaurant_tables WHERE id = p_table;
    IF NOT FOUND THEN RETURN jsonb_build_object('ok', false, 'error', 'Không tìm thấy bàn'); END IF;
    IF p_size > t.capacity THEN
        RETURN jsonb_build_object('ok', false, 'error', format('%s chỉ chứa tối đa %s người', t.name, t.capacity));
    END IF;
    IF EXISTS (SELECT 1 FROM reservations WHERE table_id = p_table AND slot_id = p_slot AND status = 'confirmed') THEN
        RETURN jsonb_build_object('ok', false, 'error', format('%s đã được đặt trong khung giờ này', t.name));
    END IF;

    INSERT INTO reservations (customer_name, phone, table_id, slot_id, party_size)
    VALUES (p_name, p_phone, p_table, p_slot, p_size);
    UPDATE time_slots SET booked_seats = booked_seats + p_size WHERE id = p_slot RETURNING booked_seats INTO v_new;

    v_t := extract(epoch from clock_timestamp());
    PERFORM demo_log('info', format('Đã INSERT đơn (%s, %s người) và tăng chỗ đã đặt %s → %s, CHƯA COMMIT',
                                    t.name, p_size, s.booked_seats, v_new));

    PERFORM pg_sleep(p_hold);          -- giữ giao dịch mở: CHƯA COMMIT

    RAISE EXCEPTION 'DEMO_ROLLBACK|%|%|%|%', s.booked_seats, v_new, s.max_seats, v_t;   -- hủy toàn bộ (ROLLBACK)
END $$;

-- B: khách xem khung giờ còn bao nhiêu chỗ và bàn có trống không (2 lần).
-- Mức cô lập (READ UNCOMMITTED / READ COMMITTED) do web chọn khi mở kết nối của khách.
CREATE OR REPLACE FUNCTION sp_dr_customer(
    p_slot int, p_table int, p_after double precision, p_gap double precision)
RETURNS jsonb LANGUAGE plpgsql AS $$
DECLARE
    v_t1 double precision;
    v_left1 int;  v_taken1 boolean;
    v_left2 int;  v_taken2 boolean;
BEGIN
    PERFORM pg_sleep(p_after);
    v_t1 := extract(epoch from clock_timestamp());

    -- Nếu có dirty read, 2 câu SELECT này sẽ thấy dữ liệu CHƯA COMMIT của nhân viên.
    SELECT max_seats - booked_seats INTO v_left1 FROM time_slots WHERE id = p_slot;
    SELECT EXISTS (SELECT 1 FROM reservations
                    WHERE slot_id = p_slot AND table_id = p_table AND status = 'confirmed') INTO v_taken1;
    PERFORM demo_log('info', format('[%s] Xem lần 1 → còn %s chỗ, bàn %s',
                     current_setting('transaction_isolation'), v_left1,
                     CASE WHEN v_taken1 THEN 'đã đặt' ELSE 'còn trống' END));

    PERFORM pg_sleep(p_gap);           -- đợi nhân viên kết thúc

    SELECT max_seats - booked_seats INTO v_left2 FROM time_slots WHERE id = p_slot;
    SELECT EXISTS (SELECT 1 FROM reservations
                    WHERE slot_id = p_slot AND table_id = p_table AND status = 'confirmed') INTO v_taken2;
    PERFORM demo_log('info', format('Xem lần 2 (sau khi nhân viên kết thúc) → còn %s chỗ, bàn %s',
                     v_left2, CASE WHEN v_taken2 THEN 'đã đặt' ELSE 'còn trống' END));

    RETURN jsonb_build_object('ok', true,
        'iso', current_setting('transaction_isolation'),
        'first_left', v_left1, 'first_taken', v_taken1,
        'after_left', v_left2, 't_read', v_t1);
END $$;

-- =====================================================================
-- KỊCH BẢN CHẠY TAY trong pgAdmin (mở 2 tab Query Tool: tab 1 và tab 2).
-- Bỏ dấu -- ở các dòng cần chạy, bôi đen từng khối rồi bấm F5.
--
-- [Tab 1 - nhân viên]
--   BEGIN;
--   UPDATE time_slots SET booked_seats = booked_seats + 5 WHERE id = 3;    -- CHƯA COMMIT
-- [Tab 2 - khách]
--   BEGIN TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
--   SHOW transaction_isolation;                  -- báo "read uncommitted"
--   SELECT id, booked_seats FROM time_slots WHERE id = 3;   -- KHÔNG thấy +5 => KHÔNG có dirty read
--   COMMIT;
-- [Tab 1]
--   ROLLBACK;
--
-- THAM KHẢO (SQL Server, KHÔNG chạy trên PostgreSQL) - dirty read xảy ra thật:
--   [Phiên 1] BEGIN TRAN; UPDATE time_slots SET booked_seats = booked_seats + 5 WHERE id = 3;
--   [Phiên 2] SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
--             SELECT booked_seats FROM time_slots WHERE id = 3;     -- hoặc ... WITH (NOLOCK)
--   [Phiên 1] ROLLBACK;       -- phiên 2 đã đọc một con số "ma"
-- =====================================================================
