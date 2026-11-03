# 검사 도구

Windows에서 의존성을 설치한 뒤 저장소 루트에서 실행합니다.

```powershell
.\.venv\Scripts\python.exe qa\run_unit_checks.py
```

0.4.24 단위 검사 137개는 승인 전 저장 차단, 수정 내용 보존, 입력 처리, 파일명과 바로가기 등을 확인합니다. 실제 API·한글·NAS 통합 시험이나 업무 정확도 수치와 구분합니다.

| 목적 | 도구 |
| --- | --- |
| 전체 단위 검사 | `run_unit_checks.py` |
| 빌드 EXE와 소스 일치 | `verify_frozen.py PATH_TO_EXE` |
| HWP 직접 읽기 | `direct_hwp_checks.py` |
| PDF 처리 비교 | `pdf_baseline.py`, `pdf_speed_benchmark.py`, `pdf_visual_verify.py` |
| 화면 흐름·초기화·제목 | `workflow_checks.py`, `reset_checks.py`, `report_header_checks.py` |
| API 연결 모의 시험 | `api_connection_checks.py` |
| 실제 AI·한글 통합 시험 | `direct_visual_workflow.py`, `revision_checks.py`, `report_header_roundtrip.py`, `hwp_memory_checks.py` |

단위 검사와 GUI 모의 시험은 실제 서비스 시험과 다릅니다. 통합 도구는 실행 조건을 먼저 확인하고 가상 자료·별도 시험 폴더를 사용하세요. 실제 API는 비용이 발생하고, 한글 저장 시험은 파일을 생성합니다. `hwp_memory_checks.py`는 `--approved EXISTING_TEST_FOLDER`로 명시적으로 실행합니다.

현재 동작의 반복 검사와 겹치는 과거 화면 점검 스크립트는 정리했습니다. 당시 근거와 도구는 [정리 전 기록](https://github.com/munwonshin/ai-inspection-report/tree/35850bd0f59dd21bcfc9b78e4d3ee65a5bd88828/qa)에서 확인할 수 있습니다.

[검증 근거](../docs/README.md)
