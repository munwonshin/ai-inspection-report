# v0.4.28 최종 검증과 배포 검토

2026-11-17 · **소스·실제 배포 EXE 검증·main 병합·v0.4.28 정식 배포·공개 다운로드 동일성 확인 완료**

이 버전은 C1 검수 보호를 유지하면서 저장 작업 제한·실패 후 재시도·PDF 호환 대체·UI 책임 분리를 추가했다. v0.4.27의 승인이나 체크섬을 이번 시험 결과로 재사용하지 않았다.

| 검사 | 이번 버전 실제 결과 |
| --- | --- |
| 기존 단위 + 신규 저장/PDF | **163/163**, 기존151 + 신규12, 제외0 |
| C1·저장 UI 수용 | **28/28**, 기존26 + timeout 후 재시도·동명 안내2 |
| GUI QA / 측정기 | **4/4 / 8/8** |
| 동일 합성16×3 | **48 PASS**, 미검토 저장 진입0/18·정상 오차단0/30 |
| 실제 COM 소스 복구 시험 | 지연 주입→제한 초과→UI 해제→같은 이름 재시도, 재입력 실패→재시도 PASS |
| 최종 Windows CI·번들 검사 | 단위163개·28모듈 소스 일치·GUI/TLS/PDF 런타임 PASS |
| 실제 EXE 핵심 흐름 | A 저장·B 변경 후 차단/본문 보존·검토 후 저장·동명 보호·파일명 변경·60문단 PASS |
| 실제 EXE 복구 | 제한 초과 시 소유 프로세스·임시파일 정리, 실패 후 편집 유지·재시도 PASS |
| 실제 EXE HWP Open | **6파일** 실제 COM 재열기·내용/서식·기존 출력 해시 유지 PASS |

합성48회는 API/저장을 대역으로 둔 저장 함수 진입 시험이며 실제 COM 회차와 합산하지 않는다. 실제 COM·EXE 시험도 합성 자료와 테스트 대화 응답을 사용했고 API·키 접근은 하지 않았다. Windows11·한글2018(10.0.0.7888)에서 실행했다. 파일 접근 확인은 사용자가 직접 처리하며 자동 승인·보안 정책 변경은 없다.

지연 시험은 **실제 COM HWP 재입력 직전에 의도적으로 지연/실패를 넣은 시험**이다. 시험에서는20초 override로 정리·재시도를 관찰했고 제품 기본값은120초다. 임의의 실제 COM 교착·다중 한글 버전·사용자 세션 공존·NAS·OS 호출 멈춤을 모두 검증했다는 의미는 아니다. 소유권 확인 전에 DispatchEx가 멈춘 경우에는 사용자 한글 보호를 위해 미확인 프로세스를 강제 종료하지 않는다. [동작과 안전 경계](../SAVE_JOB_RECOVERY.md)

## 새 후보의 출처·동일성

- 소스: `25fa1e8c09e3db7328e0bb962e4be8b3ec37cee5`
- [Windows 빌드](https://github.com/munwonshin/ai-inspection-report/actions/runs/44026313371) · 28모듈 컴파일 코드 일치
- ZIP SHA-256: `7a07be0d5ef3b3508a62b95232f4e6664bafb503c64d32d106a2acee15dd5019`
- EXE SHA-256: `a519b3389f10673920b69b2e57c2dbb788a494a39c0ff5804c198875d31b8b8a`
- [새 승인 manifest](../../release/approved.json) · [기계 판독 결과](V028_QUALITY_EVIDENCE.json)

검증한 이 후보를 **재빌드 없이 동일 파일로 게시**했다. 공개 URL의 ZIP과 SHA256SUMS.txt를 다시 내려받아 ZIP CRC·ZIP SHA-256·내부 EXE SHA-256 일치를 확인했다. v0.4.26·v0.4.27 자산의 ID·체크섬도 게시 전과 동일했다.

- [v0.4.28 정식 Release·다운로드](https://github.com/munwonshin/ai-inspection-report/releases/tag/v0.4.28)
- [PR #2](https://github.com/munwonshin/ai-inspection-report/pull/2), main 병합 커밋 `442095be7ecd6818eee5ddef7960cea82727700e`
- [동일 파일 게시 실행](https://github.com/munwonshin/ai-inspection-report/actions/runs/44027903375): publish PASS, build SKIPPED
- 과거 승인 원본은 [v0.4.27 manifest](../../release/history/v0.4.27-approved.json)·기존 Git 이력에 보존했다.

## 실패·무효 기록

- 최초 신규 PDF 대체 테스트는 Mock fixture 구성 오류1개로 실패했다. fixture를 수정하고 기준을 유지해 재시험163개를 통과했다.
- 의존성 폴더 읽기 제한으로 시작하지 못한 최초 회차와, 시험 중 소스 변경으로 개별26개 통과에도 무효인 수용 회차는 보존했다.
- 복구 시험 실행기의 실제 저장 참조 순서 오류를 수정한 후 실제 COM 지연/실패/재시도4분기를 통과했다.
- **첫 EXE 후보는 동명 파일을 보호했지만 안내 문구가 일반 오류로 표시돼 FAIL**이었다. FileExistsError를 경로 노출 없는 명확한 안내로 처리하고 신규 수용 검사를 추가했다. 이전 후보는 게시하지 않았으며 수정 소스로 새 EXE를 빌드해 전체10분기·6파일 Open을 통과했다.

원시 로그·합성 HWP·호스트 경로·PID는 로컬 보존하며 공개하지 않는다. 실제 업무 사고 감소·만족도·AI 품질을 측정한 결과는 아니다.

## 재현

`qa/c1_native/run_native_units.py --expected-tests 163`, `qa/c1_acceptance/run_checks.py`, `qa/c1_baseline/run_regressions.py`, `qa/c1_baseline/run_baseline.py`의 기존16×3 계약, 새 `qa/c1_native/run_recovery.py`를 새 격리 출력 폴더에서 실행한다. 의존성과 실행 방법은 [네이티브 QA](../../qa/c1_native/README.md)를 따른다. 실제 EXE는 합성 fixture 준비 후 `--c1-frozen-check`로 실행하고6파일 Open의 사용자 접근 승인을 확인한다. **존재하지 않는 새 시험 폴더만 사용**한다.
