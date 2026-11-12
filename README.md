# AI 현장점검 결과서 작성 도구

사업계획서와 회의록으로 AI 초안을 만들고, 사람이 검토·수정·승인한 내용을 기존 한글 양식에 저장하는 Windows 프로그램입니다.

**자료 입력 → 초안 생성 → 검토·수정 → 승인 후 HWP 저장**

## 다운로드

**[Windows 실행용 ZIP 다운로드 · v0.4.26](https://github.com/munwonshin/ai-inspection-report/releases/download/v0.4.26/AIInspectionReport-0.4.26-windows-x64.zip)** · [전체 배포본](https://github.com/munwonshin/ai-inspection-report/releases)

1. ZIP 전체를 압축 해제합니다.
2. `AIInspectionReport` 폴더의 **바탕화면 아이콘 만들기.cmd**를 실행합니다.
3. 바탕화면 아이콘으로 프로그램을 엽니다.

Python을 별도로 설치할 필요는 없습니다. **Code → Download ZIP**은 실행용 배포본이 아닌 개발 소스입니다.

## 주요 기능

| 단계 | 기능 |
| --- | --- |
| 자료 입력 | PDF·HWP 첨부, 회의록 입력, 일반현황·사업연도·분과 분석 |
| 초안 생성 | 회의록을 근거로 본문 작성, 생성 진행 표시 |
| 검토·수정 | 직접 편집, 채팅 수정, 이전 초안 복원 |
| 승인·저장 | 기존 HWP 양식 저장, 덮어쓰기 방지, 파일·폴더 열기 |

방문일 달력, 점검 정보 고정, API 설정을 유지하는 초기화를 지원합니다. 종합의견은 본문 10pt·문단 사이 빈 줄 3pt로 저장합니다.

![가상 자료를 사용한 프로그램 화면](docs/images/app-workflow.png)

*가상 자료를 사용한 v0.4.15 화면입니다.*

## 사용 방법

**필수 환경:** Windows 64비트, 한글 COM 자동화를 지원하는 한컴오피스, OpenAI API 키, 인터넷 연결

1. **API 설정**에서 키를 저장하고 연결을 확인합니다.
2. 사업계획서와 회의록을 넣고 일반현황·연도·분과를 확인합니다.
3. 초안을 생성하고 직접 편집하거나 채팅으로 수정합니다.
4. 파일명·저장 폴더를 지정하고 **승인 및 한글 저장**을 누릅니다.

- HWP는 첨부 시 한글 실행·PDF 변환 없이 직접 읽습니다. 최대 30MB이며 HWPX는 지원하지 않습니다.
- 로컬·UNC·매핑 드라이브 저장을 지원합니다.
- 문서·참조 그림·회의록·초안 등이 OpenAI로 전송되며 API 비용은 별도입니다. 기본 모델은 `gpt-6-luna`입니다.
- 키는 Windows 자격 증명 저장소에 보관합니다. 사실·수치·자동 입력값은 사용자가 최종 확인해야 합니다.
- 승인 전에는 결과 HWP를 저장하지 않습니다. 실패 시 입력은 유지하지만, 종료하면 미저장 초안은 사라집니다.

[첨부 지원 범위](docs/HWP_NO_LAUNCH_VERIFICATION.md)

## 적용 결과와 제품 개선

| 구분 | 결과 |
| --- | --- |
| 초기 개인 업무 적용 | 3건 이상 사용, 평균 약 60분 → 3분으로 약 95% 단축 |
| C1 재검수 개선 | 합성 시험에서 미검토 저장 진입 18/18 → 0/18건 |
| 정상 흐름 보존 | 같은 시험에서 정상 저장 오차단 0/30건 유지 |

초기 시간 성과는 건별 원기록이 없는 개인 적용 경험입니다. C1 결과는 동일 합성 시나리오 16개를 3회 반복한 검증이며 운영 사고율이나 실제 HWP 저장 성공률을 뜻하지 않습니다.

C1은 자료 변경 후 이전 본문이 재검토 없이 승인되는 문제를 다뤘습니다. **로컬 구현·합성 검증만 완료했으며 실제 HWP 연동 시험과 정식 출시는 보류 상태입니다.** 위 v0.4.26 배포본에 반영된 기능은 아닙니다.

업무 문제·요구사항·우선순위·검수·출시 판단을 정의하고, Codex의 분석·구현·테스트 지원을 활용했습니다.

[제품 개선 사례](docs/product/PM_CASE_STUDY.md) · [검증 결과](docs/product/EVIDENCE_SUMMARY.md) · [출시 검토](docs/product/RELEASE_REVIEW_PUBLIC.md)

## 개발 환경

Python 3.12·Tkinter 기반입니다. PDF는 pypdf/pypdfium2, HWP 저장은 한글 COM, 패키징은 PyInstaller를 사용합니다. 의존성 버전은 [requirements.txt](requirements.txt)를 확인하세요.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

검사와 패키징은 `.\build.ps1`로 실행하며, 결과는 `dist/AIInspectionReport/`에 생성됩니다.

## 상세 기록

[검사 도구](qa/README.md) · [개발·검증 기록](docs/DEVELOPMENT_TEST_RECORD.md) · [모델 비교](docs/MODEL_EVALUATION.md) · [버전별 상세 이력](https://github.com/munwonshin/ai-inspection-report/blob/5bf235601ff873cb4e310c024ab85db53757c355/README.md#버전별-개선-이력) · [제3자 소프트웨어 고지](THIRD_PARTY_NOTICES.md)
