# 공고 줄 간격 수정 검토

## 결과와 범위
- 대상: 프로젝트 JD에서 생성한 공고문의 빈 줄과 하위 항목 들여쓰기 보존.
- 기준: 원격 `/home/chaconne/exdigm-debug`, 시작 HEAD `6ac315e930880406f6f7f9d489322b07b85e380f`, 운영·개발 작업 트리 모두 clean.
- 조사한 공고: 화장품영업 (관리자급), 비즈니스피플 `BR260911A00535`.
- 운영 원문은 `scripts/debug_workspace.sh shell-readonly`로만 조회했다. 저장 원문·운영 공고를 수정하지 않았다.

## 확인된 원인
1. 저장된 원문에는 6·17번째 줄의 빈 줄과 하위 항목 들여쓰기가 있다.
2. 비즈니스피플의 `_set_namo`는 `if line.strip()`으로 빈 줄을 제거한다. 피플앤잡에도 같은 구현이 있다.
3. 비즈니스피플 공개 본문 DOM은 빈 문단이 없고 문단 여백 0px, white-space normal이다. 일반 앞 공백도 들여쓰기로 표시되지 않는다.
4. 생성 서비스는 원문 내부 줄바꿈을 지우지 않고 내부 미리보기는 whitespace-pre-wrap을 사용한다. 이번 수정은 생성 지침을 변경하지 않는다.

## 수정 계획과 구현
- 최소 구현 게이트 2단계: 기존 Exdigm `_html`의 빈 문단·앞 공백 보존 방식을 재사용한다.
- `auto_posting/common.py`에 기존 변환을 이동한다.
- `auto_posting/sites/businesspeople.py`, `peoplenjob.py`, `exdigm.py`가 같은 변환을 호출한다.
- `tests/test_auto_posting_browser_runtime.py`에 두 사이트의 LF·CRLF, 빈 줄, 연속 빈 줄, 들여쓰기, HTML 문자 보존 검사 4개를 추가한다.
- 보호 조건: 저장 원문, 공고 생성 프롬프트, 사이트 편집기 호출·저장·로그인·재시도·게시 권한은 유지한다. 기존 검사와 기대값을 변경하지 않는다.

## 검증
- 변경 전 관련 검사 91개 통과. 변경 후 95개 통과.
- 다른 작업에서 별도로 추가한 검사를 포함한 최종 같은 검사 묶음: 98개 통과.
- 고정 보호 기준 18개 파일 보존, 보호 검사 194개 통과.
- Django check, 변경 코드 Ruff, git diff --check 통과.
- code_knowledge catalog_update: current, broken references 없음.
- 같은 실제 공고를 변경 전·후 `_set_namo`에 넣고 편집기 전달 HTML을 비교: 빈 문단 0→2개, 하위 항목 들여쓰기 7개 보존.
- 비교 HTML은 실제 변환 함수의 출력이다. 외부 사이트의 수정 후 화면이나 저장 성공 증거가 아니다.
- 코드 리뷰: 이번 5개 파일 및 직접 호출자 범위에서 승인된 finding 없음.

