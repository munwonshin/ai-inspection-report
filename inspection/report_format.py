"""Document-facing formats without inventing missing PDF facts."""
import re
from datetime import date

DIVISIONS=('일반분과','반도체분과','소상공인분과','글로벌분과')

def canonical_division(value):
    value=re.sub(r'\s+','',value)
    return value+'분과' if value in ('일반','반도체','소상공인','글로벌') else value

def valid_document_context(year,division):
    return bool(re.fullmatch(r'20\d{2}',year.strip()) and canonical_division(division) in DIVISIONS)

def parse_visit_date(value):
    if isinstance(value,date):return value
    match=re.fullmatch(r'\s*(\d{4}|\d{2})\s*(?:년|-|\.|/)\s*(\d{1,2})\s*(?:월|-|\.|/)\s*(\d{1,2})\s*일?\.?\s*',value)
    if not match:return None
    year,month,day=map(int,match.groups())
    if year<100:year+=2000
    try:return date(year,month,day)
    except ValueError:return None

def visit_date(value):
    parsed=parse_visit_date(value)
    return f'{parsed.year}년 {parsed.month}월 {parsed.day}일' if parsed else value

def report_title(year='',division=''):
    year=year.strip();division=re.sub(r'\s+','',division)
    prefix=f'{year}년 ' if re.fullmatch(r'20\d{2}',year) else ''
    suffix=f' ({division})' if division else ''
    return prefix+'AI바우처 현장점검 결과'+suffix
