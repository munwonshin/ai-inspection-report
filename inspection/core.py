"""In-memory report data and approval-only export boundary."""
from dataclasses import dataclass, field
from .report_format import visit_date
from pathlib import Path
import hashlib
import json
import ntpath
import re
import xml.etree.ElementTree as ET
from copy import deepcopy

GENERAL = {
    'project': '과제명', 'lead_org': '주관기관', 'partner_org': '참여기관',
    'lead_person': '주관 책임자', 'partner_person': '참여 책임자',
    'visit_date': '방문일자', 'visit_org': '방문기관',
    'inspector_org': '점검자 소속', 'inspector': '점검자',
}

@dataclass(frozen=True)
class Report:
    title: str
    general: tuple
    findings: str
    actions: str
    checks: str

    def values(self):
        return dict(self.general)

    def missing(self):
        return [label for k, label in GENERAL.items() if not self.values().get(k, '').strip()]

    def as_dict(self):
        return dict(title=self.title, general=self.values(), findings=self.findings,
                    actions=self.actions, checks=self.checks)

def filename(value):
    # Normalize the filesystem name only; preserve the approved report title.
    value=re.sub(r'[.\s]+$','',value.strip())
    if value.lower().endswith('.hwp'):
        value=re.sub(r'[.\s]+$','',value[:-4].strip())
    if not value:
        raise ValueError('저장할 제목을 입력해 주세요. 공백·마침표·확장자만으로는 저장할 수 없습니다.')
    if len(value)>120 or any(c in '<>:"/\\|?*' or ord(c)<32 for c in value):
        raise ValueError('제목은 120자 이하로 입력하고 < > : " / \\ | ? * 및 제어문자를 제외해 주세요. 밑줄(_)·괄호·하이픈은 사용할 수 있습니다.')
    if value.split('.')[0].rstrip().upper() in {'CON','PRN','AUX','NUL',*(f'COM{i}' for i in '0123456789¹²³'),*(f'LPT{i}' for i in '0123456789¹²³')}:
        raise ValueError('Windows 예약 파일명은 사용할 수 없습니다.')
    return value+'.hwp'

def destination(folder, name):
    if not ntpath.isabs(folder) or not ntpath.splitdrive(folder)[0] or folder.startswith(('\\\\?\\','\\\\.\\')):
        raise ValueError('드라이브 절대 경로 또는 \\\\서버\\공유 경로를 입력해 주세요.')
    return Path(folder) / filename(name)

def normalize(s):
    return s.replace('\r\n','\n').replace('\r','\n').strip('\n')

def table_cell(table, row, col):
    return next(c for c in table.findall('./ROW/CELL')
                if int(c.get('RowAddr'))==row and int(c.get('ColAddr'))==col)

def cell_text(cell):
    return '\n'.join(''.join(p.itertext()) for p in cell.findall('./PARALIST/P'))

def set_cell(cell, value, top=False):
    pl = cell.find('PARALIST')
    original = pl.find('P')
    pa = dict(original.attrib)
    shape = original.find('TEXT').get('CharShape')
    for c in list(pl):
        pl.remove(c)
    if top:
        pl.set('VertAlign','Top')
    for line in normalize(value).split('\n'):
        p=ET.SubElement(pl,'P',pa)
        ET.SubElement(ET.SubElement(p,'TEXT',{'CharShape':shape}),'CHAR').text=line

def targets(tables, report):
    g=report.values()
    body=report.actions
    if report.checks.strip():
        body += ('\n\n' if body else '')+report.checks
    return [(2,0,0,report.title),
        (3,0,1,g['project']),(3,1,1,g['lead_org']),(3,1,3,g['partner_org']),
        (3,2,1,g['lead_person']),(3,2,3,g['partner_person']),
        (4,1,1,report.findings),(4,2,1,body),
        (5,0,1,visit_date(g['visit_date'])),(5,0,3,g['visit_org']),
        (5,1,1,g['inspector_org']),(5,1,3,g['inspector']),(5,1,4,'(인)')]

def parse_template(xml):
    root=ET.fromstring(xml)
    ts=list(root.iter('TABLE'))
    if [(t.get('RowCount'),t.get('ColCount')) for t in ts] != [('1','2'),('1','3'),('1','1'),('3','4'),('3','2'),('2','5')]:
        raise ValueError('승인된 양식의 표 구조와 다릅니다. 저장하지 않았습니다.')
    if any(root.iter('PICTURE')) or any(root.iter('OLE')):
        raise ValueError('양식에 검증되지 않은 그림 또는 OLE 개체가 있습니다.')
    return root,ts

