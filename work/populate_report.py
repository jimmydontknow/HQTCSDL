from pathlib import Path
from shutil import copy2
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
src=Path(r'C:\Users\asus\Documents\Codex\2026-11-14\d-a-v-o-bi-u\outputs\Tieu_luan_He_quan_tri_co_so_du_lieu.docx')
out=Path(r'D:\DHTT02Nam 3\HQTCSDL\restaurant-booking\outputs\Tieu_luan_HQTCSDL_den_Chuong_2.docx')
out.parent.mkdir(parents=True,exist_ok=True); copy2(src,out); d=Document(out)
def setp(p,t):
    if p.runs:
        p.runs[0].text=t
        for x in p.runs[1:]: x.text=''
    else: p.add_run(t)
for tb in d.tables:
 for row in tb.rows:
  for c in row.cells:
   for p in c.paragraphs:
    if p.text.strip()=='TÊN HỌC PHẦN': setp(p,'HỆ QUẢN TRỊ CƠ SỞ DỮ LIỆU')
    elif p.text.strip()=='TÊN ĐỀ TÀI': setp(p,'HỆ THỐNG ĐẶT BÀN NHÀ HÀNG VÀ MÔ PHỎNG TRUY XUẤT ĐỒNG THỜI')
# Remove hand-typed contents lines but keep automatic TOC field.
ps=list(d.paragraphs); toc=next(p for p in ps if p.text.strip()=='MỤC LỤC'); tocfield=next(p for p in ps if 'Mục lục tự động' in p.text); inside=False
for p in list(d.paragraphs):
 if p._p is toc._p: inside=True; continue
 if p._p is tocfield._p: break
 if inside: p._p.getparent().remove(p._p)
# Remove old prompt content between opening and Ch. 3.
ps=list(d.paragraphs); opening=next(p for p in ps if p.text.strip()=='MỞ ĐẦU' and p.style.name.startswith('Heading')); ch3=next(p for p in ps if p.text.strip().startswith('CHƯƠNG 3.') and p.style.name.startswith('Heading')); inside=False
for p in list(d.paragraphs):
 if p._p is opening._p: inside=True; continue
 if p._p is ch3._p: break
 if inside: p._p.getparent().remove(p._p)
