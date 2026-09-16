# LinkedIn 문자·이메일 인증 연결 수정 — 2026-09-16

## 승인과 목표

- 사용자 요청: 두 LinkedIn 연결 실패 확인 뒤 `수정해`. 추가 조건은 사용자가 진행 화면을 벗어나지 않고 제한 시간 안에 문자든 이메일이든 인증번호를 입력·처리하는 것이다.
- 승인 범위: 기존 설정 화면과 기존 LinkedIn 인증 경로의 문자 코드 지원, 발송 방식·실제 수신처별 안내, 같은 행·프로필·탭의 확인, 관련 검증·리뷰·문서화·커밋.
- 추가 요청: 실제 이메일 주소 또는 전화번호 안내를 입력칸 바로 위에 표시한다. LinkedIn이 가린 값은 그대로 유지한다. 표시되지 않은 수신처를 저장된 이메일이나 추측으로 채우지 않는다.
- 운영 배포, 운영 DB·계정 수정, 실제 코드 발송·재발송·제출, 다른 직원 계정·검색 결과·게시 기능은 제외한다.

## 현재 근거와 원인

- 운영 조회 전용 경로에서 두 대상 계정의 저장과 failed를 확인했다. 보관된 실제 계정 탭은 문자 인증코드 입력 화면이다. 전화번호 전체·코드·인증 URL·비밀값은 기록하지 않는다.
- 화면을 읽는 기존 프롬프트와 출력 스키마는 이메일 코드만 지원하고 SMS를 unsupported로 분류한다. 실행 함수는 이에 일반 연결 실패를 반환한다.
- 원인 연결: 문자 화면을 실패로 처리함 → 판독 결과가 unsupported임 → 기존 구현이 이메일 코드로 한정됨. LinkedIn이 문자 인증을 요구한 외부 이유는 미확인이고 이번 제품 수정의 원인으로 지어내지 않는다.

## 기준선과 보호

- 코드 base: fb177d6a02f2a5b5ea14ea6440ad679f4331826a, 운영 clean main / debug detached HEAD.
- 기존 별도 변경 5파일: auto_posting/common.py, auto_posting/sites/jobkorea.py, projects/services/auto_posting_workflow.py, tests/test_auto_posting_failed_site_payloads.py, tests/test_auto_posting_workplace.py. 수정·스테이징·커밋 제외.
- 변경 전 동일 관련 검사: 157 passed / 텔레그램 설정 화면의 기존 404 1 failed. 검사·기대값을 삭제하거나 완화하지 않는다.
- 변경 전 contracts: 216 passed, 승인된 보호18파일 보존.
- 보호: 이메일 코드, 소유권, 요청 동일성·만료, 코드 암호화·사용 후 삭제, 같은 탭 재개, 이중 제출 차단, CAPTCHA·신원 확인·약관·계정 제한 중단, 다른 입력·URL·검색·게시 결과.

## 최소 구현·공식 경로

- 최소 구현 게이트: 2단계. 검색 근거는 기존 authenticate_connection, queue_verification_code, settings_linkedin_login.html, tests/accounts/test_external_site_login.py다. 새 파일·서비스·모델·DB migration·의존성·LLM 호출을 만들지 않는다.
- 경로: settings_extension 저장/재연결 → queue_linkedin_login → process_auto_posting_runs --queue candidate → process_next_credential_login → LinkedIn._authentication_map / 기존 Gemini → authenticate_connection → login_state → 기존 행 partial → 코드 POST → queue_verification_code → 같은 후보 작업자·프로필·탭 → 결과 행.
- 통합: 기존 email_code 처리 분기를 SMS와 공유한다. 판독 결과의 방식은 기존 login_state JSON에 연결한다. 화면 판독 의미는 LLM, 스키마·좌표 검사/코드 입력·상태 저장은 코드가 맡는다.
- 수신처 연결: 기존 판독 결과의 delivery_destination → 같은 인증 대기 반환값 → login_state → 같은 행 안내. 빈 수신처도 코드 입력을 막지 않으며 확인되지 않았다는 안내를 표시한다. 새 LLM 호출·DB 필드·보조 경로는 없다.
- 프롬프트 변경은 이메일 한정 규칙을 문자·이메일의 관측된 발송 안내+입력칸 규칙으로 대체한다. 앱 코드·CAPTCHA·신원 확인 등은 계속 제외하고, 재발송은 자동 선택하지 않는다.

