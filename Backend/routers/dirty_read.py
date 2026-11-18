from steps import Runner, make_router, val


def judge(key, R):
    p = val(R, "t2_read", "price")
    if p is None:
        return {"bug": False, "headline": "Chưa phân tích được: thiếu kết quả bước đọc của T2.", "explain": [], "fix": []}
    if p == 50000:
        return {"bug": True, "headline": "DIRTY READ: T2 đọc được 50000, là giá chưa COMMIT của T1.",
                "explain": ["T2 đọc dữ liệu mà T1 chưa COMMIT, rồi T1 ROLLBACK nên giá 50000 chưa từng tồn tại."],
                "fix": ["Dùng tối thiểu READ COMMITTED."]}
    ex = [f"Ở t2, T1 đã UPDATE giá = 50000 nhưng chưa COMMIT. T2 đọc được {p}: vẫn là giá cũ đã COMMIT.",
          "PostgreSQL xử lý READ UNCOMMITTED như READ COMMITTED nhờ MVCC: người đọc chỉ thấy phiên bản đã commit.",
          "Ở SQL Server (READ UNCOMMITTED hoặc NOLOCK), t2 sẽ đọc được 50000, sau đó T1 ROLLBACK nên đó là con số ma (xem đoạn T-SQL cuối file)."]
    if key == "commit":
        p2 = val(R, "t4_read", "price")
        ex.append(f"Sau khi T1 COMMIT ở t3, T2 đọc lại ở t4 và thấy {p2}: giá mới chỉ hiện ra khi đã COMMIT.")
    return {"bug": False, "headline": f"KHÔNG có dirty read: T2 đọc {p}, không thấy giá chưa COMMIT của T1.",
            "explain": ex, "fix": ["PostgreSQL không cho dirty read nên không có chỗ lỗi để sửa."]}


router = make_router("/dirty-read", "Module 2 - Dirty Read", Runner("m2_dirty_read.sql", judge))
