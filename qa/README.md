# GUI 검증 스크립트

Windows 소스 실행 의존성을 설치한 후 이 폴더의 스크립트를 실행할 수 있습니다.

- chat_checks.py: 모의 API·HWP로 최초 채팅, 직접 편집, 수정, 오류 보존, 최신 초안만 승인 저장되는지 검사합니다.
- chat_layout_checks.py: 기본·최소 창 크기, 100%·150% 글꼴 배율, 채팅·직접 편집 탭·일반현황 32조건의 배치를 검사합니다. 화면을 가리지 않는 투명 시험 창을 사용합니다.
- ui_checks.py: 기존 채팅·API 오류·NAS 오류·재승인 상태 검사를 수행합니다. API·NAS 장애는 모의 시험입니다.

이 스크립트는 실제 API를 호출하거나 실제 HWP 결과를 만들지 않습니다. 시험 JSON은 이 폴더에 작성합니다. 실제 API 및 한글 검증 범위는 DEVELOPMENT_TEST_RECORD.md를 확인하세요.

- pdf_drop_checks.py: 실제 TkDND 로드, PDF 파일명/드롭 입력 검증, 실패 시 기존 첨부 보존과 버튼 호환성을 확인합니다. 가상 PDF만 임시 생성하며 API/HWP는 호출하지 않습니다.

- pdf_drop_checks.py: 실제 TkDND 파일 첨부, × 해제, 메모리 제거, 재첨부, 원본/초안 보존을 검사합니다. 가상 자료만 쓰며 API/HWP는 호출하지 않습니다.

- pdf_speed_benchmark.py: 기본 가상 PDF 또는 --pdf 경로를 로컬로 비교합니다. API 호출/문서 출력 없이 시간·보존 결과만 표시합니다. pdf_visual_verify.py는 메모리에서 원본과 부분 PDF의 모든 선택 페이지 글자·렌더링을 대조합니다. pdf_baseline.py는 개선 전 대조 함수입니다.

- stream_checks.py: 지연된 모의 스트림으로 경과 초·점진 표시·제목 연결·승인 차단·중단 보존을 실제 Tk 위젯에서 검사합니다. API/HWP 호출은 하지 않습니다.
