# 검사 도구

저장소 루트에서 Windows용 의존성을 설치한 뒤 실행합니다.

```powershell
.\.venv\Scripts\python.exe qa\run_unit_checks.py
```

0.4.16의 98개 단위검사에는 승인 전 저장 차단, 수정 범위·검수 메모 보존, 이전 초안 복원 등이 포함됩니다. 실제 API·한글·NAS 통합 시험과 구분합니다.

`hwp_input_checks.py`는 실제 TkDND에서 HWP 버튼·드롭·삭제·교체 오류 보존을 검사합니다. 변환·API·저장은 모의 처리하며 실제 사용자의 자료나 키를 읽지 않습니다.

## 도구 구분

| 대상 | 스크립트 |
| --- | --- |
| 채팅·편집·승인·입력 보존 | `chat_checks.py`, `ui_checks.py`, `workflow_checks.py`, `response_failure_checks.py` |
| 화면 배치·진행 표시 | `chat_layout_checks.py`, `stream_checks.py`, `quiet_checks.py` |
| 첨부·일반현황·저장 이름 | `pdf_drop_checks.py`, `metadata_checks.py`, `save_name_checks.py` |
| 달력·고정·날짜·분과 | `calendar_pin_checks.py`, `inline_calendar_checks.py`, `pin_tick_checks.py`, `today_checks.py`, `division_checks.py` |
| 연결·키 재사용의 모의 시험 | `api_connection_checks.py`, `remember_checks.py` |
| PDF 로컬 성능·보존 대조 | `pdf_speed_benchmark.py`, `pdf_visual_verify.py`, `pdf_baseline.py`, `lightweight_benchmark.py` |
| 배포 EXE의 소스 일치 | `verify_frozen.py PATH_TO_EXE` — 빌드 마지막에도 실행 |
| 실제 AI 수정 검증 | `revision_checks.py` — 실행 옵션·비용·가상 자료 조건을 먼저 확인 |
| 실제 한글 저장·재입력 | `hwp_memory_checks.py --approved EXISTING_TEST_FOLDER` — 가상 출력의 명시적 승인 필요 |

GUI 회귀 검사는 실제 Tk 위젯과 모의 네트워크·저장을 사용합니다. 실제 API·한글을 이용하는 도구는 별도로 구분했으며, 전체 단위검사에서 자동 실행하지 않습니다. 시간에 민감한 GUI 검사는 순차 실행하세요.

실제 API 시험은 비용이 발생합니다. 키는 Windows 자격 증명 저장소를 사용하며 업무자료 대신 명확한 가상 자료를 사용하세요. 시험 출력은 로컬 검증용이고 배포 프로그램의 업무 로그 기능이 아닙니다.

[검증 근거 안내](../docs/README.md) · [개발 이력](../docs/DEVELOPMENT_TEST_RECORD.md)
