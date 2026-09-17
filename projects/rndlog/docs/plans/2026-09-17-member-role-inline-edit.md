# 담당자 역할 셀 편집

## 사용자 요청과 범위

2026-09-17 사용자 첨부 이미지 1의 담당자 역할 UI를 이미지 2의 관리 상태 편집 UI와 같은 형태로 변경한다. HTMX로 가장 작은 역할 셀만 교체한다. 이 요청의 구현·검증·리뷰·작업 기록만 수행하며 운영 배포와 운영 계정 변경은 별도 승인 범위다.

## 기준선과 보호할 동작

- 조정실: `C:/Users/chaconne/projects/rndlog`; 기획 정본: controlroom의 `projects/rndlog/docs`.
- SSH: `chaconne@49.247.207.147`; 개발 코드: `/home/chaconne/rndlog-dev`.
- 시작 개발 HEAD: detached `72cd790530e61f35a899029760968979fcd78571`.
- 운영 코드 `/home/chaconne/rndlog`는 main `67d07991e755ab146e73fbbf35395d2f65699ec9`, clean. 운영 코드·서비스는 이번에 변경하지 않는다.
- 대상 accounts view·URL·행 템플릿은 변경 전 개발·운영 파일 SHA-256이 같고 대상 파일의 사용자 diff는 없다.
- 개발에 있던 이메일 설정·모델·회사 상세 UI·신규 스크립트·마이그레이션 및 `.venv`·`node_modules` 연결은 보존한다. 커밋·push로 다른 변경을 묶지 않는다.
- 정상 설정은 운영 `company_main.rndlog`에 연결되므로 이름이 local이라는 이유만으로 쓰기 테스트를 실행하지 않는다.
- 전용 검증 DB: pytest가 생성한 `test_rndlog_role_ui_20260917.public`; 메일은 locmem, 주간 발송은 비활성.
- 자기/마지막 슈퍼관리자 보호, 허용 역할 검사, 고객사 복수 연결, TM 역할 해제 시 진행 내역 보존, 가입 승인·거절, 일반 POST redirect를 유지한다.

## 경로와 최소 구현

최소 구현 게이트: 2단계에서 멈춤. `accounts/views.py`의 `_account_row`, `_account_result`, `approve`와 `accounts/services/membership.py`의 `approve`를 재사용한다. UI는 `templates/rndlog/_company_status.html`의 값+수정 아이콘, 선택창+확인 형태와 공용 Tailwind 토큰을 따른다.

1. 담당자 GET 목록 → `funding/agents.html` → `_account_row.html` → 역할 셀 partial.
2. 수정 버튼 GET → 활성 승인 담당자의 편집 view → 같은 역할 셀 partial; DB를 변경하지 않는다.
3. 확인 POST → 기존 `approve` → 기존 membership 서비스 → 저장 결과 역할 셀 partial.
4. 입력/서비스 오류 → 선택값과 오류를 담은 같은 역할 셀 partial.
5. 가입 신청의 승인·거절은 기존 행 교체/제거와 `account-resolved` 이벤트를 유지한다.

역할 셀 partial은 기존 행 내부 폼을 옮겨 공용으로 사용한다. 별도의 저장 서비스·자바스크립트·CSS·의존성을 만들지 않는다. 고객사 역할 변경에 필요한 회사·담당 역할 입력은 유지한다. 다른 행의 DOM, 선택값, URL, 스크롤을 바꾸지 않는다. `funding/agents.html`의 역할 열 제목도 셀의 가운데 정렬과 맞춘다.

## 검증

