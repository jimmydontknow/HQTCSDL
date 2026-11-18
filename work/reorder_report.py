from docx import Document
from pathlib import Path
p=Path(r'D:\DHTT02Nam 3\HQTCSDL\restaurant-booking\outputs\Tieu_luan_HQTCSDL_den_Chuong_2.docx')
d=Document(p)
ps=list(d.paragraphs)
opening=next(x for x in ps if x.text.strip()=='MỞ ĐẦU' and x.style.name.startswith('Heading'))
ch3=next(x for x in ps if x.text.strip().startswith('CHƯƠNG 3.') and x.style.name.startswith('Heading'))
started=False; nodes=[]
for q in list(d.paragraphs):
    if q._p is opening._p: started=True; continue
    if q._p is ch3._p: break
    if started: nodes.append(q._p)
# The insertion pass had reversed this block; put it back in outline order.
for el in nodes: el.getparent().remove(el)
for el in reversed(nodes): ch3._p.addprevious(el)
d.save(p)
v=Document(p)
hs=[q.text for q in v.paragraphs if q.style.name.startswith('Heading')]
print('first_headings',hs[:15])
print('chapter_order',[x for x in hs if x.startswith('CHƯƠNG')])
print('first_content',[q.text[:90] for q in v.paragraphs[0:12]])
print('file_size',p.stat().st_size,'level3',sum(q.style.name=='Heading 3' for q in v.paragraphs))
