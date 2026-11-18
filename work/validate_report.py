from docx import Document
from zipfile import ZipFile
from pathlib import Path
p=Path(r'D:\DHTT02Nam 3\HQTCSDL\restaurant-booking\outputs\Tieu_luan_HQTCSDL_den_Chuong_2.docx')
d=Document(p); s=d.sections[0]; hs=[q.text for q in d.paragraphs if q.style.name.startswith('Heading')]
print('file',p.exists(),p.stat().st_size)
print('chapters',[x for x in hs if x.startswith('CHƯƠNG')])
print('last_ch2',next(x for x in hs if x.startswith('2.5.2.')))
print('level3_count',sum(q.style.name=='Heading 3' for q in d.paragraphs))
print('placeholder_in_completed_part',[(q.text[:70]) for q in d.paragraphs if q.text.startswith('[') and any(k in q.text for k in ['Trình bày','Nêu ','Mô tả','Xác định','Liệt kê']) and q.style.name!='Normal'])
print('course/title replaced',('HỆ QUẢN TRỊ CƠ SỞ DỮ LIỆU' in d.tables[0].cell(0,0).text),('TRUY XUẤT ĐỒNG THỜI' in d.tables[0].cell(0,0).text))
print('page',s.page_width/360000,s.page_height/360000,'margins',[getattr(s,x)/360000 for x in ['top_margin','left_margin','bottom_margin','right_margin']],'header_footer',s.header_distance/360000,s.footer_distance/360000)
with ZipFile(p) as z:
 x=z.read('word/document.xml').decode(); setting=z.read('word/settings.xml').decode(); i=x.find('TOC'); print('TOC_depth3',x[i:i+16], 'auto_update', 'w:updateFields' in setting)
print('font_spacing',d.styles['Normal'].font.name,d.styles['Normal'].font.size.pt,d.styles['Normal'].paragraph_format.line_spacing)