## 화면 수용 계약

- 경로 /accounts/settings/extension/. 기존 상단 저장 응답의 #settings-content 갱신은 유지한다. 이후 진행·확인 응답은 해당 data-external-site-credential-row만 outerHTML로 교체한다.
- queued/running: 이 화면에서 기다리며 문자나 이메일 코드 입력창이 열릴 것을 안내한다. 해당 행만 2초 조회한다.
- awaiting_code: 실제 발송 방식에 맞춘 안내와 기존 one-time-code 입력·확인 버튼을 같은 행에 표시한다. 자동 갱신을 멈춰 입력을 보존한다. 만료 전에 이 화면에서 즉시 입력하도록 안내한다.
- verify queued/running: 즉시 확인 대기·처리를 표시하고 이중 제출을 막는다. succeeded는 실제 feed 확인 뒤에만 연결 완료다.
- 잘못된 코드: 같은 입력 경로로 다시 입력한다. 만료: 기존 서버의 요청 만료 검사로 거절하고 재연결을 안내한다. 다른 폼·URL·스크롤·열린 입력은 행 갱신으로 변경하지 않는다.
- 기존 form-control, one-time-code, 44px 버튼, aria-live/alert, reduced-motion 진행 표시를 재사용한다. 이동을 강제로 차단하거나 새로운 팝업·타이머·CSS·추가 설명을 만들지 않는다.

## 검증·리뷰와 재개

- test-first로 기존 테스트 파일에 SMS 판독·코드 대기·같은 탭 제출·worker 방식 전달·같은 화면 안내를 추가하고 실패→통과를 확인한다.
- 동일 관련 4파일 검사, contracts, Django/Ruff/diff/catalog. 기존 텔레그램 실패를 같은 기준으로 별도 대조한다.
- 실제 dev runserver / exdigm_debug 경계를 확인한다. 개발 전용 합성 계정과 외부 응답 double로 실제 UI 저장→대기→코드→성공/실패 및 desktop/mobile를 확인한다. 실 LinkedIn 코드 수신·제출 성공을 이 증거로 주장하지 않는다.
- 실제 보관 SMS 화면은 읽기 전용으로 새 프롬프트의 인식을 확인할 수 있다. 운영 인증·탭·브라우저는 변경하지 않는다.
- code-review-loop는 주 에이전트가 수행한다. 이번4파일과 직접 소비자만 리뷰한다.
- 현재 상태: 문자·이메일 공통 코드 처리와 실제 수신처 안내 구현·검증을 마쳤다. 운영 반영과 실제 받은 코드의 제출·로그인 성공은 제외 범위이며 아직 하지 않았다.

## 리뷰 계약 잠금

1. 원천: 이 문서의 승인·기준선, 주인님의 문자/이메일 입력·화면 유지·실제 수신처 요청, 프로젝트 AGENTS 및 code-review-loop.
2. 역할: 외부 계정 연결 중 사람이 받은 코드를 기존 작업자와 같은 LinkedIn 탭에 전달하고, 실제 로그인 완료만 표시한다.
3. 경계: base fb177d6a와 현재 이번4파일 diff. 직접 소비자는 settings_extension, ExternalSiteCredential 상태 속성, 해당 행 partial, candidate 큐 관리 명령이다. 다른 dirty 파일은 제외한다.
4. 입력: LinkedIn의 보이는 발송 안내·좌표, 코드 최대32 ASCII 영숫자, 본인 credential와 같은 request_id, 기존 사용자별 profile/page, 개발 검증은 격리 계정만.
5. 절차: 판독 → 기존 공통 코드 대기 → 행 안내 → 본인 코드 POST/암호화 → 같은 큐/탭 제출 → feed 확인. 재발송·보안 우회 없음. 만료·중복 요청·오류 후 코드를 보존하지 않는다.
6. 출력: awaiting_code에 관측된 방식과 수신처만 저장한다. 화면은 가려진 값을 유지·escape하며, 미표시 수신처를 추정하지 않는다. 실제 feed 전에 succeeded를 만들지 않는다.
7. 보호: 기준선의 이메일 성공·소유권·요청 동일성·만료·암호화/삭제·같은 탭·중복 차단과 다른 화면 입력/URL 및 외부 효과를 그대로 보존한다.
8. 비목표: 운영 배포, 실제 발송/제출, 앱/통화/CAPTCHA/신원/복구/약관 처리, 다른 계정·게시·검색·Hermes 및 다른 사용자 변경.
9. 근거: 이번4파일 diff/기존 테스트, 동일 관련4파일 검사, contracts, Django/Ruff/catalog, 실제 개발 desktop/mobile 화면 및 합성 fixture의 공식 저장→큐→확인 경로.