## 미완료·재개 경계
- 확대 실행한 작업자 검사에서는 11건 실패, 2건 통과 뒤 실행을 중단했다. 개발의 dry-only 경계와 기존 test/publish 기대값 충돌, 알림·작업 결과 기대 불일치가 발생했다. HTML 변환 전 단계의 실패이며 이 검사를 통과시키기 위해 운영 차단을 완화하지 않았다. 전체 작업자 검사 통과를 주장하지 않는다.
- 외부 사이트의 실제 `autoposting --mode dry` 및 저장 후 화면 검증은 수행하지 않았다. 개발 환경에는 운영 채용사이트 자격증명을 연결하지 않았다.
- 재발 판정: 변환 함수의 빈 줄 삭제 원인은 닫힘. 외부 편집기 저장 후 보존은 미검증.
- 진행 중 다른 작업의 `auto_posting/sites/saramin.py`, `projects/views/project.py`, `tests/test_auto_posting_updates.py` 변경은 보존했다. 이번 수정 범위로 포함하거나 커밋하지 않았다.
- 이번 작업은 커밋·운영 배포·기존 외부 공고 갱신을 실행하지 않았다.
- 재개: 작업 트리의 다른 작업 상태 확인 → 공식 사이트 검증과 승인 범위 확인 → 검증된 변경 커밋 → 별도 승인된 공식 prod 배포 → 비즈니스피플 기존 공고 수정 경로로 갱신 → 공개 본문 빈 문단·들여쓰기 및 공고번호·지원자 보존 확인.
- 배포 승인 원천: GBrain `default:project/exdigm-deploy-workflow`의 “구현·검증 승인은 운영 배포 승인을 대신하지 않는다.”
- 외부 게시 승인 원천: `.agents/skills/auto-posting/SKILL.md`의 “사용자의 명시 지시 없이 publish 하지 않는다.”

## 승인 후 운영 반영 — 2026-09-11 23:19 KST
- 사용자가 운영 반영 및 해당 공고 갱신을 명시적으로 승인했다.
- 승인된 5개 파일만 커밋: `573a50755b91e6483fe521e8a596a857d693413f`.
- 다른 작업의 3개 파일을 stash `4f14aa7390d24cb52ee2c1ddd4823c02a626b314`에 보관하고 배포 후 복원했다. 복원 전후 diff의 SHA256 `8e3e60ef7de0b12c222e09bc929937f7392fc422aed2d0bb6122455eebc726ef` 일치.
- 배포 대상만 분리한 상태의 관련95 및 보호194 검사 통과. 공식 prod는 23:19:27 KST exit0, `prod ok 573a5075`.
- GitHub main·운영 main·debug HEAD·실행 앱 `.source-commit` 일치. 운영 clean. 개발에는 복원한 다른 작업의 3개 변경만 남는다.
- 이미지 `exdigm_app:20260911231640`, digest `sha256:6c6a8ef033ef3a87e3cb2354fbbbba83dbc27606108351539c10a8c46809b266`. 이미지 문서 계약 및 앱·SSE·notification 업데이트 완료. 서비스5개 1/1, worker/support11 active/jobs0/drain off, HTTPS200.

## 기존 공고 갱신 중단 근거 — 23:20 KST
- 공식 운영 명령 `manage.py autoposting --site businesspeople --action update --ref BR260911A00535 --mode dry --payload runtime/auto_posting/payloads/aaeb64a5-89f5-41df-b897-7a2b636c13f7/businesspeople.json` 실행.
- payload는 해당 프로젝트·최근 성공 site_run과 일치하고 현재 posting_text로 시작함을 먼저 확인했다.
- run_id `20260911232008`: 로그인은 기존 세션 재사용으로 성공. 채용 중 목록에서 해당 공고의 수정 버튼을 찾지 못해 30초 후 실패. 본문 입력·저장 단계에 도달하지 않음.
- 공개 공고를 새로 읽으니 접수마감, 종료일2026-09-10, “본 공고는 마감되었습니다”, 수정 버튼 없음. 관리 화면 채용 중 목록에서도 대상이 없다. 누가 마감했는지는 확인하지 않았다.
- 이 실행은 dry이며 마감 호출이 없다. DB 공고 원문 해시 `58facd3f7664804ec2f6f5202cc3daabbc355d123d18084d99f6f04d6f4d1a55`, 같은 외부번호, 지원자0, last_run 불변을 확인했다.
- 증거: 운영 `runtime/auto_posting/evidence/businesspeople/20260911232008/result.json` 및 `update-failure.png`. 로컬 사본 `artifacts/businesspeople-update-failure.png`.
- 현재 결론: 코드 운영 반영 완료. 마감된 외부 공고의 갱신 및 외부 저장 후 간격 검증은 미완료. 새 공고로 다시 게시할지 사용자 선택을 요청한 상태다.
