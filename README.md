# AI 현장점검 결과서 자동화 | PM Case Study

**반복적인 결과서 작성 문제를 해결한 뒤, 자료 변경 시 잘못된 내용이 승인될 수 있는 위험을 발견해 C1 재검수 기능을 기획·개선·정식 배포한 프로젝트입니다.**

**v0.4.27 정식 출시 · 2026-11-16** · [Windows Release](https://github.com/munwonshin/ai-inspection-report/releases/tag/v0.4.27) · [PM 사례 연구](docs/product/PM_CASE_STUDY.md) · [실제 UI 시연](docs/product/C1_DEMO.md)

## 1. 프로젝트 개요와 담당 역할

| 항목 | 내용 |
| --- | --- |
| **사용자·문제** | AI바우처 현장점검 결과서를 작성·검수하는 담당자. 본인의 업무 경험에서 작성 비효율과 승인 위험 발견 |
| **제품 흐름** | PDF·HWP 사업계획서/회의록 → AI 초안 → 사람 검토·직접/채팅 수정 → 승인 → 기존 HWP 양식 저장 |
| **내 역할** | 문제·사용자 목표 정의, 개선안 우선순위, MVP·PRD·수용 기준 설정, 구현·QA 검토, 출시 판단 |
| **진행 방식** | 1인 업무 개선 프로젝트. Codex를 활용해 분석·구현·테스트를 진행했으며 별도 개발·디자인팀 리딩 경험은 아님 |

## 2. 사용자 문제를 발견하고 해결 방향을 정하다

**처음 해결한 문제 — 작성 비효율.** 사업계획서와 회의록을 확인하고 한글 결과서에 옮기는 데 건당 약 60분이 걸렸다. AI 초안만 만드는 대신 **자료 입력부터 사람의 최종 검토·HWP 저장까지** 연결하는 업무 도구를 구현했다. 초기 본인 업무 3건 이상에서 평균 약 **60분→3분(95% 단축)**을 자체 측정했다. 건별 원기록·대조군은 없어 다른 사용자에게 일반화하지 않는다.

**다음에 발견한 문제 — 잘못된 승인 위험.** 자료 A로 작성한 초안을 남겨둔 상태에서 자료 B를 첨부해도, 기존 제품은 새 자료와 이전 본문의 재검토를 요구하지 않았다. 이 위험은 **기존 코드와 합성 사례로 확인**했으며 실제 제출 사고가 발생했다고 주장하지 않는다.

> **핵심 제품 판단:** 자료 변경 시 본문을 삭제하면 사용자의 편집물이 사라지고, 그대로 승인하면 다른 자료의 내용이 남을 위험이 있다. 따라서 **본문은 보존하되 현재 자료를 다시 검토하기 전에는 저장을 차단**하는 C1을 설계했다.

![자료 B를 첨부한 뒤 이전 A 본문이 남아 있어 재검수 전 저장을 차단하는 실제 C1 로컬 UI](docs/images/c1/03-unreviewed-blocked.jpg)

*개인정보 없는 합성 A/B 자료와 고정 AI 응답으로 실행한 실제 C1 로컬 화면. 이미지 자체는 배포 EXE 또는 실제 HWP 저장 시험 결과가 아니다.* [전체 6단계 UI 흐름](docs/product/C1_DEMO.md)

## 3. 무엇을 먼저 해결할지 결정하다

| 개선 후보 | 선택·보류 이유 | 결과 |
| --- | --- | --- |
| **C1 · 자료 변경 후 재검수** | 승인 위험을 재현했고 제한된 범위에서 오류 차단·정상 업무 보존을 함께 검증 가능 | **v0.4.27 출시 완료** |
| **C3 · AI 수정 차이 확인** | 검수 부담을 줄일 수 있지만 기존 초안 복원 기능으로 일부 대응 가능 | 후속 후보·미착수 |
| **C2 · HWP 저장 복구** | 영향이 크지만 실제 장애 빈도와 COM·파일 보호의 안전한 복구 조건 미확인 | 후속 후보·미착수 |

영향도·시급성·개발 부담을 상대 평가해 **C1→C3→C2**로 결정했다. 이는 실측 ROI나 사용자 설문 점수가 아닌 제품 위험과 검증 가능성에 따른 판단이다. [의사결정 기록](docs/product/DECISION_LOG_PUBLIC.md) · [제품 로드맵](docs/product/ROADMAP_PUBLIC.md)

## 4. 요구사항을 제품으로 연결하다

- **목표:** 기존 작성 내용은 잃지 않으면서, 변경된 자료의 검토가 끝나기 전에는 저장되지 않도록 하기
- **MVP:** 처리 자료 식별 → 변경·재검수 안내 → 명시 검토 → 복원·지연 응답 보호 → 승인 전 차단
- **완료 기준:** 5개 User Story를 14개 수용 기준(AC01~AC14)에 연결하고, 잘못된 저장 차단뿐 아니라 정상 저장이 막히지 않는지도 검사
- **실행:** Windows/Tkinter와 기존 HWP COM 양식을 유지하며 개발·실제 UI·회귀 검증·배포로 연결

**실제 사용자 피드백 반영 사례:** 기존 제품에서 동료가 날짜 입력이 불편하다는 의견을 전달해 **달력 선택 기능**을 추가했다. 이는 실제 기능 변경 경험이지만 C1 사용자 인터뷰나 사용성 효과 측정 사례는 아니다.

[PRD·Goals·User Story·수용 기준](docs/product/PRD_PUBLIC.md) · [기능 백로그](docs/product/PRODUCT_BACKLOG.md) · [PM 사례 연구 상세](docs/product/PM_CASE_STUDY.md)

## 5. 결과를 검증하고 출시하다

| 검증 대상 | 결과 | 증거 범위 |
| --- | --- | --- |
| **초기 작성 효율** | 개인 업무 평균 **60분→3분** | 본인 업무 3건 이상 자체 측정. **C1 개선 효과와 별개** |
| **C1 승인 보호** | 미검토 저장 함수 진입 **18/18→0/18**, 정상 저장 오차단 **0/30 유지** | 16개 합성 시나리오×3회=48회. 운영 사고율 아님 |
| **품질 검증** | 수용 **26/26**, 기존 단위 **151/151**, GUI QA **4/4** | 정의된 기능·회귀 검증 |
| **실제 Windows EXE** | HWP 저장·재열기·내용/서식·60문단 장문·동명 파일 보호 PASS | 합성 업무 자료, 한글 COM 기반 핵심 E2E |
| **정식 출시** | 검증된 동일 ZIP을 재빌드 없이 **v0.4.27로 게시**, 공개 파일 해시·압축 무결성 확인 | 2026-11-16 GitHub Release |

**판단 기준:** 기능 테스트 통과와 실제 사용자 가치 입증은 다르다. C1은 정식 배포됐지만 **실사용자의 안내 이해도·추가 검수시간·운영 사고 감소율**은 아직 측정하지 않았다.

[EXE 배포·무결성 근거](docs/product/EXE_RELEASE_REVIEW.md) · [품질·실패 기록](docs/product/EVIDENCE_SUMMARY.md)

## 6. 회고와 다음 제품 판단

이 프로젝트에서 가장 중요했던 선택은 **더 많은 기능을 만드는 대신, 기존 작업물을 보호하면서 잘못된 최종 승인을 막는 작은 범위부터 해결한 것**이다. 재검수 기능이 정상 업무까지 차단하지 않도록 반대 지표도 함께 확인했고, 소스 검증 이후 배포 EXE를 별도로 검증해 정식 출시했다.

**Released · C1 v0.4.27 → Now · 사용자 검수 부담·지원 환경 검증 → Next 후보 · C3 → Later 후보 · C2**

향후 제한된 실무자 관찰을 통해 재검수 안내 이해도와 활성 검수시간을 확인하고, 실제 장애·검수 부담의 근거에 따라 다음 우선순위를 재평가할 계획이다. **C1 사용자 인터뷰·사용성 테스트는 미실행**, 다중 한글 버전·기존 세션 공존·NAS·강제 COM 멈춤 복구도 별도 미검증이다.

[로드맵·의존성·리스크](docs/product/ROADMAP_PUBLIC.md) · [사용성·KPI 측정 계획](docs/product/USABILITY_KPI_PLAN.md)

<details>
<summary>상세 문서 및 설치·개발 안내</summary>

**기획·검증:** [PM 사례 연구](docs/product/PM_CASE_STUDY.md) · [PRD](docs/product/PRD_PUBLIC.md) · [사용자 여정·향후 조사 설계](docs/product/USER_RESEARCH_JOURNEY.md) · [UX 화면 명세](docs/product/UX_PROTOTYPE_SPEC.md) · [의사결정 기록](docs/product/DECISION_LOG_PUBLIC.md) · [실제 HWP E2E](docs/product/C1_E2E_REVIEW.md) · [출시 검토](docs/product/RELEASE_REVIEW_PUBLIC.md)

**실행 환경:** Windows 64비트, 한글 COM 지원 한컴오피스, OpenAI API 키 및 인터넷 연결.

- [v0.4.27 Windows ZIP](https://github.com/munwonshin/ai-inspection-report/releases/download/v0.4.27/AIInspectionReport-0.4.27-windows-x64.zip) · [릴리스·체크섬](https://github.com/munwonshin/ai-inspection-report/releases/tag/v0.4.27) · [이전 v0.4.26](https://github.com/munwonshin/ai-inspection-report/releases/tag/v0.4.26)
- ZIP 전체를 압축 해제한 뒤 `AIInspectionReport` 폴더에서 **바탕화면 아이콘 만들기.cmd**를 실행합니다. Python 별도 설치는 필요하지 않습니다.
- 업무 문서를 OpenAI API에 전송하며 비용이 발생할 수 있으므로 정보 취급 기준을 확인하고 최종 사실·수치를 사람이 검수해야 합니다.
- [사용·빌드 안내](docs/USAGE.md) · [개발 검증 이력](docs/DEVELOPMENT_TEST_RECORD_PUBLIC.md) · [버전 변경 이력](docs/CHANGELOG.md)

</details>