# (style, text) sequence; Heading 1/2/3 makes the TOC expand through level 3.
I=[]
def H(t,n=2): I.append(('Heading '+str(n),t))
def B(t): I.append(('Normal',t))
def C(t): I.append(('Heading 1',t))
B('Trong hệ thống đặt bàn nhà hàng, nhiều khách hàng có thể cùng chọn một khung giờ, trong khi nhân viên và quản lý đồng thời cập nhật đơn đặt, số chỗ còn lại hoặc thông tin hóa đơn. Nếu các giao dịch đọc và ghi dữ liệu không được điều phối đúng, hệ thống có thể xác nhận vượt sức chứa, ghi đè lượt đặt của người khác hoặc hiển thị kết quả không nhất quán.')
B('Tiểu luận trình bày cơ sở lý thuyết về hệ quản trị cơ sở dữ liệu, giao tác và truy xuất đồng thời, sau đó vận dụng vào ứng dụng đặt bàn nhà hàng và các mô-đun mô phỏng bất thường dữ liệu. Sản phẩm sử dụng PostgreSQL, FastAPI, psycopg2 và React. Trọng tâm là quan sát lịch thực thi của hai giao dịch, nhận diện hậu quả và so sánh các biện pháp kiểm soát.')
B('Nội dung được xây dựng dựa trên mã nguồn và các kịch bản SQL trong thư mục dự án; các kết luận về mức cô lập và khóa được đối chiếu với tài liệu chính thức của PostgreSQL [1]–[3].')
C('CHƯƠNG 1. GIỚI THIỆU')
H('1.1. Lý do chọn đề tài'); B('Các ứng dụng đặt bàn xử lý dữ liệu có tính cạnh tranh cao: hai khách có thể cùng yêu cầu chỗ cuối cùng trong một khung giờ, hoặc nhân viên có thể đang nhập đơn trong khi khách khác kiểm tra tình trạng chỗ. Nếu thao tác kiểm tra và thao tác ghi không được bảo vệ như một đơn vị nhất quán, cả hai giao dịch có thể dựa trên một số liệu cũ, khiến hệ thống xác nhận vượt khả năng phục vụ hoặc cập nhật sai số chỗ.')
B('Ngoài đặt bàn, việc đọc và cập nhật giá trị đơn hàng cũng có thể gặp lỗi khi nhiều giao dịch chạy đồng thời. Lost Update, Dirty Read, Unrepeatable Read và Phantom Read giúp minh họa vì sao DBMS cần giao tác, mức cô lập và khóa. Đề tài kết nối các khái niệm này với tình huống nhà hàng, đồng thời cho thấy PostgreSQL ngăn một số bất thường nhờ kiến trúc MVCC.')
H('1.2. Mục tiêu đề tài'); B('Mục tiêu tổng quát là xây dựng và phân tích ứng dụng đặt bàn nhà hàng có thể minh họa tác động của truy xuất đồng thời lên dữ liệu. Ứng dụng hỗ trợ xem bàn và khung giờ, tạo hoặc hủy đơn; các mô-đun cho phép hai giao dịch A và B thực hiện thao tác theo thời điểm người dùng chọn.')
B('Mục tiêu cụ thể: mô tả lịch giao dịch gây ra bốn bất thường; giải thích sự khác nhau giữa các mức cô lập; minh họa kiểm soát bằng version, FOR UPDATE, cập nhật nguyên tử và snapshot; ghi nhận nhật ký cùng dữ liệu sau COMMIT hoặc ROLLBACK để đối chiếu.')
H('1.3. Phạm vi đề tài'); B('Nghiệp vụ đặt bàn gồm xem bàn, chọn ngày/khung giờ, tạo đơn với tên, số điện thoại và số người, kiểm tra sức chứa bàn và khung giờ, và hủy đơn. Mã nguồn giới hạn ngày đặt trong 60 ngày tiếp theo, dùng các khung giờ 11:00, 12:00, 18:00 và 19:00; sức chứa mặc định mỗi khung giờ là 20 chỗ. Khi tạo đơn, API khóa dòng khung giờ bằng FOR UPDATE trước khi kiểm tra và cập nhật số chỗ [4].')
B('Phạm vi mô phỏng gồm Lost Update (khóa lạc quan theo version và khóa bi quan/cập nhật nguyên tử), Dirty Read, Unrepeatable Read và Phantom Read. Thử nghiệm dùng PostgreSQL và kết nối riêng cho mỗi giao dịch. Sản phẩm phục vụ học tập, chưa bao gồm thanh toán thực, xác thực/phân quyền hoàn chỉnh, mã hóa dữ liệu cá nhân hoặc kiểm thử tải quy mô sản xuất.')
H('1.4. Đối tượng nghiên cứu'); B('Đối tượng nghiên cứu gồm PostgreSQL; giao tác, lịch giao tác, MVCC, mức cô lập và khóa; dữ liệu bàn, khung giờ, đặt chỗ, món ăn và hóa đơn; cùng cách tầng React và FastAPI gửi yêu cầu đến cơ sở dữ liệu. Các vai trò khách hàng, nhân viên, quản lý và thu ngân được mô hình hóa thành hai phiên giao dịch đồng thời trong từng kịch bản.')
H('1.5. Phương pháp nghiên cứu'); B('Đề tài kết hợp nghiên cứu tài liệu để hệ thống hóa lý thuyết; phân tích mã nguồn để xác định bảng dữ liệu, điểm đọc/ghi và mức cô lập; thực nghiệm bằng cách chạy hai giao dịch với các khoảng chờ khác nhau; và so sánh kết quả giữa kịch bản lỗi với phương án kiểm soát. Nhật ký thời gian và trạng thái cuối cơ sở dữ liệu được dùng để kiểm chứng.')
H('1.6. Bố cục đề tài'); B('Chương 1 giới thiệu lý do, mục tiêu, phạm vi, đối tượng và phương pháp. Chương 2 trình bày nền tảng về DBMS, giao tác, truy xuất đồng thời, mức cô lập, khóa và an toàn dữ liệu. Chương 3 dự kiến khảo sát yêu cầu, phân tích hệ thống, thiết kế cơ sở dữ liệu và trình bày quá trình xây dựng, kiểm thử sản phẩm.')
C('CHƯƠNG 2. CƠ SỞ LÝ THUYẾT')
H('2.1. Tổng quan về hệ quản trị cơ sở dữ liệu')
H('2.1.1. Cơ sở dữ liệu và hệ quản trị cơ sở dữ liệu',3); B('Cơ sở dữ liệu là tập hợp dữ liệu được tổ chức để lưu trữ, truy vấn và cập nhật có kiểm soát. Hệ quản trị cơ sở dữ liệu (Database Management System – DBMS) cung cấp dịch vụ định nghĩa cấu trúc, thực thi truy vấn, quản lý giao tác, kiểm soát truy cập và phục hồi. Trong mô hình quan hệ, dữ liệu được biểu diễn bằng bảng; hàng là bản ghi, cột là thuộc tính, còn khóa và ràng buộc thể hiện định danh và quy tắc hợp lệ.')
H('2.1.2. Vai trò của DBMS trong ứng dụng đặt bàn',3); B('DBMS duy trì dữ liệu dùng chung để nhiều khách và nhân viên làm việc trên cùng trạng thái được quản lý. Với bài toán đặt bàn, hệ thống phải liên kết bàn, khung giờ và đơn; kiểm tra sức chứa; ngăn số chỗ đã đặt vượt giới hạn; đồng thời điều phối các phiên đọc và cập nhật. DBMS thực thi SQL, duy trì ràng buộc, quản lý giao tác và xử lý xung đột giữa kết nối.')
H('2.1.3. PostgreSQL và mô hình dữ liệu sử dụng',3); B('Dự án dùng PostgreSQL. Nghiệp vụ đặt bàn truy cập các bảng restaurant_tables, time_slots và reservations. Các mô-đun minh họa dùng thêm foods để mô phỏng tồn kho và orders để mô phỏng hóa đơn. Một số bảng demo được khởi tạo khi cần; các hàm SQL sp_* của mô-đun được cài từ tệp riêng trong thư mục sql. Backend Python kết nối bằng psycopg2, FastAPI cung cấp API cho giao diện React [4].')
H('2.2. Giao tác và lịch giao tác')
H('2.2.1. Khái niệm giao tác và tính chất ACID',3); B('Giao tác (transaction) là nhóm thao tác cơ sở dữ liệu được xử lý như một đơn vị. COMMIT xác nhận thay đổi; ROLLBACK hủy các thay đổi chưa xác nhận. ACID gồm: tính nguyên tử (Atomicity), các thao tác cùng được xác nhận hoặc cùng bị hủy; tính nhất quán (Consistency), giao tác bảo toàn các ràng buộc; tính cô lập (Isolation), điều chỉnh ảnh hưởng qua lại giữa giao tác đồng thời; tính bền vững (Durability), thay đổi đã xác nhận được lưu giữ theo bảo đảm của DBMS.')
B('Trong đặt bàn, tạo bản ghi reservation và tăng booked_seats phải cùng thành công hoặc cùng bị hủy. Nếu chỉ tạo đơn mà không tăng số chỗ, hoặc tăng số chỗ nhưng không tạo đơn, dữ liệu sẽ không nhất quán. Do đó các thao tác ghi và kiểm tra liên quan cần được bao trong cùng giao tác.')
H('2.2.2. Lịch giao tác và khả năng tuần tự hóa',3); B('Lịch giao tác là thứ tự xen kẽ thao tác đọc, ghi và kết thúc của nhiều giao tác. Lịch tuần tự chạy trọn từng giao tác; lịch đồng thời cho phép thao tác đan xen để tăng khả năng đáp ứng. Lịch đồng thời an toàn khi kết quả tương đương với một thứ tự tuần tự hợp lệ. Nếu thao tác xung đột trên cùng dữ liệu được sắp xếp không phù hợp, kết quả có thể phụ thuộc thứ tự thực hiện và vi phạm quy tắc nghiệp vụ.')
H('2.2.3. Các bất thường khi giao tác chạy đồng thời',3); B('Lost Update xảy ra khi hai giao tác đọc cùng giá trị cũ rồi ghi giá trị mới tính từ dữ liệu cũ, làm mất một cập nhật. Dirty Read là đọc thay đổi chưa COMMIT mà sau đó bị ROLLBACK. Unrepeatable Read xảy ra khi cùng giao tác đọc lại một dòng nhưng thấy giá trị đã được giao tác khác cập nhật và COMMIT. Phantom Read xảy ra khi chạy lại truy vấn có điều kiện nhưng tập dòng phù hợp đã đổi do giao tác khác thêm hoặc xóa dòng.')
B('Các mô-đun dùng dữ liệu dễ diễn giải: hai khách đặt từ cùng tồn kho cho Lost Update; nhân viên ghi đơn chưa COMMIT trong khi khách kiểm tra chỗ cho Dirty Read; khách đọc lại khoản phí trong lúc thu ngân cập nhật cho Unrepeatable Read; quản lý chạy lại truy vấn hóa đơn trong khi thu ngân thêm hóa đơn cho Phantom Read. Ba hiện tượng sau phản ánh đọc dữ liệu không nhất quán; Lost Update là xung đột ghi do trình tự đọc-tính-ghi.')
H('2.3. Điều khiển truy xuất đồng thời')
H('2.3.1. Mục đích và các hướng kiểm soát',3); B('Điều khiển đồng thời cho phép nhiều giao tác hoạt động mà vẫn bảo toàn tính nhất quán. Các hướng phổ biến gồm khóa khi có xung đột; kiểm tra phiên bản theo cơ chế lạc quan; cập nhật nguyên tử kèm điều kiện; và dùng snapshot hoặc mức cô lập do DBMS cung cấp. Mỗi cách có chi phí khác nhau về thời gian chờ, xác suất xung đột và nhu cầu thử lại.')
H('2.3.2. Mức cô lập giao tác',3); B('Bốn mức thường được nhắc đến là READ UNCOMMITTED, READ COMMITTED, REPEATABLE READ và SERIALIZABLE. Mức bảo vệ mạnh hơn có thể giảm khả năng cùng lúc xử lý hoặc khiến một giao tác phải thử lại. Bảng 2.1 tóm tắt hành vi PostgreSQL 18: READ UNCOMMITTED tương đương READ COMMITTED; REPEATABLE READ của PostgreSQL cũng ngăn Phantom Read, dù mức tối thiểu mà chuẩn SQL yêu cầu có thể thấp hơn [1].')
B('Bảng 2.1. Các hiện tượng theo mức cô lập trong PostgreSQL 18')
B('READ UNCOMMITTED: không Dirty Read; có thể Unrepeatable Read và Phantom Read. READ COMMITTED: không Dirty Read; có thể Unrepeatable Read và Phantom Read. REPEATABLE READ: không Dirty Read, Unrepeatable Read hoặc Phantom Read; vẫn có thể có serialization anomaly. SERIALIZABLE: hệ quản trị phát hiện lịch không tương đương tuần tự và có thể hủy một giao tác. Đây là hành vi PostgreSQL, không khẳng định mọi DBMS triển khai giống hệt [1].')
H('2.3.3. MVCC và snapshot trong PostgreSQL',3); B('PostgreSQL dùng điều khiển đồng thời đa phiên bản (Multiversion Concurrency Control – MVCC). Truy vấn đọc dựa trên snapshot phù hợp, nhờ đó đọc không nhất thiết phải chờ mọi giao tác ghi kết thúc. Ở READ COMMITTED, mỗi câu lệnh đọc thấy dữ liệu đã COMMIT trước khi câu lệnh bắt đầu; hai SELECT liên tiếp có thể thấy trạng thái khác nhau. Ở REPEATABLE READ, các câu đọc trong giao tác dùng snapshot ổn định hơn và không nhìn thấy các thay đổi được giao tác khác xác nhận sau khi snapshot được thiết lập [1], [2].')
B('Vì đặc tính này, mô-đun Dirty Read không tạo lần đọc bẩn thật trên PostgreSQL: READ UNCOMMITTED vẫn chỉ đọc dữ liệu đã COMMIT. Kịch bản ghi dữ liệu chưa xác nhận rồi ROLLBACK minh họa rằng khách không nhìn thấy thay đổi đó. Giao diện phân biệt hành vi PostgreSQL với tình huống lý thuyết trên DBMS cho phép dirty read [1], [4].')
H('2.3.4. Áp dụng kiểm soát vào các hiện tượng nghiên cứu',3); B('Có thể ngăn Lost Update bằng UPDATE nguyên tử có điều kiện quantity >= số lượng đặt, hoặc cập nhật theo cột version để phát hiện dữ liệu đã đổi. Unrepeatable Read có thể được kiểm soát bằng snapshot ổn định hoặc khóa phù hợp. Phantom Read cần mức snapshot thích hợp hoặc cơ chế khóa phạm vi/bảng; khóa bảng khiến thao tác ghi liên quan phải chờ. PostgreSQL ngăn Dirty Read bằng cách không cung cấp khả năng đọc thay đổi chưa COMMIT [1]–[3].')
H('2.4. Các vấn đề về khóa')
H('2.4.1. Khóa chia sẻ, khóa độc quyền và khóa dòng/bảng',3); B('Khóa điều phối quyền đọc hoặc ghi trên dữ liệu dùng chung. Tùy chế độ, nhiều thao tác đọc có thể cùng tồn tại trong khi cập nhật xung đột phải chờ đến khi giao tác giữ khóa kết thúc. Khóa dòng giới hạn xung đột ở các hàng liên quan; khóa bảng có phạm vi rộng hơn. PostgreSQL cung cấp khóa dòng tường minh như FOR UPDATE, FOR SHARE và khóa bảng qua LOCK [3].')
H('2.4.2. Khóa bi quan và khóa lạc quan',3); B('Khóa bi quan giả định xung đột có thể xảy ra, nên khóa dữ liệu trước khi cập nhật. Trong ứng dụng, SELECT khung giờ FOR UPDATE khóa dòng trước khi kiểm tra số chỗ và tăng booked_seats; thao tác hủy khóa dòng đơn trước khi đổi trạng thái và hoàn chỗ [4]. Cách này giúp bảo vệ quy trình đọc-sửa-ghi nhưng có thể làm phiên khác chờ.')
B('Khóa lạc quan không khóa ngay từ lần đọc đầu. Ứng dụng lưu version đã đọc rồi cập nhật với điều kiện version trong DB vẫn khớp. Nếu phiên khác cập nhật trước, câu lệnh không còn dòng phù hợp và ứng dụng báo xung đột để người dùng tải lại hoặc thử lại. Mô-đun Lost Update 1A minh họa version; mô-đun 1B minh họa FOR UPDATE và cập nhật nguyên tử có điều kiện tồn kho [4].')
H('2.4.3. Chờ khóa, deadlock và xử lý',3); B('Khi giao tác yêu cầu khóa do giao tác khác giữ, nó có thể phải chờ. Deadlock xảy ra khi các giao tác tạo thành vòng chờ khóa. PostgreSQL phát hiện tình trạng này và hủy một giao tác để giao tác khác tiếp tục. Có thể giảm rủi ro bằng cách lấy khóa theo cùng thứ tự, giữ giao tác ngắn và xử lý thử lại khi giao tác bị hủy vì deadlock [3].')
B('Khóa rộng hoặc giữ khóa lâu làm giảm khả năng xử lý đồng thời. Nên giới hạn phạm vi khóa và thời gian giữ khóa; đồng thời mọi luồng cập nhật cùng dữ liệu cần tuân thủ quy tắc khóa đã chọn.')
H('2.5. An toàn dữ liệu')
H('2.5.1. Toàn vẹn và nhất quán dữ liệu',3); B('Toàn vẹn dữ liệu là duy trì giá trị hợp lệ và quan hệ nghiệp vụ sau mỗi thao tác. Công cụ thường dùng gồm khóa chính/ngoại, NOT NULL, CHECK, kiểu dữ liệu, giao tác và cập nhật có điều kiện. Bảng foods có ràng buộc giá và số lượng không âm. Nghiệp vụ đặt bàn kiểm tra ngày, sức chứa bàn, số chỗ khung giờ và tình trạng bàn trước khi tạo đơn. Kiểm tra chống cạnh tranh cần phối hợp với giao tác và khóa/điều kiện cập nhật, không chỉ dựa vào giá trị đọc trước đó [4].')
H('2.5.2. Bảo vệ dữ liệu và giới hạn của sản phẩm hiện tại',3); B('An toàn dữ liệu còn gồm xác thực, phân quyền, bảo vệ thông tin cá nhân, sao lưu, phục hồi và ghi nhận sự kiện. Mã nguồn hiện tập trung vào giao tác và tính nhất quán phục vụ học tập; chưa phải hệ thống sản xuất có đầy đủ tài khoản, phân quyền, mã hóa hoặc quy trình sao lưu. Nếu phát triển tiếp, cần giới hạn quyền xem số điện thoại khách, quản lý cấu hình kết nối ngoài mã nguồn và kiểm tra định kỳ khả năng khôi phục bản sao lưu.')
B('Truy vấn nên truyền dữ liệu qua tham số của driver thay vì nối trực tiếp đầu vào người dùng vào chuỗi SQL. API cần kiểm tra kiểu và miền giá trị; DBMS cần giữ các ràng buộc ở cấp dữ liệu. Hai lớp bổ trợ nhau: ứng dụng trả lỗi dễ hiểu, còn ràng buộc DB bảo vệ dữ liệu qua các đường ghi khác nhau.')
# Insert the drafted content immediately before Chapter 3, in original order.
for style,text in reversed(I):
 p=ch3.insert_paragraph_before(style=style); r=p.add_run(text); r.font.name='Times New Roman'; r._element.get_or_add_rPr().rFonts.set(qn('w:eastAsia'),'Times New Roman')
 if style=='Normal': p.alignment=WD_ALIGN_PARAGRAPH.JUSTIFY; p.paragraph_format.line_spacing=1.5; p.paragraph_format.first_line_indent=Cm(1); p.paragraph_format.space_after=Pt(4); r.font.size=Pt(14)
 else:
  p.paragraph_format.keep_with_next=True
  if style=='Heading 1': p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.page_break_before=True
  if style=='Heading 3': p.paragraph_format.left_indent=Cm(.5)