- 전후 동일 기준: `POSTGRES_DB=rndlog_role_ui_20260917 DATABASE_SCHEMA=public EMAIL_BACKEND=django.core.mail.backends.locmem.EmailBackend RNDLOG_WEEKLY_EMAIL_ENABLED=false .../pytest accounts/test_signup.py accounts/test_membership.py accounts/test_company_status.py --reuse-db -q`.
- 추가: GET 편집의 무변경·권한·미승인 대상 차단, 역할 셀 성공/오류 응답, CSRF, 기존 가입 승인과 고객 연결 보존.
- HTMX가 작은 셀 응답을 요구하므로 기존 성공 응답의 행 시작 마크업 기대값만 셀로 바꾼다. 데이터·권한·오류 기대값은 보존한다.
- Tailwind 빌드, collectstatic, Django check, 변경 Python Ruff, diff 검사.
- 격리 DB의 합성 계정만 사용하여 실제 Chrome에서 수정→확인→표시 복귀, 오류→수정→재저장, 다른 행 미저장 입력 보존, 탭 이동 후 편집 재진입을 확인한다. 관리 탭 이동은 기존 일반 페이지 이동을 유지한다.
- 데스크톱 1440px, 모바일 390px/480px. CSS 실제 응답과 계산 스타일, 전체 페이지 overflow와 표 내부 스크롤, 접근 가능한 이름·focus·로딩·오류를 확인한다.
- 공용 hidden-desktop-browser 실행층을 사용하고 입력 데스크톱과 전경 창 보호 증거 및 소유한 테스트 자원 정리를 확인한다.
- code-review-loop는 주 에이전트가 직접 같은 요청 범위에서 수행한다.

## 재개 정보

- 상태: 개발 구현·실제 화면 검증·코드 리뷰 완료. 이번 6개 파일만 개발 저장소의 detached commit `15ba8e3efa656bcbab08b4550b130ff1e5e75120`에 저장했다. 기존 이메일 관련 변경과 환경 연결은 작업 시작 그대로 남아 있다.
- 다음 행동: 운영 반영이 명시적으로 승인되면 운영 Git 상태와 누적 변경을 다시 확인한다. 이번 커밋의 6개 파일 차이만 검토해 공식 main 경로로 통합하고 재검증한 후 공식 deploy.sh 절차를 따른다. 개발 저장소의 별도 이메일 변경을 임의로 함께 배포하지 않는다.
- 운영 배포: 미실행. 운영 계정 쓰기: 미실행.
- 코드 push: 미실행. 작업 문서는 조정실 controlroom에 저장한다. controlroom에는 이번 범위 밖의 미전송 FundKeeper 커밋 `ca8f6a7`과 다른 사용자 변경이 있어 전체 push는 실행하지 않는다.
- 전용 UI 서버 PID `1206544`, 원격 8017, 조정실 SSH tunnel tool session `80298`/port 18817과 전용 Chrome PID `23588`은 모두 종료했다. 이 개발 검증 URL은 종료된 주소다.
- 합성 사용자·고객사 관계·회사·로그인 세션을 제거했다. 원래 사용자 파일 18개는 SHA-256/심볼릭 링크 대조로 보존을 확인했다.
- 기준선·개발 테스트 DB는 기존 운영 데이터와 별개인 `test_rndlog_role_ui_20260917.public`이다. 재검증할 때 POSTGRES_DB를 명시하고 운영 DB로 실행하지 않는다.

## 코드 리뷰 계약

1. 원천: 이번 사용자 이미지와 역할 UI 변경 요청, 적용 AGENTS.md, 변경 전 accounts의 권한·승인 계약.
2. 상위 역할: 담당자 목록에서 승인된 계정의 역할을 관리하며 실제 역할·Django 권한·회사 연결 동기화는 기존 membership 서비스가 담당한다.
3. 경계: 작업 시작 파일 백업 대비 `accounts/views.py`, `accounts/urls.py`, `_account_row.html`, 신규 `_account_role.html`, `accounts/test_signup.py`, `funding/agents.html`. 직접 호출자는 `funding:agents_manage`, 가입 승인 화면과 셀 폼; 직접 피호출자는 `_require_approver`, `_account_options`, `_account_row`, `_account_result`, `membership.approve`.
4. 입력: 활성 슈퍼관리자만 편집 GET/저장 POST를 사용할 수 있다. GET 대상은 활성 승인자이며 선택지는 기존 User.Role에서 pending을 제외한다. 고객사 변경 입력과 기존 고객사의 복수 연결 계약을 유지한다.
5. 절차: GET은 화면만 반환한다. POST는 기존 검증·잠금·membership transaction을 사용한다. 오류 시 셀 편집과 입력을 보존하며, 가입 신청 성공은 기존 행 제거 이벤트를 유지한다.
6. 출력: 담당자 성공/오류는 같은 ID의 td, 가입 신청 오류는 tr, 신청 처리 성공은 빈 응답+account-resolved, 일반 POST는 기존 redirect와 message.
7. 보호 불변조건: 계정/명단/승인 권한, 자기·마지막 관리자 보호, 고객사 연결, TM 진행 보존, 다른 행과 이름 셀 DOM·선택·URL·스크롤, 시작 사용자 변경.
8. 비목표: 운영 반영·메일 작업·회사 상세·공용 앱 셸·권한 규칙·DB 모델·새 의존성은 변경하지 않는다.
9. 검증 근거: 같은 pytest 3개 파일과 실제 Chrome 셀 요청·DOM 동일성·격리 DB 저장값, 변경 diff·템플릿·membership 코드. 변경 diff와 직접 호출/소비자 관점으로 검토하며 별도 리뷰 에이전트는 사용하지 않는다.

