# 잡코리아 게시 실패 해결 — 2026-09-14

## 결과

완료. 사용자가 지정한 프로젝트의 잡코리아 게시 재시도 1건이 성공했다. 2026-09-14 12:40:58 KST에 실행 장부가 succeeded로 끝났고, 원래 프로젝트 화면의 다섯 사이트가 모두 게시 완료로 표시된다. 공식 잡코리아 목록에서도 같은 제목의 공고 49984616 한 건을 확인했다.

- 프로젝트: e0a75269-3c08-4e23-876e-9a081d81d08b.
- 프로젝트 화면: https://office.exdigm.com/projects/e0a75269-3c08-4e23-876e-9a081d81d08b/edit/
- 공개 공고: https://www.jobkorea.co.kr/Recruit/GI_Read/49984616?Oem_Code=S1&PageGbn=HH
- 외부 제목: 산업/생활용 수세미 제조업체-생산설비 유지보수·공정관리자(과장급).
- 자동 게시 실행: 1aef5916-a239-499f-9a56-65806bd5d0de.
- 사이트 실행: 62d1b86c-b0b9-4c18-901f-a9375ff81fd3.
- 엔진 run_id: 20260914124023. 결과 submitted/published true, deleted false, reference_error 없음.
- 증거: /home/chaconne/exdigm/runtime/auto_posting/evidence/jobkorea/20260914124023/result.json 및 같은 디렉터리의 06-published.png.
- 추가 사용자 조치나 남은 게시 재시도 없음.

## 승인과 시작 상태

- 사용자 요청: 이 프로젝트의 게시 실패 해결. 이후 실제 공고·회사 정보를 기존 AI로 검증, 운영 배포, 잡코리아 1건 게시 재시도를 명시적으로 승인했다.
- 최초 실제 데이터 AI 검증 명령은 자동 승인 심사에서 거절됐지만, 명시 승인 후 같은 공식 경로로 수행했다. 현재 차단 사유가 아니다.
- 서버: chaconne@49.247.202.197. 운영 /home/chaconne/exdigm main, 개발 /home/chaconne/exdigm-debug detached.
- 시작 운영 d7a6f905, 개발 1342df3c 모두 clean. 개발의 기존 문서 이전 커밋을 보존했다.
- 보호 범위: 기존 네 사이트의 상태·공고번호·last_run, 원본 공고문·담당자·회사명 비공개·급여 협의·기존 로그인 및 게시 승인 경계.
- 변경 범위: projects/services/auto_posting_workflow.py, auto_posting/sites/jobkorea.py, tests/test_auto_posting_failed_site_payloads.py.

## 확인한 원인과 수정

1. 회사 업종 변환 누락
   - 기존 두 실패의 오류: jobkorea company industry cannot be mapped.
   - 최신 기존 site_run f6d2f3da-d79c-4c50-9c64-f8cf7d242be5, parent 4b16c82a-6145-4db8-9ade-92fbd1506265. 10:58:47–11:00:17 KST에 브라우저 엔진 전 입력 생성에서 실패했다.
   - 회사의 제조/기타는 정상 내부 선택값이나 JobKorea 변환표에 없었다. 공식 shell-readonly의 exdigm_debug_ro / exdigm / transaction_read_only on에서 같은 오류를 재현했다.
   - 기존 표로 결정되지 않는 입력은 기존 AI 변환과 검증·수정 루프 안에서 회사 사업에 맞는 확인된 업종을 선택하도록 했다. 회사 설명을 제공하고 option_id와 option_label을 기존 정본 표에 대조한다. 없는 항목은 실패로 처리한다.
   - 기존 매핑과 세부 태그는 우선 유지한다. 제조업을 한 업종으로 고정하거나 회사별 예외를 만들지 않았다.
   - 실제 선택은 섬유·의류·패션. 잡코리아 공개 기업정보 https://www.jobkorea.co.kr/company/44704134 와 회사의 수세미·부직포 사업 맥락에 부합했다.
2. 제목 길이 계약 누락
   - 최초 dry 20260914122126은 검증용 [DRYRUN] 접두어가 붙어 제목이 잘렸다. 접두어 제거 후 20260914122747에서도 실제 제목이 잘렸다. 따라서 접두어만이 원인이라는 최초 설명은 불완전했다.
   - 두 실제 입력의 잘린 결과는 ASCII 1/비ASCII 2 기준 70칸이었다. 실제 원문 제목은 75칸이었고, 사전 검사표에는 Saramin 60만 존재했다.
   - 기존 제목 길이표에 JobKorea 70을 추가하고, 기존 의미 보존 AI 재작성 프롬프트도 같은 표를 읽게 했다. 두 번 재작성 후에도 부적합하면 게시 전에 멈추는 기존 계약을 유지했다.
   - 게시하지 않는 dry는 실제 publish와 같은 제목을 입력한다. test 게시 식별 접두어와 입력 잘림 실패 검사는 유지했다.