# Replace sample references with bibliography supporting material through Ch. 2.
ps=list(d.paragraphs); ref=next(p for p in ps if p.text.strip()=='TÀI LIỆU THAM KHẢO'); appendix=next(p for p in ps if p.text.strip().startswith('PHỤ LỤC') and p.style.name.startswith('Heading')); inside=False
for p in list(d.paragraphs):
 if p._p is ref._p: inside=True; continue
 if p._p is appendix._p: break
 if inside: p._p.getparent().remove(p._p)
refs=[
'[1] PostgreSQL Global Development Group, “13.2. Transaction Isolation,” PostgreSQL 18 Documentation. https://www.postgresql.org/docs/18/transaction-iso.html (truy cập ngày 14/11/2026).',
'[2] PostgreSQL Global Development Group, “13.1. Introduction,” PostgreSQL 18 Documentation. https://www.postgresql.org/docs/18/mvcc-intro.html (truy cập ngày 14/11/2026).',
'[3] PostgreSQL Global Development Group, “13.3. Explicit Locking,” PostgreSQL 18 Documentation. https://www.postgresql.org/docs/18/explicit-locking.html (truy cập ngày 14/11/2026).',
'[4] Nhóm phát triển dự án, mã nguồn ứng dụng đặt bàn và mô-đun mô phỏng giao tác đồng thời: Backend/main.py, Backend/demo_utils.py, Backend/routers/, Frontend/src/ và sql/m1a_lost_update_lac_quan.sql, sql/m1b_lost_update_bi_quan.sql, sql/m2_dirty_read.sql, sql/m3_unrepeatable_read.sql, sql/m4_phantom_read.sql (truy cập ngày 14/11/2026).']
for t in reversed(refs):
 p=appendix.insert_paragraph_before(style='Normal'); p.add_run(t); p.alignment=WD_ALIGN_PARAGRAPH.JUSTIFY; p.paragraph_format.line_spacing=1.5; p.paragraph_format.left_indent=Cm(.8); p.paragraph_format.first_line_indent=Cm(-.8); p.paragraph_format.space_after=Pt(6)
 for r in p.runs: r.font.name='Times New Roman'; r.font.size=Pt(14); r._element.get_or_add_rPr().rFonts.set(qn('w:eastAsia'),'Times New Roman')
# Keep automatic TOC refresh on open.
u=d.settings.element.find(qn('w:updateFields'))
if u is None: u=OxmlElement('w:updateFields'); d.settings.element.append(u)
u.set(qn('w:val'),'true'); d.save(out)
# Structural checks
v=Document(out); hs=[p for p in v.paragraphs if p.style.name.startswith('Heading')]
assert any(p.text.startswith('2.5.2.') for p in hs) and any(p.text.startswith('CHƯƠNG 3.') for p in hs)
assert any('Mục lục tự động' in p.text for p in v.paragraphs)
assert sum(p.style.name=='Heading 3' for p in v.paragraphs)>=18
assert not any(p.text.startswith('[') and 'Trình bày' in p.text for p in v.paragraphs if p._p is not None)
print('OUTPUT',out,'SIZE',out.stat().st_size,'PARAGRAPHS',len(v.paragraphs),'HEADING3',sum(p.style.name=='Heading 3' for p in v.paragraphs))
print('CHAPTER_HEADINGS',[p.text for p in hs if p.text.startswith('CHƯƠNG')])