def compose(template_xml, report):
    root, ts=parse_template(template_xml)
    for ti, row, col, value in targets(ts,report):
        if any(ord(c)<32 and c not in '\r\n\t' for c in value):
            raise ValueError('입력에 지원하지 않는 제어문자가 있습니다.')
        set_cell(table_cell(ts[ti],row,col),value,ti==4)
    # Only the empty separator paragraphs get a fixed 3pt height. Text retains
    # the template's original font and line spacing, without rewriting edits.
    shapes=root.find('.//PARASHAPELIST')
    by_id={s.get('Id'):s for s in shapes}
    blank_shapes={}
    for row in (1,2):
        for p in table_cell(ts[4],row,1).findall('./PARALIST/P'):
            if ''.join(p.itertext()).strip():continue
            source=p.get('ParaShape')
            if source not in blank_shapes:
                clone=deepcopy(by_id[source]);new_id=str(max(int(s.get('Id')) for s in shapes)+1)
                clone.set('Id',new_id);clone.set('SnapToGrid','false')
                margin=clone.find('PARAMARGIN')
                margin.set('LineSpacingType','Fixed');margin.set('LineSpacing','300')
                margin.set('Prev','0');margin.set('Next','0')
                shapes.append(clone);blank_shapes[source]=new_id
            p.set('ParaShape',blank_shapes[source])
    shapes.set('Count',str(len(shapes)))
    # Long body cells must be allowed to continue across page boundaries.
    ts[4].set('PageBreak','Cell')
    pos=ts[4].find('./SHAPEOBJECT/POSITION')
    pos.set('TreatAsChar','false')
    pos.set('FlowWithText','true')
    for p in root.iter():
        for c in list(p):
            if c.tag in {'SCRIPTCODE','DOCSUMMARY','BINDATASTORAGE'}:
                p.remove(c)
    return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'+ET.tostring(root,encoding='unicode')

def verify_xml(xml, report):
    root,ts=parse_template(xml)
    for ti,row,col,value in targets(ts,report):
        if normalize(cell_text(table_cell(ts[ti],row,col))) != normalize(value):
            raise ValueError('저장 후 편집 내용이 일치하지 않습니다. 최종 파일로 확정하지 않았습니다.')
    if any(root.iter('PICTURE')) or any(root.iter('OLE')):
        raise ValueError('서명 또는 개체 잔류가 발견됐습니다.')
    shapes={p.get('Id'):p for p in root.iter('PARASHAPE')}
    for row in (1,2):
        for p in table_cell(ts[4],row,1).findall('./PARALIST/P'):
            if ''.join(p.itertext()).strip():continue
            margin=shapes[p.get('ParaShape')].find('PARAMARGIN')
            if margin.get('LineSpacingType')!='Fixed' or int(margin.get('LineSpacing'))!=300:
                raise ValueError('저장 후 문단 사이 빈 줄의 고정 3pt 설정이 일치하지 않습니다.')

def evidenced_general(result, plan, minutes):
    """Only prefill exact source-backed values; the human supplies the rest."""
    accepted={}
    for k in GENERAL:
        v=result.get(k,{})
        if not isinstance(v,dict):
            continue
        value=v.get('value','').strip()
        quote=v.get('evidence','').strip()
        src={'plan':plan,'minutes':minutes}.get(v.get('source'),'')
        if value and quote and quote in src and value in quote:
            accepted[k]=value
    return accepted

def extract_pdf(path):
    from pypdf import PdfReader
    import io
    p=Path(path)
    if p.stat().st_size>30*1024*1024:
        raise ValueError('PDF는 30MB 이하로 첨부해 주세요.')
    data=p.read_bytes()
    if not data.startswith(b'%PDF-'):
        raise ValueError('실제 PDF 파일이 아닙니다.')
    reader=PdfReader(io.BytesIO(data))
    if reader.is_encrypted:
        raise ValueError('암호화된 PDF입니다. 암호를 제거한 사본을 첨부해 주세요.')
    if len(reader.pages)>250:
        raise ValueError('PDF는 250쪽 이하로 첨부해 주세요.')
    parts=[]
    # Send the complete PDF to the model, including diagrams and scanned pages.
    # Local text is only an extra exact-quote check for general-info prefilling.
    for i,page in enumerate(reader.pages[:8],1):
        text=(page.extract_text() or '').strip()
        parts.append(f'[사업계획서 {i}쪽]\n{text}')
    text='\n\n'.join(parts)
    return text,len(reader.pages),data
