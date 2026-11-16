# C1 Windows EXE 배포 검증

2026-11-16 · v0.4.27 · **실제 배포 EXE 검증·main 병합·v0.4.27 정식 배포 완료**

소스 실행 검증과 구분해, GitHub Windows Actions가 만든 실제 onedir EXE를 내려받아 실행했다. 테스트 후 ZIP/EXE 바이트가 그대로임을 확인했으며, 이 파일을 재빌드 없이 승격했다. PR #1을 main에 병합하고 정식 Release를 게시했다. 공개 ZIP을 다시 내려받아 ZIP CRC와 ZIP·내부 EXE의 SHA-256 일치를 확인했다.

- [v0.4.27 정식 Release·다운로드](https://github.com/munwonshin/ai-inspection-report/releases/tag/v0.4.27)
- [병합 PR #1](https://github.com/munwonshin/ai-inspection-report/pull/1), 병합 커밋 `7f339d517a7647e25147fbc1ff75ba56d5c81cf3`
- [동일 파일 게시 실행](https://github.com/munwonshin/ai-inspection-report/actions/runs/43782553378): publish PASS, build SKIPPED
- v0.4.26 ZIP·체크섬 asset ID와 SHA-256이 이전 기록과 동일함을 재확인했다.

| 필수 게이트 | 실제 결과 |
| --- | --- |
| Windows 빌드·소스/번들 일치 | PASS, C1 review·probe·PDF native를 포함한23모듈 |
| 실제 EXE GUI/TLS/PDF 런타임 | PASS, TkDND 2.9.5, PDF 준비 오류 없음 |
| 실제 EXE C1 흐름 | A 저장, B 미검토 차단·본문 보존, B 명시 검토·저장 PASS |
| 실제 실패·동명·파일명 변경 | 기존 HWP 해시 보존·실패 시 성공 표시 해제·새 파일명 저장 PASS |
| 실제 EXE HWP 재열기 | COM Open4개·내용/서식 일치·장문60개 표식·4쪽 PASS |
| 기존 단위 / 수용 / GUI QA | 151/151·제외0 / 26/26 / 4/4 |
| 동일 합성16×3 | 미검토 진입0/18·정상 오차단0/30 |

API·자격증명 및 테스트용 C1 확인 대화 응답은 대역이다. 실제 bundled App 버튼·review·exporter·동일 EXE의 worker·한글 COM을 실행했다. 보안 파일 접근 승인은 사용자가 직접 수행했으며 승인 대기를 성능 결함/개선으로 표현하지 않는다. 기존 사용자 한글이 없는지 확인하고 새 HWND/PID가 시험 소유임을 확인한 세션만 사용했다.

## 파일 동일성과 출처

- 빌드 소스: `be34dfe98954227660ae55c062f7be4e9f44d986`
- [Windows 빌드 실행](https://github.com/munwonshin/ai-inspection-report/actions/runs/43779042677)
- ZIP SHA-256: `a2babeb229f8aa8c5f42c0a8ccb1ea49dbc21c41c09e6aa2a2ee534f5b1ef5e4`
- EXE SHA-256: `2841333ac8baf363c0d7998612b7eeb5933e41835fc31f9cbc8918b6a7b73512`
- [기계 판독 검증](EXE_RELEASE_EVIDENCE.json) · [배포 승인 manifest](../../release/approved.json)

기존 실패·Baseline·원시 증거57개와 이번 무효 회차(151개 assertion은 통과했지만 시험 중 소스 변경)는 보존했다. 소스가 고정된 재시험151개는 통과했다. API 키·실제 회사 자료·NAS를 사용하지 않았고 raw로그·HWP·사용자 경로는 공개하지 않는다.

## 해석과 별도 범위

이 기록은 **C1 개발·소스 품질 검증에 더해 실제 배포 EXE 핵심 E2E까지 완료**했다는 근거다. 모든 상용 환경의 무결함 보장이나 실제 AI 응답/운영 성과 검증은 아니다. 다중 한글 버전·기존 업무 한글 세션 공존·NAS·강제 COM 멈춤/복구는 별도다. v0.4.26 자산은 유지한다.
