# AI 현장점검 결과서 자동화 | PM 제품 개선 사례

**반복 업무를 줄이는 도구를 만든 뒤, 자료 변경 시 잘못된 결과서가 승인될 수 있는 위험을 발견해 재검수 기능을 기획·검증한 프로젝트입니다.**

> **PM 관점의 핵심:** 사용자 문제 발견 → 개선안 비교·우선순위 결정 → PRD·사용자 흐름 설계 → 구현·피드백 반영 → 품질 검증 → 출시 판단

**[PM 사례 연구 먼저 읽기](docs/product/PM_CASE_STUDY.md)** · [6단계 실제 UI 시연](docs/product/C1_DEMO.md) · [PRD](docs/product/PRD_PUBLIC.md) · [제품 로드맵](docs/product/ROADMAP_PUBLIC.md)

## 1. 프로젝트와 담당 역할

| 항목 | 내용 |
| --- | --- |
| 배경·사용자 | AI바우처 현장점검 결과서를 작성·검수하는 실무자. 작성자 본인의 업무 경험을 중심으로 문제를 발견 |
| 제품 | 사업계획서(PDF·HWP)·회의록 입력 → AI 초안 → 사용자 검수·직접 수정/채팅 수정 → 승인 → 기존 HWP 양식 저장 |
| 내가 한 일 | 반복 업무 및 승인 위험 분석, MVP 설정, C1/C2/C3 우선순위 비교, PRD·User Story·수용 기준 정의, 기능 구현·검증 결과 검토, 출시 범위 판단 |
| 작업 방식 | 1인 업무 개선 프로젝트. 분석·구현·테스트·문서화에 Codex 등 AI 도구를 활용. 별도 개발·디자인 스쿼드 리딩 경험은 아님 |
| 사용 환경 | Python/Tkinter 기반 Windows 앱, OpenAI API, 한글 COM |

## 2. 사용자 문제와 개선 방향

**첫 번째 문제 — 작성 비효율.** 사업계획서·회의록을 읽고 한글 결과서 양식에 옮기는 작업이 건당 평균 약 60분 걸렸다. 단순 AI 문장 생성이 아니라 **검수·수정·승인·HWP 저장까지** 업무 흐름을 묶어 초기 도구를 만들었다.

**두 번째 문제 — 승인 품질.** 기존 도구는 자료 A로 작성한 본문을 남겨둔 채 자료 B를 첨부해도 재검수를 요구하지 않았다. 편집 내용을 지우면 작업물이 손실되므로, **본문은 보존하되 현재 자료와 다시 대조하기 전에는 저장을 막는 C1 기능**을 선택했다. 실제 운영 사고가 발생했다는 주장이 아니라 코드와 합성 시나리오에서 재현한 위험이다.

![B 자료와 기존 A 본문이 함께 있는 상태에서 재검수 전 저장을 차단하는 C1 UI](docs/images/c1/03-unreviewed-blocked.jpg)

*실제 C1 로컬 앱 화면을 합성 A/B 자료·고정 AI 응답·저장 대역으로 시연. 이 화면은 정식 배포본 또는 실제 HWP 저장 검증 사진이 아니다.* [화면 전체 시연](docs/product/C1_DEMO.md)

## 3. 무엇을 먼저 만들지 결정하다

| 우선순위 | 개선 후보 | 판단 |
| --- | --- | --- |
| **1. C1 재검수** | 자료와 남아 있는 본문이 불일치해 잘못 승인될 위험 | 코드·합성 재현 가능, 승인 경계에서 명확히 검증할 수 있어 먼저 구현 |
| **2. C3 수정 차이 확인** | AI의 수정 내용을 찾는 검수 부담 | 기존 복원 기능으로 일부 대응 가능해 다음 단계로 분리 |
| **3. C2 HWP 저장 복구** | 저장 실패·완료 불명 위험 | 영향은 크지만 장애 빈도 미확인, COM·파일 보호 실환경 검증 부담으로 보류 |

영향도·시급성·개발 부담(각 1~5)을 비교하고 **C1→C3→C2**로 정했다. 점수는 상대적 판단이며 실제 사용자 조사나 ROI 계산이 아니다. [판단 근거](docs/product/DECISION_LOG_PUBLIC.md) · [로드맵](docs/product/ROADMAP_PUBLIC.md)

## 4. 요구사항과 실행

C1 MVP는 **처리 자료 식별 → 변경 안내 → 명시 검토 → 복원·지연 응답 보호 → 승인 전 차단**의 5개 범위로 제한했다. 같은 자료 재첨부나 파일명 변경은 정상 흐름을 유지하고, 본문·자료 내용 변경 후에는 재검수를 요구하도록 구분했다.

- **[PRD·User Story·AC01~AC14](docs/product/PRD_PUBLIC.md)**: 사용자 기대 동작, 예외·저장 조건, 수용 기준
- **[실제 UI·상태 전이 시연](docs/product/C1_DEMO.md)**: 검토 전 차단과 명시 검토 흐름
- **[기능별 백로그](docs/product/PRODUCT_BACKLOG.md)**: 사용자 가치·우선순위·인수 조건·현재 상태

기존 제품에서는 동료의 **날짜 입력 불편 의견**을 듣고 달력 선택 기능을 반영했다. 이는 실제 피드백 반영 사례이며, 별도 C1 인터뷰·사용성 테스트를 진행했다는 의미는 아니다.

## 5. 결과를 무엇으로 검증했는가

