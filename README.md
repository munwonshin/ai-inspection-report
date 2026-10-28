# AI 현장점검 결과서 작성 도구

사업계획서 PDF와 회의록으로 초안을 만들고, 검토·수정 후 기존 한글 양식에 저장하는 Windows 데스크톱 프로그램입니다.

**버전 0.4.15** · `자료 입력 → AI 초안 → 편집·채팅 수정 → 승인 → HWP 저장`

## 주요 기능

- PDF 첨부·드래그 앤 드롭, 일반현황·사업연도·분과 자동 분석
- 회의록 중심 초안 생성, 직접 편집·채팅 수정·이전 초안 복원
- 날짜 선택과 점검자 정보 고정으로 반복 입력 최소화
- 승인한 내용만 기존 표·서식에 반영해 실제 HWP로 저장
- 로컬·UNC·매핑 드라이브 경로 지원, 같은 파일명 덮어쓰기 방지

## 실행

**필수:** Windows 64비트, 한글 COM 자동화가 가능한 한컴오피스, OpenAI API 키·인터넷 연결  
소스 실행·빌드에는 Python 3.12 64비트가 필요합니다.

배포 ZIP은 전체 압축을 풀고 `AIInspectionReport.exe`를 실행합니다. `_internal` 폴더를 함께 유지하세요. 실행 파일은 이 저장소에 포함하지 않습니다.

소스로 실행하려면 저장소 루트의 PowerShell에서:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

검사·빌드:

```powershell
.\.venv\Scripts\python.exe qa\run_unit_checks.py
.\build.ps1
```

빌드 결과는 `dist\AIInspectionReport\`에 생성됩니다.

## 사용 방법

1. **API 설정**에서 키를 저장하고 연결을 확인합니다. 기본 모델은 `gpt-6-luna`입니다.
2. PDF·회의록을 입력하고 자동 분석된 일반현황을 확인합니다.
3. 초안을 생성한 뒤 직접 편집하거나 채팅으로 수정합니다.
4. 제목·저장 폴더를 설정하고 **승인 및 한글 저장**을 누릅니다.

## 알아둘 점

- API 연결 상태에서 PDF를 첨부하면 원본 전체가 일반현황 분석을 위해 OpenAI로 전송됩니다. 생성·수정 시 회의록과 현재 초안 등도 전송되며 API 비용은 별도입니다.
- 키는 Windows 자격 증명 저장소에 보관해 다음 실행에서도 사용합니다. 소스·배포 파일에 키를 포함하지 않습니다.
- 승인 전에는 결과 파일을 만들지 않습니다. 저장 실패 시 편집 내용은 유지되지만, 프로그램 종료 시 미저장 초안은 사라집니다.
- AI가 작성한 사실·수치와 자동 입력값은 사용자가 최종 확인해야 합니다.
- Windows 11·한글 2018에서 검증했습니다. 다른 PC·한글 버전과 실제 NAS는 추가 검증이 필요합니다.

## 검증 기록

- [개발·테스트 기록](DEVELOPMENT_TEST_RECORD.md)
- [채팅 수정·복원 검증](CHAT_REVISION_VERIFICATION.md)
- [단계별 처리시간 실측](WORKFLOW_TIMING_VERIFICATION.md)
- [API 연결·배포본 진단](API_CONNECTION_VERIFICATION.md)
- [제3자 소프트웨어 고지](THIRD_PARTY_NOTICES.md)