## 실제 검증 결과

- 변경 전 기존 검사 57개 통과, 변경 후 추가 동작 검사를 포함한 67개 통과. 최종 수정 후에도 같은 67개 통과.
- 변경 Python Ruff·git diff --check·Django check 통과. Tailwind 빌드와 전용 STATIC_ROOT collectstatic 완료. Google SDK의 기존 폐기 예정 경고와 Browserslist 자료 갱신 안내는 검사 실패가 아니다.
- 실제 Windows Chrome: http://127.0.0.1:18817/funding/agents/, 1440px 및 390px/480px. 실제 CSS 응답 200, Pretendard와 머리글 rgb(45,58,85) 확인. 페이지 자체 가로 넘침 없음, 표 내부 가로 스크롤 유지, 모바일 선택창·확인 버튼 높이 44px.
- 실제 키보드 Enter로 편집 진입, 선택창 focus, 저장 후 수정 버튼 focus 복귀 확인. 처리 중 버튼 비활성·실제 loading 화면 확인.
- 실제 HTMX GET/POST 200과 td 응답을 확인했다. 다른 행의 DOM·미저장 선택, 수정한 행의 이름 셀 DOM, URL·세로 스크롤 위치가 유지됐다.
- 자기 관리자 권한 변경 오류는 같은 셀에서 선택값을 보존하고 올바른 값으로 재저장됐다. 고객사 전환 시 고객사·대표 역할 입력이 나타나고 활성 관계 1개가 저장됐다. 가입 신청은 기존 방식으로 승인·행 제거·빈 상태 갱신됐다. 탭 이동 뒤 역할 편집도 정상 동작했다.
- DB 직접 조회로 owner=admin, 영업1=tm, 영업2=customer, 신청자=sales 및 해당 staff/superuser 값과 고객사 관계를 확인한 후 검증 자료를 정리했다.
- 콘솔 오류·실패 요청 없음. 공용 Chrome open·행동·stop 증거에서 입력 데스크톱과 전경 창은 유지됐다.
- UI 합성 계정을 재사용 pytest DB에 남겨 둔 중간 검사 3건은 해당 계정이 마지막 관리자/TM 수 기준에 포함되어 실패했다. 합성 계정을 제거한 뒤 원래 기대값을 그대로 유지한 최종 67개가 통과했다. 이후 UI/단위 검사 자료는 순서를 분리한다.
- 모바일 중간 관측 실패는 검증 스크립트가 viewport 너비와 세로 스크롤바를 제외한 client 너비를 같다고 가정한 문제였다. 실제 scrollWidth와 clientWidth 비교로 바로잡아 가로 넘침 없음 확인. 최종 열 제목 수정은 검증 서버의 이전 템플릿 캐시를 확인하고 이번 소유 서버만 재시작한 뒤 확인했다.
- 화면 증거: `C:/Users/chaconne/.hidden-browser/evidence/rndlog-role-ui-20260917/acceptance/`의 acceptance.json, final-desktop.png, final-mobile-390.png, final-mobile-480.png 및 loading/error/saved 화면.
- 운영 main `67d07991e755ab146e73fbbf35395d2f65699ec9`과 clean 상태는 작업 종료 때도 유지됐다.

### 코드 리뷰

승인된 finding이 없습니다.

잠근 6개 파일과 직접 권한·서비스·템플릿 소비자에서 새 역할 셀 응답, 가입 신청 행 응답, 기존 redirect, 회사 연결 및 관리자 보호가 유지됨을 확인했다. 열린 계약 질문 없음. 운영 배포와 운영 쓰기 검증은 이번 범위 밖이다.