| 구분 | 확인된 결과 | 해석 범위 |
| --- | --- | --- |
| **초기 개인 업무 적용** | 본인 업무 3건 이상, 평균 약 **60분→3분(약 95% 단축)** | 개인 적용·자체 측정. 건별 원기록·대조군 없음. **C1 효과가 아님** |
| **C1 미검토 승인 차단** | 같은 합성 조건에서 저장 함수 진입 **18/18→0/18** | 6개 유형×3회. 운영 사고 감소율 아님 |
| **정상 작업 유지** | 정상 저장 오차단 **0/30 유지** | 10개 유형×3회. 실제 사용자 30명이 아님 |
| **수용·회귀 검증** | 신규 **26/26**, 기존 단위 **151/151**, GUI QA **4/4** | 정의한 소스·시험 환경 내 통과 |
| **실제 파일 검증** | 한글 COM 기반 HWP **4개** 저장·재열기·내용/서식 확인, 전체 7쪽 검수 | 합성 업무 자료를 사용한 실제 HWP 검증. 정식 배포 확인과 별개 |

**제품 판단:** 잘못된 승인을 막는 것뿐 아니라 정상 작업을 막지 않는지도 함께 측정했다. 모의 저장 경계의 합성 48회와 실제 HWP COM 시험은 별도 증거이며 서로 합산하지 않는다. [정량 근거](docs/product/EVIDENCE_SUMMARY.md) · [실제 HWP E2E](docs/product/C1_E2E_REVIEW.md) · [품질 판정](docs/product/QUALITY_REVIEW.md)

## 6. 출시 판단과 다음 개선

- **C1 v0.4.27 정식 배포 완료(2026-11-16):** PR #1 main 병합, 실제 배포 EXE 핵심 HWP E2E 통과, 검증한 동일 ZIP 게시·다운로드 해시 확인.
- **별도 미검증:** 다중 한글 버전·상용 환경 안정성·기존 한글 세션 공존·NAS·강제 COM 멈춤 복구. [배포 검증 근거](docs/product/EXE_RELEASE_REVIEW.md)
- **다음 검증:** 제한 사용자에게 재검수 안내 이해도·활성 검수시간을 관찰. 이후 C3 수정 차이 표시, C2 저장 장애 조사 순으로 재평가.

현재 문서 중 [사용자 여정](docs/product/USER_RESEARCH_JOURNEY.md)과 [UX·Figma 제작 명세](docs/product/UX_PROTOTYPE_SPEC.md)는 실제 경험·현재 UI를 구조화한 자료이며, **C1 사용자 인터뷰·Figma 클릭형 프로토타입·사용성 테스트·퍼널 측정은 미실행**이다. [향후 사용자 검증 계획](docs/product/USABILITY_KPI_PLAN.md)에서 별도로 다룬다. [출시 게이트](docs/product/RELEASE_REVIEW_PUBLIC.md)

## 더 깊이 살펴보기

| 궁금한 것 | 문서 |
| --- | --- |
| 왜 이 문제를 발견하고 C1을 선택했나? | [PM 사례 연구](docs/product/PM_CASE_STUDY.md) · [의사결정 기록](docs/product/DECISION_LOG_PUBLIC.md) |
| 사용자 요구를 어떤 기능으로 바꿨나? | [PRD](docs/product/PRD_PUBLIC.md) · [사용자 여정](docs/product/USER_RESEARCH_JOURNEY.md) |
| 화면과 실행 작업은 어떻게 연결되나? | [실제 UI](docs/product/C1_DEMO.md) · [UX 화면 명세](docs/product/UX_PROTOTYPE_SPEC.md) · [백로그](docs/product/PRODUCT_BACKLOG.md) |
| 구현·검증 결과는 재현 가능한가? | [품질 검토](docs/product/QUALITY_REVIEW.md) · [검증 집계](docs/product/EVIDENCE_SUMMARY.md) |
| 남은 사용자 검증과 출시 조건은? | [사용성·KPI 계획](docs/product/USABILITY_KPI_PLAN.md) · [로드맵](docs/product/ROADMAP_PUBLIC.md) |

<details>
<summary>기술 사용·설치 및 개발 기록</summary>

**현재 배포본 v0.4.27과 main에는 C1 재검수 기능이 포함됩니다.** 기존 v0.4.26 배포본도 보존했습니다.

**실행 환경:** Windows 64비트, 한글 COM을 지원하는 한컴오피스, OpenAI API 키 및 인터넷 연결.

- [v0.4.27 Windows ZIP 다운로드](https://github.com/munwonshin/ai-inspection-report/releases/download/v0.4.27/AIInspectionReport-0.4.27-windows-x64.zip) · [릴리스·체크섬](https://github.com/munwonshin/ai-inspection-report/releases/tag/v0.4.27) · [이전 v0.4.26](https://github.com/munwonshin/ai-inspection-report/releases/tag/v0.4.26)
- ZIP을 전체 압축 해제한 뒤 `AIInspectionReport` 폴더의 **바탕화면 아이콘 만들기.cmd**로 실행합니다. API 설정→자료 입력→검수·승인 저장 순서로 사용합니다.
- Python은 별도로 설치하지 않아도 됩니다. `Code → Download ZIP`은 개발용 소스입니다.
- 문서와 회의록 내용이 OpenAI로 전송되며 API 비용이 발생할 수 있습니다. 사용자가 사실·수치를 최종 확인해야 합니다.
- [사용 및 소스 실행·빌드 안내](docs/USAGE.md) · [개발 검증 기록](docs/DEVELOPMENT_TEST_RECORD_PUBLIC.md) · [버전 변경 이력](docs/CHANGELOG.md)

</details>