최소 구현 게이트는 2단계에서 멈췄다. 기존 변환표, AI 호출·검증 루프, 제목 재작성, 사이트 엔진을 재사용했다. 새 의존성·브라우저 러너·수동 payload·회사별 하드코딩은 없다.

## 공식 경로와 검증

- 경로: 원래 수정 화면의 잡코리아 게시 재시도 → enqueue_posting_workflow → 운영 작업자 → build_auto_posting_payload → 제목/업종 검증 → 기존 JobKorea 엔진 → 공개 링크 확인 → 실행 장부 및 원래 화면 갱신.
- 운영 워커가 활성인 상태에서 process_auto_posting_run을 수동 호출하지 않았다. 재시도 버튼은 한 번만 눌렀고 새 실행의 대상은 jobkorea 하나다. JobKorea 이력은 기존 실패 2건에서 성공 1건이 추가돼 총 3건이다.
- 실제 builder에서 제목과 업종 생성에 성공했고, 생성 전후 Project/PostingSite 전체 값의 hash가 동일했다.
- 공식 manage.py autoposting --site jobkorea --mode dry --payload ... 는 run 20260914123542에서 통과했다. 25단계 완료, submitted/published/deleted 모두 false. 제목·업종·담당자·회사명 비공개·급여 협의·본문 입력 확인.
- 이후 제목 생성 코드까지 최종 배포하고 원래 화면에서 전체 입력 생성→게시 경로를 실행해 성공했다. 실행 결과의 공개 reference 검증 오류가 없고, 공식 action list에서 공고 49984616 한 건을 재확인했다.
- 원래 화면을 실제 Chrome에서 확인했다. BusinessPeople/Exdigm/인크루트/잡코리아/사람인 모두 게시 완료.
- 원본 공고문 SHA-256 e52b35ab9bad53f0fe3f73e70fe02915b34c72c901172add2259189d461c1b3e 유지.
- 다른 네 사이트의 공고번호와 last_run 유지: BusinessPeople BR260914A00140/caf7c82c-abbb-475a-8f61-4ec67436f840, Exdigm 2608/f899e282-b5ec-4d84-a99a-96418ee6aa38, Incruit 2609140000418/3921962f-1d36-48db-82cd-8248555e0c68, Saramin 55025988/8fb83689-d06c-4d68-956d-e0dd0124048b.
- 모든 사이트 담당자 유지. 최종 JobKorea payload의 hide_real_name true, salary mode after_interview 유지.

## 검사·리뷰·배포

- 기존 업종 기준선 13건 및 제목 기준선 14건/직접 20건 통과. 새 업종 원인 재현 검사는 수정 전 같은 RuntimeError로 실패했다.
- 최종 직접 회귀: 업종·제목·입력 검증 44건 + 공개 링크 4건 = 48건 통과. 제조/기타, 잘못된 업종 수정·끝까지 실패 시 파일 생성 차단, 기존 매핑 보존, 제목 70칸 경계/초과 및 두 번 실패 차단을 포함한다.
- 보호 계약: 고정 기준 6ac315e9, 보호 파일 18개, 194건 통과.
- Django check, Ruff 3파일, git diff --check, code_knowledge catalog_update 정상. catalog 변경과 broken reference 없음.
- code-review-loop로 각 변경 diff와 직접 소비자 검토. 승인할 결함 없음. 별도 성공 경로나 고아 패치 없음.
- 최종 코드 04a42e0a9efe8451688903638532d0ec00d65e31. 선행 수정 a9a64269(업종), dfbcdacb(dry 제목)를 포함한다.
- scripts/deploy/deploy.sh prod 사용. origin/main, clean 운영 main, clean 개발 detached가 최종 코드와 일치한다. 이미지 exdigm_app:20260914123707, 앱/SSE/notification 컨테이너의 source-commit도 일치한다.
- 서비스 1/1, 운영 작업자 active 및 drain off, auto-posting 작업자 시작 시각 12:38:21 KST, HTTPS 200 확인. DB 인프라·Hermes 배포 없음.

## 검증 범위와 한계

처음의 넓은 작업자 기준선 검사는 수정 전에 24 passed/10 failed 시점에 중단했다. 개발 dry-only 경계와 기존 test/publish·알림·일부 실패 상태 기대값 불일치가 있었고, 이 검사나 안전 설정을 완화하지 않았다. 전체 저장소 테스트가 통과했다고 주장하지 않는다.

업종 정본은 현재 확인된 선택항목만 포함한다. 모든 산업과 미래 잡코리아 UI 변경에 대한 보장은 아니다. 이번 실패 입력과 같은 원인의 변형은 자동 검사에서 통과했고, 원래 프로젝트의 공식 게시 경로는 실제 성공했다.
