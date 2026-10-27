"""In-memory exact undo and validated revision boundaries; never write drafts."""
import re
from dataclasses import replace

class DraftHistory:
    def __init__(self):self.versions=[]
    def record(self,report):
        if report.findings.strip() and (not self.versions or self.versions[-1]!=report):
            self.versions.append(report)
    def restore(self,current,*,first=False,fields=('findings','actions')):
        self.record(current)
        if len(self.versions)<2:return None
        target=self.versions[0] if first else self.versions[-2]
        self.versions.pop()
        if first:self.versions=self.versions[:1]
        result=replace(current,**{k:getattr(target,k) for k in fields})
        self.record(result)
        return result

def restore_intent(text):
    if not re.search(r'되돌|복원|돌려|돌리',text):return None
    if not re.search(r'이전|직전|수정\s*전|방금\s*수정|처음|최초',text):return None
    # Mixed new edits must not be mistaken for a pure restore command.
    if re.search(r'바꾸|변경|추가해|줄여|늘려|요약|삭제해|수정해',text):return None
    findings=bool(re.search(r'현장|확인\s*사항',text));actions='향후' in text or '조치요청' in text
    if findings and actions:
        if re.search(r'향후[^.\n]{0,35}(?:그대로|유지)',text):actions=False
        elif re.search(r'현장[^.\n]{0,35}(?:그대로|유지)',text):findings=False
    fields=tuple(k for k,b in [('findings',findings),('actions',actions)] if b) or ('findings','actions')
    return {'first':bool(re.search(r'처음|최초',text)),'fields':fields}

def revision_schema():
    props={k:{'type':'string'} for k in ('findings','actions','notice')}
    props['decision']={'type':'string','enum':['applied','unchanged','blocked']}
    return {'type':'object','additionalProperties':False,'properties':props,'required':list(props)}

REVISION_RULES='''채팅 수정의 추가 규칙:
decision은 applied(요청 반영), unchanged(변경 불필요), blocked(근거 부족·수정 불가) 중 하나다.
원자료에 없는 실적·수치·완료 상태를 만들라는 요청은 blocked로 반환하고 findings/actions를 현재 초안 그대로 반환한다. notice에는 반영하지 못한 이유만 한 문장으로 쓴다. 거절 과정에서 다른 문장이나 가상 표시·검수 메모를 재작성하지 않는다.
수정 범위 밖 항목은 공백·줄바꿈·글머리표까지 그대로 반환한다. 현재 초안의 가상 표시와 검수 메모는 사용자가 명시적으로 그 부분의 삭제·변경을 요청한 때만 바꾼다. 사용자가 그대로 유지하라는 직접 편집 문장은 원문 그대로 둔다.
applied일 때 notice는 빈 문자열이다. unchanged일 때 본문은 현재 원문 그대로 두고 notice에 변경 불필요 이유를 간단히 쓴다. 새 사실을 만들지 않는다.'''

def validate_revision(data,current,instruction):
    if not isinstance(data,dict) or set(data)!={'findings','actions','decision','notice'}:
        raise ValueError('revision schema')
    if not all(isinstance(data[k],str) for k in data):raise ValueError('revision types')
    if data['decision'] not in ('applied','unchanged','blocked'):raise ValueError('revision decision')
    before={k:current.get(k,'') for k in ('findings','actions')}
    if current.get('checks','').strip():before['actions']='\n\n'.join(v for v in (before['actions'],current['checks']) if v.strip())
    reason=''
    if data['decision']!='applied':
        reason=data['notice'].strip() or '요청을 반영하지 않았습니다. 현재 초안은 유지됩니다.'
    else:
        # A narrow, explicit "only" request cannot replace the other section.
        only_findings=bool(re.search(r'(?:현장[^.\n]{0,24}사항|findings)만',instruction))
        only_actions=bool(re.search(r'(?:향후[^.\n]{0,35}만|actions만)',instruction))
        if only_findings and not only_actions and data['actions']!=before['actions']:
            reason='요청 범위 밖 향후 항목의 변경이 감지되어 현재 초안을 유지했습니다.'
        if only_actions and not only_findings and data['findings']!=before['findings']:
            reason='요청 범위 밖 현장 항목의 변경이 감지되어 현재 초안을 유지했습니다.'
        for key in before:
            for marker in re.findall(r'\[가상[^\]\n]*\]',before[key]):
                if marker not in data[key]:reason='가상 자료 표시의 변경이 감지되어 현재 초안을 유지했습니다.'
            for marker in re.findall(r'검수\s*메모[^\n]*',before[key]):
                explicit_edit=bool(re.search(r'(검수\s*메모|메모\s*문장|메모\s*문단)',instruction) and re.search(r'삭제|제거|바꾸|변경|문체',instruction))
                # A whole-section style request may legitimately change endings.
                explicit_edit=explicit_edit or bool(re.search(r'문체|존댓말',instruction) and (key=='findings' and '현장' in instruction or key=='actions' and '향후' in instruction))
                if not explicit_edit and marker not in data[key]:
                    reason='직접 편집한 검수 메모의 변경이 감지되어 현재 초안을 유지했습니다.'
    if reason:
        return {**before,'checks':'','general':{},'_blocked':data['decision']=='blocked' or data['decision']=='applied','_notice':reason}
    if not data['findings'].strip():raise ValueError('empty revised body')
    return {k:data[k] for k in ('findings','actions')}|{'checks':'','general':{},'_notice':''}