리뷰 관점의 질문:

- 변경 diff: SMS와 이메일이 같은 코드 분기를 쓰며, 수신처가 실제 판독값에서만 오는가?
- 1차 영향: 큐→login_state→행 소비자 연결, 같은 요청/탭·입력 보존·만료와 실제 feed 성공 조건이 유지되는가?
- 지침: 실제 외부 발송/재발송·보안 확인 자동 처리나 다른 dirty 파일의 변경이 추가되지 않았는가?

### 코드 리뷰

승인된 finding이 없습니다.

- 주 에이전트가 잠근 이번4파일의 전체 diff와 직접 소비자를 단일 리뷰 패스로 확인했다. 열린 material contract question과 계약 변경 항목은 없다.
- 기존 코드 입력 분기에 SMS를 연결하며 같은 큐·프로필·page_id·요청 만료·코드 삭제·실제 feed 성공 조건을 유지한다. 수신처는 기존 판독값에서만 연결되고 템플릿 autoescape를 보존한다.
- 앱→이메일 대체 경로, unsupported 중단, 다른 credential 소유권, 암호화·실패 후 코드 삭제와 중복 제출 검사는 기존 기대값을 유지했다.
- 실제 수신 코드로 LinkedIn 로그인하는 외부 성공은 이번 리뷰의 검증 증거에 포함하지 않는다.

## 최종 검증 결과

- Test-first SMS: 새 조건6실패 → 기존 및 새 인증 테스트31통과. 수신처 추가: 해당 조건19실패/기존29통과 → 전체 인증48통과.
- 동일 관련4파일 검사: 변경 전157통과/1실패 → 변경 후181통과/1실패. 남은 실패는 변경 전과 같은 텔레그램 설정404 기대값이다. 검사·기대값은 삭제하거나 완화하지 않았다.
- 보호 contracts216통과 및 승인18파일 기준 보존. Django check, Ruff, diff check, 코드 카탈로그 current/valid와 참조 검사 통과. 새 migration·의존성·프로덕션 모듈·LLM 호출 없음.
- 실제 개발 UI1440/390: 저장 → 코드 대기 → 확인 처리 → 잘못된 코드 → 재입력 → 성공 표시, 이메일 Enter 제출, 만료 요청 거절을 공식 설정·큐 관리 명령으로 확인했다. LinkedIn 경계만 합성 응답을 사용했다.
- 입력 대기 중 polling이 없고 코드와 별도 폼 입력값이 유지됐다. 같은 URL을 유지했고 코드 입력칸의 자동 초점이 확인됐다. 가로 넘침이 없다. 기존 CSS 응답은200, 실패 요청은 없었다.
- 개발 UI console에 resource404가6건 관측됐다. 공용 관찰의 document/stylesheet/script/xhr/fetch 응답은 오류가 없지만 image/font 등은 URL 기록 대상이 아니어서404의 정확한 리소스는 미확인이다. 새 인증 동작의 오류나 콘솔 전체 무오류로 주장하지 않는다.
- 두 실제 보관 LinkedIn 탭에서 코드가 비어 있음을 확인하고 새 _authentication_map만 읽기 전용 실행했다. 최신 판독은 모두 sms_code 및 전화번호 끝자리 안내다. 탐색·코드 입력·재발송·인증 DB 상태 변경은 없다. 최초 검사의 text 타입 선택 오류는 실제 pin 입력이 tel임을 확인해 바로잡았다. 중간 판독1회의 AssertionError는 반환값을 기록하지 않아 원인을 확정하지 않았고, 추가 읽기에서 현재 결과를 확인했다. 모델 판독의 모든 외부 화면 변형까지 검증했다고 주장하지 않는다.
- 합성 계정·credential는 고유 UUID/이름을 대조해 제거했다. 공용 stop은 이번 도구가 소유한 숨은 Chrome만 종료했다. 입력 데스크톱과 전경 창 유지가 공용 open/모든 capture에서 확인됐다.

