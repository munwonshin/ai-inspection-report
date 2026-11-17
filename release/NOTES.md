Windows x64 **v0.4.28 — 저장 작업 제한·복구와 PDF 호환성 보강**

- HWP 작업 기본120초 제한, 이번 작업 소유 Python/한글만 정리하고 UI 잠금 해제·수정 내용 보존·재시도
- 최종 게시를 부모에서만 수행해 시간 초과 뒤 늦은 저장 방지, 기존 파일 no-replace·재열기/내용 검증 유지
- pypdf 버전 확인 후 내부 API 사용, 내부 API 불가 시 공개 API 대체
- 기존 화면을 유지하며 UI 비동기·승인 저장 흐름을 별도 모듈로 분리
- 동명 사전 검사 오류 안내를 명확히 표시하고 경로 노출 방지

새 소스·후보에서 단위163/163·수용28/28·GUI4/4·동일 합성48회(0/18·0/30), 실제 EXE 지연·실패 후 재시도와6개 HWP Open·내용/서식 검증을 통과했습니다. 테스트용 지연은20초 제한 override이며 기본120초입니다. 모든 실제 교착을 재현한 시험은 아닙니다. API·자격증명·테스트 대화 응답은 대역이며 보안 접근 승인은 사용자가 직접 처리합니다.

ZIP 전체를 풀고 폴더 안 `바탕화면 아이콘 만들기.cmd`로 실행하세요. EXE만 옮기지 마세요. Windows64비트·한글 COM 지원 한컴오피스가 필요합니다. 기존 파일은 덮어쓰지 않으며 미검토 상태에서 저장할 수 없습니다.

미확인 소유권의 한글은 강제 종료하지 않습니다. 다른 한글 버전·기존 사용자 세션 공존·NAS·실사용 성과는 별도 미검증입니다. 이전 v0.4.26·v0.4.27 자산은 보존합니다.

[검증 결과·범위](https://github.com/munwonshin/ai-inspection-report/blob/main/docs/product/V028_QUALITY_REVIEW.md) · [저장 동작 안내](https://github.com/munwonshin/ai-inspection-report/blob/main/docs/SAVE_JOB_RECOVERY.md)
