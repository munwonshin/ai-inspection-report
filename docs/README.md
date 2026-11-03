# 포트폴리오 근거 문서

최종 7쪽 포트폴리오의 주요 설명을 확인할 수 있는 기록입니다. 원래 검증일·버전·성공 및 미검증 범위를 보존했습니다.

| 포트폴리오 내용 | 근거 |
| --- | --- |
| 모델 선택·비용·출력 비교 | [모델 비교](MODEL_EVALUATION.md), [가상 응답·usage](../benchmarks/synthetic_results.json), [토큰·비용](../benchmarks/token_cost.csv) |
| 날짜 선택·고정·오늘 강조 | [날짜·고정](CALENDAR_PIN_VERIFICATION.md), [앱 내부 달력](INLINE_CALENDAR_VERIFICATION.md), [오늘 날짜](TODAY_HIGHLIGHT_VERIFICATION.md) |
| HWP 직접 읽기·한글 자동 실행 제거·123개 검사 | [0.4.20 직접 읽기 검증](HWP_NO_LAUNCH_VERIFICATION.md) |
| PDF 전체 분석·분과·날짜 출력 | [전체 PDF](FULL_PDF_METADATA_VERIFICATION.md), [분과·날짜](DIVISION_DATE_VERIFICATION.md) |
| 초안 수정·이전 초안 복원·90개 검사·22회 AI 시험 | [채팅 검증](CHAT_REVISION_VERIFICATION.md), [테스트 소스](../tests), [검사 도구](../qa) |
| API 보존 초기화 | [초기화 검증](RESET_VERIFICATION.md) |
| 별첨 제거·분과 제목·파일명 분리 | [출력 양식·제목 검증](REPORT_HEADER_VERIFICATION.md) |
| 승인 저장·한글 결과 | [HWP 입출력](HWP_MEMORY_VERIFICATION.md), [본문·여백](BODY_SPACING_VERIFICATION.md) |
| 소스/배포 EXE의 API 오류 해결 | [API 진단](API_CONNECTION_VERIFICATION.md), [TLS 빌드 훅](../hooks/hook-ssl.py) |
| 단계별 자동 처리시간 | [3회 실측](WORKFLOW_TIMING_VERIFICATION.md) |
| 버전별 개발·검증 이력 | [개발 기록](DEVELOPMENT_TEST_RECORD.md) |

상세 시험 기록은 작성 당시 동작을 설명합니다. 현재 실행 방법은 [README](../README.md)를 기준으로 확인하세요. 검사 건수는 업무 정확도·만족도 수치가 아니며, 자동 처리시간은 사람의 입력·검토시간이나 편집 영상 길이와 구분합니다.

과거 기능별 검사 도구는 [0.4.24 정리 전 기록](https://github.com/munwonshin/ai-inspection-report/tree/35850bd0f59dd21bcfc9b78e4d3ee65a5bd88828)에서 확인할 수 있습니다.
