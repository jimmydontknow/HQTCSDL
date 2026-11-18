from steps import Runner, make_router, val


def judge(key, R):
    n1, n2 = val(R, "c1", "so_hoa_don"), val(R, "c2", "so_hoa_don")
    if n1 is None or n2 is None:
        return {"bug": False, "headline": "Chưa phân tích được: thiếu kết quả hai lần báo cáo.", "explain": [], "fix": []}
    if n1 != n2:
        return {"bug": True, "headline": f"PHANTOM READ: báo cáo lần 1 có {n1} hóa đơn, lần 2 có {n2} hóa đơn.",
                "explain": [f"Ở t1 T1 xuất báo cáo: {n1} hóa đơn. Ở t2 T2 INSERT hóa đơn mới và COMMIT.",
                            "Ở READ COMMITTED câu truy vấn ở t3 lấy snapshot mới nên thấy thêm một dòng 'ma'.",
                            "Dòng chưa tồn tại thì không có gì để khóa từng dòng. Dòng gây lỗi: truy vấn lần 2 ở t3 (chú thích '-- LỖI')."],
                "fix": ["Chọn kịch bản 'Sửa 1' (REPEATABLE READ) hoặc 'Sửa 2' (LOCK TABLE) và so sánh các dòng '-- SỬA'."]}
    if (R.get("ins") or {}).get("waited"):
        ex = ["Ở t2 T2 định INSERT nhưng bị CHỜ vì T1 đang khóa cả bảng (LOCK TABLE ... SHARE MODE).",
              f"T1 xuất lần 2 vẫn {n2} hóa đơn, COMMIT ở t4 để nhả khóa; sau đó T2 mới INSERT xong."]
    else:
        ex = [f"T2 đã INSERT và COMMIT ở t2 (không bị chặn) nhưng T1 vẫn thấy {n2} hóa đơn ở t3.",
              "REPEATABLE READ dùng snapshot cố định. Theo chuẩn SQL mức này vẫn cho phantom, nhưng PostgreSQL chặn được ngay ở mức này."]
    return {"bug": False, "headline": f"Không có phantom: hai lần báo cáo đều {n1} hóa đơn.", "explain": ex, "fix": []}


router = make_router("/phantom-read", "Module 4 - Phantom Read", Runner("m4_phantom_read.sql", judge))