### 화면 증거

- 문자 데스크톱: C:/Users/chaconne/.hidden-browser/evidence/exdigm-linkedin-verification/sms-email-20260916/20260916-080421.png
- 이메일 모바일: C:/Users/chaconne/.hidden-browser/evidence/exdigm-linkedin-verification/sms-email-20260916/20260916-080437.png
- 문자 모바일: C:/Users/chaconne/.hidden-browser/evidence/exdigm-linkedin-verification/sms-email-20260916/20260916-080445.png
- 만료 안내 모바일: C:/Users/chaconne/.hidden-browser/evidence/exdigm-linkedin-verification/sms-email-20260916/20260916-080447.png

### 남은 작업과 재개

- 커밋은 이번4파일만 포함한다. 기존 게시 관련5파일과 별도 추천 이력서2파일은 다른 사용자 작업으로 보존한다.
- 디버깅 커밋: 5c8a295f0678cd079946c8875c4149fc544d97fb. 이번4파일만 포함했으며 작업 시작 상태와 다른 사용자7파일을 스테이징하지 않았다.
- GBrain project/exdigm-external-site-credential-settings에 현재 개발 계약·검증·미배포/미인증 상태를 갱신했다. 기존 기록은 역사 기록으로 보존한다.
- 제가 시작한 개발 runserver 프로세스 그룹은 cwd·명령·PID/PGID를 대조한 뒤 SIGINT로 종료했다. wrapper가 자기 게시 dry-run 작업자만 함께 정리했고 공식 status는 inactive다. 기존 운영 작업자2개와 원래 보관 LinkedIn 브라우저는 유지한다. 임시 adapter·patch는 제거하고 화면 증거는 남긴다.
- 운영은 clean main fb177d6a이며 이번 수정은 미배포다. push·운영 배포·실제 코드 발송/제출은 하지 않는다.
- 재개: 주인님이 운영 배포를 별도로 승인하면 exdigm-deploy를 사용한다. 다른 작업자의 dirty 변경과 일괄 배포 범위를 다시 대조하고 공식 deploy.sh prod만 사용한다. 주인님은 같은 진행 화면에서 실제 수신 코드만 직접 입력하며, 실제 feed/연결 상태·코드 삭제를 검증한다.

## LinkedIn만 운영 배포 — 2026-09-16

- 별도 승인: 주인님의 “링크드인 수정된거만 운영 배포”. 앞의 운영 미배포/승인 대기는 이 승인으로 갱신한다. 실제 인증 발송·재발송·제출은 승인 범위가 아니다.
- 후보는 검증·리뷰한 5c8a295f0678cd079946c8875c4149fc544d97fb 그대로다. 운영/GitHub 기준 fb177d6a와 차이는 위 LinkedIn4파일뿐이며 새 제품 변경을 추가하지 않는다.
- 운영은 clean main fb177d6a, debug detached HEAD5c8a295f, index 공백을 재확인했다. 다른 사용자의 게시5파일 및 추천 이력서2파일은 편집 중단 확인 후 정확한7경로의 Git stash에 복구 가능하게 보관한다. ignored .debug 진단 자료와 인증 프로필은 건드리지 않는다.
- 보호 기준선은7파일 SHA256·6tracked 파일 binary diff SHA256·status 목록과 동일한 HEAD다. 복원 시 모두 대조하며 충돌을 임의 해결하지 않는다. 기존 이메일·암호화/삭제·만료·같은 큐/탭 계약과 운영 DB 인프라/Hermes는 유지한다.
- 공식 검증은 깨끗한 후보에서 인증 테스트, contracts, Django/Ruff/diff 및 카탈로그를 다시 확인한다. 공식 scripts/deploy/deploy.sh prod만 실행하고, GitHub/운영/실행 코드 일치·서비스·작업자·HTTPS·운영 화면을 확인한다.
- 배포 후7파일은 정확한 stash 객체에서 복원하고 보관본은 삭제하지 않는다. 다른 작업자에게 HEAD 및 해시·diff 동일성을 알린 뒤 편집을 재개하도록 한다.

