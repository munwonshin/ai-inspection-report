# 포트폴리오 근거 문서

최종 7쪽 포트폴리오의 주요 설명을 확인할 수 있는 기록입니다. 원래 검증일·버전·성공 및 미검증 범위를 보존했습니다.

| 포트폴리오 내용 | 근거 |
| --- | --- |
| 모델 선택·비용·출력 비교 | [모델 비교](MODEL_EVALUATION.md), [가상 응답·usage](../benchmarks/synthetic_results.json), [토큰·비용](../benchmarks/token_cost.csv) |
| 날짜 선택·고정·오늘 강조 | [날짜·고정](CALENDAR_PIN_VERIFICATION.md), [앱 내부 달력](INLINE_CALENDAR_VERIFICATION.md), [오늘 날짜](TODAY_HIGHLIGHT_VERIFICATION.md) |
| HWP 직접 읽기·한글 자동 실행 제거·123개 검사 | [0.4.20 직접 읽기 검증](HWP_NO_LAUNCH_VERIFICATION.md) |
| 과거 HWP 첨부·PDF 변환 구현(0.4.16) | [과거 HWP 입력 검증](HWP_INPUT_VERIFICATION.md) |
| PDF 전체 분석·분과·날짜 출력 | [전체 PDF](FULL_PDF_METADATA_VERIFICATION.md), [분과·날짜](DIVISION_DATE_VERIFICATION.md) |
| 초안 수정·이전 초안 복원·90개 검사·22회 AI 시험 | [채팅 검증](CHAT_REVISION_VERIFICATION.md), [테스트 소스](../tests), [검사 도구](../qa) |
| API 보존 초기화 | [초기화 검증](RESET_VERIFICATION.md) |
| 별첨 제거·분과 제목·파일명 분리 | [출력 양식·제목 검증](REPORT_HEADER_VERIFICATION.md) |
| 승인 저장·한글 결과 | [HWP 입출력](HWP_MEMORY_VERIFICATION.md), [본문·여백](BODY_SPACING_VERIFICATION.md) |
| 소스/배포 EXE의 API 오류 해결 | [API 진단](API_CONNECTION_VERIFICATION.md), [TLS 빌드 훅](../hooks/hook-ssl.py) |
| 단계별 자동 처리시간 | [3회 실측](WORKFLOW_TIMING_VERIFICATION.md) |
| 버전별 개발·검증 이력 | [개발 기록](DEVELOPMENT_TEST_RECORD.md) |

상세 시험 기록은 작성 당시 동작을 설명합니다. 현재 실행 방법은 [README](../README.md)를 기준으로 확인하세요. 검사 건수는 업무 정확도·만족도 수치가 아니며, 자동 처리시간은 사람의 입력·검토시간이나 편집 영상 길이와 구분합니다.

## 저장소 정리

2026-11-02에 실행·빌드·테스트·양식·라이선스는 유지하고 검증 문서를 이 폴더로 옮겼습니다. 과거 기능별 단편 보고서 14개와 과거 버전의 시험 결과 JSON 9개는 현재 트리에서 제거했습니다. 개발 이력과 아래 정리 전 커밋에서 원래 기록을 확인할 수 있습니다. 모델 선정의 실패 응답을 포함한 96회 원자료와 비용 CSV는 그대로 유지합니다.

[정리 전 저장소 전체](https://github.com/munwonshin/ai-inspection-report/tree/2da0327f34efea114891413cfe529234c1b27c70)

이력은 삭제하거나 재작성하지 않았습니다. 이력서·포트폴리오·영상·업무자료·API 키는 이번 정리에 추가하지 않았습니다.
