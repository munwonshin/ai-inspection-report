# C1 네이티브 합성 검증 재현

Windows·한글 COM·Python3.12와 requirements의 고정 의존성으로 실행한다. 모든 출력은 **존재하지 않는 새 폴더**를 사용하며 기존 결과를 삭제/덮어쓰지 않는다. `records/`는 공개하지 않는다. 실제 키·업무 자료·NAS는 사용하지 않는다.

## 실제 저장 E2E

```powershell
python -B qa/c1_native/run_e2e.py --deps-dir <DEPS> --output qa/c1_native/records/new-e2e
```

공개 합성 A/B fixture와 60문단을 생성해 실제 Tk 검토/승인 버튼→원본 exporter/worker→실제 COM으로 HWP4개를 만든다. API·자격증명·테스트 대화상자 응답은 모의한다. 내부 검토 permit 직접 설정이나 저장 대역은 사용하지 않는다. worker.py는 새 COM HWND/PID를 확인하는 시험 계측이며 제품 보호를 대체하지 않는다. 기존 한글이 있으면 활성화를 거절한다.

## 별도 COM Open·내용/서식

```powershell
python -B qa/c1_native/measure_open.py --deps-dir <DEPS> --input-root qa/c1_native/records/new-e2e --output qa/c1_native/records/new-open
```

4개 최종 파일을 새 COM 세션3회에서 Open하고 내용·서식·해시를 대조한다. **사용자가 시험용 파일 접근 승인창을 직접 확인·승인해야 한다.** 보안 승인 자동화/우회는 하지 않는다. 호출 시간에는 승인 대기가 포함되므로 성능 KPI로 해석하지 않는다. 60초 경고/전체120초 감시 종료가 발생하면 회차를 미완료로 보존하고 자식 상태·소유 로그를 확인한다. 자동 강제 종료·재시도하지 않는다.

## 네이티브 기존 검사와 오프라인 수용/QA

```powershell
python -B qa/c1_native/run_native_units.py --deps-dir <DEPS> --output qa/c1_native/records/new-units
python -B qa/c1_acceptance/run_checks.py --deps-dir <DEPS> --output qa/c1_acceptance/records/new-checks
python -B qa/c1_baseline/run_baseline.py --suite C1-BL-v1 --repeats 3 --deny-network --mode candidate --review-hook qa.c1_acceptance.adapter:invoke_review_ui --deps-dir <DEPS> --output qa/c1_acceptance/records/new-core48
python -B qa/c1_baseline/run_regressions.py --deps-dir <DEPS> --output qa/c1_acceptance/records/new-regressions
python -B qa/c1_acceptance/run_local_qa.py --deps-dir <DEPS> --output qa/c1_acceptance/records/new-pdf
```

첫 명령은 native ShellLink/IStorage를 포함한 원래151개이며 실제 Hancom 활성화는 차단한다. 실제 바탕화면·설치 경로는 합성 fixture로 대체하고 원래 CMD20초 제한을 유지한다. 수용은26개, 비교는동일16×3회다. 오프라인 regressions는 COM 차단 때문에147통과+4제외가 범위이므로 네이티브151통과와 혼합하지 않는다. GUI QA4와 harness8도 그 실행기에 포함된다.

실제 한글 전체 페이지 렌더는 로컬 보존한 원본 시험 스냅샷에서 CreatePageImage를 사용했다. 공개 PNG는 [실제 E2E](../../docs/product/C1_E2E_REVIEW.md)에 있다. 파일 접근 승인이 포함된 소스 기능 검증이며 배포 EXE·상용 환경·기존 한글 공존·강제 멈춤 복구는 별도다.