### 운영 반영 및 검증 결과

- 공식 prod는2026-09-16 17:23:22 KST에 prod ok5c8a295f 및 exit0으로 끝났다. 실제 GitHub refs/heads/main, 운영 clean main, debug detached HEAD, 실행 app/SSE/notification .source-commit이5c8a295f0678cd079946c8875c4149fc544d97fb로 일치했다. fb177d6a 대비 LinkedIn4파일만 추가됐다.
- 이미지 exdigm_app:20260916172201, 세 실행 컨테이너 모두 sha256:54057a17fb794417eff3329b524a114362f2d6889c31054c7db7b6776fcfedef다. 서비스5개1/1 및 세 앱 서비스 update completed, 작업자·지원11개 active/jobs0/drain off, 공식 운영 read-write 실행 경로, HTTPS200을 확인했다. DB 인프라와 Hermes는 배포하지 않았다.
- 깨끗한 후보에서 인증48개와 보호216개가 재통과했다. 고정 보호18파일 보존, 새 이미지 DOC/DOCX/PDF 실제 업로드 텍스트 전달 계약, Django/Nginx/Ruff/diff 및 카탈로그 current/valid/참조 검사가 통과했다. 카탈로그의 존재하지 않는 status 명령 조회1회는 오류로 끝났으며 실제 catalog_update 출력과 공식 map_validate로 확인했다. 제품 코드 변경이나 검사 완화는 없다.
- 보관 stash 객체는 b339c331b0fc1493842555db9623dff5ac462645다. 정확한 객체를 apply해7파일을 복원했다.7파일 SHA256,6tracked binary diff SHA256 1aa0a6e5c8247c9d7dcb342fd75c020aba47628b68842f44ae1cf65a1677491f 및 status 목록이 보관 전과 완전히 동일하다. index는 공백이며 stash는 복구용으로 남긴다.
- 운영 화면 확인은 공용 숨은 Chrome의 읽기 전용 조회만 사용했다. 운영 로그인 세션이 없어 정확한 settings URL에서 정상 로그인 화면으로 이동하는 것까지 직접 확인했다. 새 OTP 요청·재발송·코드 제출·운영 인증 상태 조작은 하지 않았고, 인증된 운영 코드 입력 화면 및 실제 LinkedIn 로그인 성공은 미검증이다. 개발 합성 경로의 성공과 구분한다.
- 화면 증거: C:/Users/chaconne/.hidden-browser/evidence/exdigm-linkedin-prod/linkedin-only-20260916/20260916-082246.png. 직접 이미지 확인 후 이번 소유 Chrome만 stop했고 공용 open/capture/stop의 input desktop 및 foreground 유지가 확인됐다. 영속 프로필은 보존했다.
- 재개 조치: 주인님이 운영 설정을 새로고침하고 본인 LinkedIn 행에서 다시 연결하면, 코드 대기 상태에서 발송 대상 안내와 입력칸을 확인하고 받은 코드를 직접 제출한다. 외부 실제 feed 및 성공 상태·코드 삭제 확인은 그 사용자 조작 이후다. 앱/통화/CAPTCHA/신원/약관·자동 재발송을 성공으로 처리하지 않는다.
- 공용 GBrain의 credential settings/deploy workflow/operating context에17:23 LinkedIn-only 반영과 미검증 인증 경계를 기록하고 세 페이지를 실제 재조회해 새 구역 및 커밋·역사 기록 보존을 확인했다. embedding 대기1회 뒤 capture가 정상 종료했다.
- 이 요청의 원격 편집·Git·배포는 끝난 뒤 별도 승인된 추천 이력서 작업에 Git 단독 소유를 인계했다. 그 작업은 추천2파일만 추가한 f0154004의 독립 prod를 이후 시작했다. 위5c8a295f 일치/서비스 증거는17:23 LinkedIn 배포 검증 시점이며 이후 운영 판본의 고정 주장이나 합동 배포가 아니다. 게시5파일 작성자에게 그 작업의 보관/복원 완료 뒤 재개하도록 통보했다.
