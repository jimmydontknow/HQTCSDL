from steps import Runner, make_router, val


def judge(key, R):
    r1, r2 = val(R, "r1"), val(R, "r2")
    if r1 is None or r2 is None:
        return {"bug": False, "headline": "Chưa phân tích được: thiếu kết quả hai lần đọc.", "explain": [], "fix": []}
    if r1 != r2:
        return {"bug": True, "headline": f"UNREPEATABLE READ: cùng một giao dịch nhưng lần đọc 1 = {r1}, lần đọc 2 = {r2}.",
                "explain": [f"Ở t1 T1 đọc tổng tiền = {r1}. Ở t2 T2 sửa phí dịch vụ và COMMIT.",
                            "Ở READ COMMITTED mỗi câu SELECT lấy snapshot mới nên ở t3 T1 đọc lại thấy dữ liệu T2 vừa commit.",
                            "Dòng gây lỗi: lần đọc 2 ở t3 (chú thích '-- LỖI')."],
                "fix": ["Chọn kịch bản 'Sửa 1' (REPEATABLE READ) hoặc 'Sửa 2' (FOR SHARE) và so sánh các dòng '-- SỬA'."]}
    if (R.get("fee") or {}).get("waited"):
        ex = ["Ở t2 T2 định UPDATE nhưng bị CHỜ vì T1 đang khóa dòng (FOR SHARE).",
              f"T1 đọc lần 2 vẫn = {r2}, rồi COMMIT ở t4 để nhả khóa; sau đó T2 mới sửa xong. Thay đổi của T2 không bị mất, chỉ phải chờ."]
    else:
        ex = [f"T2 đã sửa và COMMIT ở t2 (không bị chặn) nhưng T1 vẫn đọc {r2} ở t3.",
              "REPEATABLE READ lấy snapshot một lần lúc bắt đầu giao dịch nên T1 thấy thế giới 'đứng yên'. PostgreSQL không chặn T2 như SQL Server."]
    return {"bug": False, "headline": f"Không có lỗi: hai lần đọc đều = {r1}.", "explain": ex, "fix": []}


router = make_router("/unrepeatable-read", "Module 3 - Unrepeatable Read", Runner("m3_unrepeatable_read.sql", judge))
