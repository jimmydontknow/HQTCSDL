from steps import Runner, make_router, val


def judge(key, R):
    a_read, final = val(R, "a_read"), val(R, "final")
    if a_read is None or final is None:
        return {"bug": False, "headline": "Chưa phân tích được: thiếu kết quả bước đọc hoặc bước kiểm tra cuối.", "explain": [], "fix": []}
    b_read = val(R, "b_read")
    sold = sum(1 for k in ("a_write", "b_write") if (R.get(k) or {}).get("rowcount"))
    reduced = a_read - final
    if sold != reduced:
        return {"bug": True,
                "headline": f"LOST UPDATE: có {sold} lượt đặt thành công (UPDATE 1) nhưng kho chỉ giảm {reduced}.",
                "explain": [
                    f"Ở t1 và t2, T1 và T2 cùng đọc tồn kho (T1 thấy {a_read}, T2 thấy {b_read}) trước khi bên nào ghi.",
                    "Ở t3, T1 ghi quantity = 0 (tính từ số cũ) rồi COMMIT. Ở t4, T2 cũng ghi quantity = 0 (cũng tính từ số cũ) và ghi đè kết quả của T1.",
                    "Hai lệnh UPDATE đều gán một giá trị tuyệt đối nên không bên nào biết bên kia đã sửa. Một lượt đặt bị mất khỏi sổ sách.",
                    "Dòng gây lỗi: các dòng có chú thích '-- LỖI' ở bước t3 và t4."],
                "fix": ["Chọn kịch bản 'Sửa 1' (version), 'Sửa 2' (FOR UPDATE) hoặc 'Sửa 3' (UPDATE nguyên tử) và so sánh các dòng có chú thích '-- SỬA'."]}
    if key == "sua_version" or (R.get("b_write") or {}).get("rowcount") == 0:
        why = "Câu UPDATE của T2 có điều kiện version = 0 nhưng T1 đã tăng version lên 1 nên 0 dòng bị ảnh hưởng (UPDATE 0). T2 bị từ chối."
    elif key == "sua_for_update":
        why = f"T2 bị CHỜ ở t2 vì T1 giữ khóa dòng (FOR UPDATE). Sau khi T1 COMMIT, T2 đọc ra {b_read} suất nên không đặt được."
    else:
        why = "T2 bị CHỜ ở t4 vì T1 chưa COMMIT. Sau khi T1 COMMIT, T2 chạy lại điều kiện quantity >= 1 và không còn dòng nào khớp."
    return {"bug": False,
            "headline": f"Không mất dữ liệu: bán {sold} suất và kho giảm đúng {reduced}.",
            "explain": [why, "Dòng sửa lỗi: các dòng có chú thích '-- SỬA'."], "fix": []}


router = make_router("/lost-update", "Module 1 - Lost Update", Runner("m1_lost_update.sql", judge))
