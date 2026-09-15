# 2026-09-15 운영 오류 수정

## 현재 재개 기준 — 합동 배포 완료, 사람인 추가 보완 배포 대기

- 운영은 d5d7ad7869384a12eec37c8748474c1a99455503으로 합동 배포 완료다. 정렬 화면과 오류 수집 수정이 실제 운영 경로에 반영됐다. 아래 이전 시점의 미배포 기록은 경과 기록이다.
- 승인된 이력서 8건 중 인크루트4건과 잡코리아1건이 done이다. 5건 모두 실제 Drive 메타데이터의 파일 크기·MD5·정확한 대상 폴더·원래 장부 식별자를 확인했다. 원본 링크/메타데이터 해시 및 기존 알림 영수증은 유지됐다.
- 사람인3건은 미완료다. 첫 장부 a2f861d4-49b8-420f-80da-d89ed791a904는 attempt4 인쇄 준비 단계 실패, 나머지2건은 원래 attempt3을 유지한다. 성공한5건은 재실행하지 않는다.
- 사람인 추가 보완2파일은 fa524969aaba4aa1fd0686eeb8e69d02fc03daf4로 커밋했다. 관련85개·보호194개·Django/Ruff/catalog/diff 검사 통과, 같은 base8c2ea773와 합동 계약의 재리뷰에서 승인 finding0개다. 추가 push/배포는 아직 하지 않았다.
- 공유 debug worktree에서 별도 인크루트 근무지역 UI 대응 작업의 auto_posting/sites/incruit.py, auto_posting/site_maps/incruit/field-map.json, tests/test_auto_posting_failed_site_payloads.py 변경이 진행 중이다. 원래 정렬 합동 배포 범위가 아니므로 손대거나 포함하지 않았다. clean 배포 전제 때문에 순서 조정 방향을 주인님께 질문했다.
- 다음: 별도 인크루트 작업과 충돌 없이 clean 배포 후보를 확정한 뒤 공식 prod로 fa524969를 반영한다. Git/실행 판본과 서비스 정상 확인 후 사람인 첫 장부만 source hash/attempt4/failed/no FileData/no claim 조건으로 waiting에 돌린다. 공식 worker의 파일 저장 성공 후 나머지2개를 검증한다.
- CEO 메일502 상세 원인과 사용자 식별 기록 보완, bk 직원의 네 사이트 개인 연결은 이 배포로 해결되지 않았다. 운영 DB 인프라·Hermes·메일 검색 범위는 변경하지 않았다.
- 직접 실행했던 숨은 Chrome은 종료했고, 개발 runserver의 소유 프로세스 그룹3029160을 확인해 종료했다. 프로세스와8443리스너가 없음을 재확인했으며 운영 작업자11개는 active/jobs0/drain off, 서비스5개는1/1을 유지한다. 사용자 기존 운영 Chrome 탭은 열어 둔 채 원래 URL로 복원했다.

## 2026-09-15 합동 배포 승인 및 재개 상태

- 주인님은 검증된 오류 수정의 운영 배포와 실패 이력서 링크 8건의 재처리 제안에 `진행해`로 승인했다.
- 이어서 `같이 배포해`로 프로젝트 목록 정렬 변경 커밋 89fccbef45bb92ff09ea973b97bd896dc544e36c도 함께 배포하도록 승인했다. 아래 초기 기록의 보드 변경 제외 및 배포 승인 대기는 이 결정으로 대체한다.
- 배포 기준 base는 운영 main 8c2ea773723757da4422e698ac8b34c86a0fd2f8이다. 배포 대상은 정렬 변경 6파일과 오류 수정 8파일이다. 운영 DB 인프라, Hermes 설정, 계정 연결, 메일 검색 범위는 변경하지 않는다.
- 합동 검사: 오류 관련 235개와 프로젝트 화면 56개 통과, 프로젝트 화면 12개 실패 및 4개 setup 오류. 같은 공식 테스트를 기존 운영 판본에서도 실행해 동일한 16개 실패와 54개 통과를 확인했다. 새 정렬 검사 2개는 통과했다. 기존 실패를 삭제하거나 기대값을 완화하지 않는다.
- 기준선 비교 중 오류 수정은 stash bf49f10073093c66cd533747753f706a72929044에 보관했다가 89fccbef 위에 복원했다. 전후 전체 diff SHA-256은 140e39d2dd617a4aa02a7ed559b5a24fcbb79a421e7b6992f7b8c12673294d85로 일치한다. 복구용 stash는 보존 중이다.
- 실제 화면 검증: SSH 개발 서버 세션 28715, DB/역할 exdigm_debug, 메모리 이메일 backend, dev.exdigm.com, Windows 숨은 Chrome exdigm-errors-deploy, 1440x1000. 현재 정렬 후 필터/보기 전환의 상태 보존을 확인 중이다.
- 아직 제품 커밋 추가, push, 운영 배포, 실패 장부 상태 변경은 하지 않았다.

### 합동 코드 리뷰 계약

1. 원천: 오류 수정 요청과 본 문서의 보호 조건, 정렬 커밋 89fccbef 및 주인님의 함께 배포 승인.
2. 역할: 기존 이력서 수집의 실패 원인을 제거하고, 프로젝트 목록에서 선택한 기준과 방향대로 허용된 프로젝트를 표시한다.
3. 경계: base 8c2ea773부터 정렬 6파일과 오류 8파일 및 직접 호출/소비자. 정렬은 project_list → get_project_kanban_cards → 목록/보드 partial → 사용자 필터·보기 전환까지 확인한다.
4. 입력: 기존 URL/파일/사이트 입력 계약에 더해 허용 정렬 기준 3개, 방향, 사용자 권한, 검색·고객사·담당자·상태 필터.
5. 절차: 기존 수집 절차는 보존. 정렬은 GET 요청으로 보드와 URL을 갱신하고 후속 필터/보기 요청에서도 현재 선택을 전달한다. 업무 데이터 쓰기는 없다.
6. 출력: 실제 이력서 파일과 기존 장부 연결, 정상 문서만 수집; 화면은 선택한 기준·방향으로 정렬되고 필터와 접근 범위를 보존한다.
7. 보호: 본 문서의 수집 보호 조건, 직원별 프로젝트 접근 제한, 기존 검색/고객사/상태/보기 선택, 다른 작업의 커밋과 수정 내용.
8. 비목표: 정렬 UI 재설계, 기존 무관한 게시·기준 데이터 검사 실패 수정, DB 인프라/Hermes/인증 정책 변경, 메일함 검색 확대.
9. 검증: 동일 공식 테스트의 base 대조, 정렬·필터 실제 Chrome 상호작용, 보호 계약 194개, 배포 이미지 계약, 운영 Git/이미지/서비스/작업자 일치, 원래 장부 8건의 공식 작업자 결과.

리뷰 관점은 변경 diff와 직접 소비 관계이다. 기존 16개 검사 실패는 base에서도 재현됐으므로 이번 diff의 finding으로 승인하지 않는다. 실제 화면 결과와 운영 재처리는 개발 테스트 통과로 대체하지 않는다.

### 합동 리뷰 finding 및 수정 검증

- 승인 finding 1개: 정렬 HTMX 응답이 보드만 교체하므로, 보드 밖 필터/상태/보기 폼이 이전 sort_by·sort_open·sort_closed를 제출한다. 실제 Chrome에서 elapsed 선택 후 closed 전환이 document_deadline으로 돌아감을 재현했다.
- 연속 질문: 정렬 초기화는 이전 값 제출 때문(확인), 이전 값 제출은 바깥 폼 미갱신 때문(확인), 미갱신은 partial의 상태 전달 계약 누락 때문(확인). 버드뷰의 정렬 선택 → 보드/주소 → 후속 필터 요청과 대조해 최초 이탈이 일치함을 확인했다.
- 최소 구현 4단계: 기존 HTMX OOB 기본 기능을 사용한다. project_list의 partial 응답에 sync_sort_state를 설정하고 view_board에서 정렬 hidden input 3종만 OOB 갱신한다. 새 JS/라이브러리/저장 상태 없이 해당 책임에 통합했다.
- 기존 정렬 테스트에 검사를 추가해 red 1개를 확인한 뒤 수정하여 정렬 2개가 통과했다. 실제 Chrome에서 세 정렬 기준, 방향, 검색어, 진행/종료, 카드/리스트 전환의 선택 보존을 확인했다. 데스크톱/390px 화면 PNG를 직접 확인했고 가로 overflow는 없었다.
- 최종 같은 확대 검사: 291 passed, 기존과 동일한 12 failed 및 4 errors. 보호 계약 194 passed, 보호 파일18개 동일, check/Ruff/catalog/diff 검사 통과. 추가 회귀는 없다.
- 알려진 개발 화면 별도 항목: nginx Basic 인증에 따른 PWA manifest 401, 전체 이동 시 heartbeat 취소; 정렬 XHR과 실제 CSS는 200이며 정렬 조작 중 새 오류는 없었다. 이 범위를 이번 정렬 코드 결함으로 처리하지 않는다.
- 재리뷰: base 8c2ea773, 합동 14파일 및 직접 소비자를 같은 계약으로 재확인. 승인 finding 0개, 계약 변경이 필요한 열린 질문 없음. 정렬 상태 전달의 재발 경로는 실제 개발 화면 검증 범위에서 닫힘이다.
- 운영 사전 조회: 원래 링크 8건 모두 failed/attempt3/FileData 없음/claim 없음/실패 알림 발송 완료. source URL·metadata 해시를 기록했다. 프로젝트74개, 오류 기록14개이며 초기 조사 이후 추가 기록은 원래 11건과 구분한다.
- 배포 후 UI 확인에는 현재 로그인된 사용자 Chrome의 Exdigm 프로젝트 탭(1386260259)을 사용한다. 기존 금융 탭과 개인 인증은 이동·복사·종료하지 않는다.

### 18:16 운영 반영과 실제 이력서 재처리

- d5d7ad7869384a12eec37c8748474c1a99455503 공식 prod 배포가 18:16:04 KST exit0으로 완료됐다. debug/origin/main/운영 main/실행 app·SSE·notification 모두 같은 판본, 서비스5개1/1, 작업자11개active/read-write/drain off, HTTPS200이다.
- 실제 Chrome 운영 화면에서 새 정렬 기준이 표시되고, 경과일수 선택 후 종료 전환에도 선택이 유지됐다. 원래 URL `?sort_open=desc&status_view=open`로 복원했다. 이 전환은 프로젝트 내용 수정이나 게시를 하지 않는다.
- 원래 장부8개와 관련 메일기록8개를 `/home/chaconne/exdigm-debug/.debug/operational-errors-20260915-before-retry.json`에 0600으로 백업했다. SHA256 fa6c30af63d2b7fd26f57e3b76c4e668ab419d0629556108ee52ef222e261408. 민감한 원문 URL/메일 내용은 채팅·Git·GBrain에 기록하지 않는다.
- 정확한 ID·source URL/metadata 해시·failed/attempt3/FileData 없음/claim 없음 조건을 확인하고 원래 장부를 waiting으로 돌렸다. 기존 운영 resume-uploader가 claim과 모든 다운로드·업로드를 수행한다. attempt budget과 이전 알림 영수증은 초기화하지 않았다.
- 인크루트4개는 attempt4에서 done. 실제 Drive 메타데이터의 크기(75564/89888/34732/59470바이트), MD5, 대상 폴더, 장부 appProperty가 모두 일치하고 각각 메일 uploaded_count1이다.
- 잡코리아1개도 attempt4에서 done, 186610바이트, FileData a09b609d-aa12-4d75-9c04-98508f5df61e, Drive 1WLY1k4DM6fwJ309wD1WSgEiBbpvDGDag. 기존 성공 첨부를 포함한 해당 메일 uploaded_count는2다.
- 사람인 첫건 a2f861d4-49b8-420f-80da-d89ed791a904는 지원자 선택을 통과했으나 인쇄 버튼 검사에서 실패했다. 나머지 사람인2개는 재시도하지 않고 보존했다. 8개 중5개 완료이며 사람인3개는 아직 미완료다.

### 사람인 인쇄 단계 재개 게이트

- 현상 잠금: 정확한 지원자의 공식 PDF를 Drive/FileData/메일 결과로 전달해야 한다. 첫 운영 재처리에서 `Saramin resume print control is not unique`가 발생해 완료 조건을 축소하지 않고 조사를 재개했다.
- 연속 질문1: 왜 인쇄 확인이 실패하는가? 버튼/대화상자가 표시되기 전 count가0이다(확인: 실제 원격 공유 브라우저9223).
- 연속 질문2: 왜 표시 전에 검사하는가? 고정3.27초 시점에 인쇄 버튼이0이고,4.30초에1개가 된다. 버튼 클릭 직후 대화상자도0이었다가 visible 대기 후1개다(확인).
- 연속 질문3: 왜 고정시간/즉시 count를 사용하는가? 상세 버튼의 준비 계약이 없고, 대화상자는 기존 wait_for보다 count를 먼저 실행한다(확인: Saramin.download_resume).
- 버드뷰: 목록→지원자 선택→상세→인쇄 대화상자→공식 print popup/PDF의 단계별 생산 구조에서 상세/대화상자 준비 확인이 최초 이탈이다. 결과 대조는 일치. 선택한 인쇄 사유는 즉시 표시됐으므로 이 부분은 바꾸지 않는다.
- 최소 구현2단계: 기존 wait_for를 재사용한다. 인쇄 버튼은 표시 후 유일성 확인, 대화상자는 기존 표시 대기를 유일성 확인 앞으로 이동한다. 후보 신원/경력/인쇄 사유/PDF 검증 및 기존 로그인 대기는 유지한다. 새 분기·의존성·실행 경로는 없다.
- 기준선: d5d7ad78 clean에서 브라우저42개 통과. 기존 테스트를 목록/인쇄버튼/대화상자의 즉시·지연 표시8조합으로 확장해 red6개/성공2개 확인. 수정 후 전체 browser+uploader85개 통과. 보호194·Ruff·catalog·diff 검사 및 같은 base8c2ea773의 합동 리뷰를 수행한다.
- 재리뷰 계약은 기존 합동 계약을 유지한다. 이번 차이는 Saramin.download_resume와 기존 브라우저 테스트2파일뿐이며 이미 배포된 나머지 파일과 복구된5개 장부는 보호한다. 추가 운영 반영/사람인 재처리 전 상태다.

## 목표와 승인 범위

- 주인님 요청: DB에 남은 오류 내역에 문제해결 게이트를 적용해 수정한다.
- 원천 기록: projects.OperationalError 12건 중 배포 테스트 1건을 제외한 11건.
- 구현·격리 검증·리뷰·작업 문서화는 현재 요청 범위다. 운영 배포·실패 장부 재처리·외부 계정 연결 변경은 실제 영향과 검증 결과를 보고하고 별도 확정한다.
- 서버: chaconne@49.247.202.197. 수정 위치: /home/chaconne/exdigm-debug.
- 기준선: 운영 clean main 및 개발 clean detached HEAD 모두 8c2ea773723757da4422e698ac8b34c86a0fd2f8.
- 조정실 controlroom도 변경 시작 시 clean이었다.

## 현상 잠금

| 묶음 | 기록 수 | 필수 결과 | 원래 실패 지점 |
|---|---:|---|---|
| 인크루트 링크 | 4 | 메일의 이력서 원본을 내려받아 기존 Drive 업로드 장부에 연결 | HTTP 이동 주소 UTF-8 해석 오류 |
| 사람인 링크 | 3 | 메일이 지목한 정확한 지원자의 이력서 파일 확보 | 후보자 행 0개 |
| 잡코리아 링크 | 1 | 지원 이력서 공식 다운로드 | 다운로드 버튼의 개수/표시 상태 검사 |
| Drive 임시 파일 | 1 | 실제 문서만 처리하고 임시 소유자 파일은 수집 대상에서 제외 | 162바이트 ~$ DOCX를 문서로 처리 |
| 외부 검색 | 1 | 허용된 본인 연결로 사이트별 검색, 기존 성공 결과 보존 | 네 사이트 개인 로그인 정보 없음 |
| CEO 회사 메일 | 1 | 본인 메일함 검색을 정상 목록/빈 목록으로 반환 | /agent/email/messages/ HTTP 502 |

## 연속 질문과 직접 근거

### 인크루트

1. 왜 다운로드가 멈췄는가? HTTP 이동 주소를 읽는 중 UTF-8 해석이 실패했다. 확인: 원래 실패 링크에서 동일 바이트 0xb9와 position 217 재현.
2. 왜 HTTP 이동 주소를 읽는 중 UTF-8 해석이 실패했는가? Requests가 Location 헤더의 원래 바이트를 UTF-8로 가정한다. 확인: sessions.get_redirect_target → to_native_string 호출 경로.
3. 왜 Requests가 Location 헤더의 원래 바이트를 UTF-8로 가정하는가? 라이브러리 기본 정책이며 현재 다운로드 통합 경계가 비 UTF-8 이동 주소를 URL 표기로 보존하지 않는다. 확인: allow_redirects=False여도 다음 요청 준비 중 예외가 발생한다.

### 사람인

1. 왜 후보자 행 0개로 실패했는가? 비동기 후보자 목록이 나타나기 전에 행을 센다. 확인: 페이지 틀은 0.37초, 이름 컨트롤은 약 5.04초에 표시.
2. 왜 비동기 후보자 목록이 나타나기 전에 행을 세는가? 고정 2.5초 대기 후 count를 즉시 호출한다. 확인: Saramin.download_resume.
3. 왜 고정 2.5초 대기 후 count를 즉시 호출하는가? 이 단계에 실제 목록 준비 계약이 없다. 확인: 같은 선택자는 준비 뒤 20명과 세 실패 대상의 이름을 반환한다.

### 잡코리아

1. 왜 다운로드 버튼을 확정하지 못했는가? 버튼 개수 또는 표시 상태가 즉시 검사에서 맞지 않았다. 확인: 저장된 오류를 발생시키는 분기.
2. 왜 버튼 개수 또는 표시 상태가 즉시 검사에서 맞지 않았는가? 고정 2초 뒤 준비 대기 없이 검사한다. 확인: 현재 버튼은 하나이며 표시 완료를 기다리면 존재한다. 당시 정확한 화면은 미검증.
3. 왜 고정 2초 뒤 준비 대기 없이 검사하는가? 페이지 틀과 다운로드 컨트롤 준비를 구분하는 계약이 없다. 코드 결함은 확인, 원래 사건의 유일 원인 여부는 미검증.

### Drive

1. 왜 DOCX에서 텍스트가 없었는가? 읽기 대상은 162바이트의 ~$ Office 임시 파일이다. 확인: 운영 FileData의 이름·크기·처리 상태.
2. 왜 읽기 대상은 162바이트의 ~$ Office 임시 파일인가? Drive 수집이 확장자/MIME을 근거로 문서 처리 대상으로 넘겼다. 확인: drive_batch 경로와 build_file_row.
3. 왜 Drive 수집이 확장자/MIME을 근거로 문서 처리 대상으로 넘겼는가? 공통 분류에 Office 임시 파일 제외 조건이 없다. 확인: sync_drive_changes → build_file_row → decision_for_row → FileData/manifest.

### 외부 검색

1. 왜 네 사이트 검색이 시작되지 않았는가? 사용자 로그인 정보가 없다. 확인: 저장된 site result.reason.
2. 왜 사용자 로그인 정보가 없는가? 해당 사용자에게 ExternalSiteCredential이 등록되지 않았다. 확인: 운영 조회 0행.
3. 왜 해당 사용자에게 ExternalSiteCredential이 등록되지 않았는가? 등록 경위는 확인하지 못했다. 코드의 타인 계정 대체 근거는 없다. 미검증/사용자 연결 필요.
- LinkedIn 성공 후보자 15명은 보존한다. 전체 검색을 재실행하거나 다른 직원 인증을 복사하지 않는다.

### CEO 메일

1. 왜 요청이 502로 끝났는가? 회사 메일 서비스가 읽기 실패를 반환했다. 확인: nginx/app 로그와 응답 분기.
2. 왜 회사 메일 서비스가 읽기 실패를 반환했는가? 당시 상세 예외는 저장되지 않아 미확인이다. 로그인/검색/개별 메일 fetch를 구분해야 한다.
3. 왜 당시 상세 예외는 저장되지 않아 미확인인가? 응답으로 변환된 예외는 일반 502 로그가 되고 현재 수집기는 method/path/status만 보존한다. 확인: company_email 및 OperationalErrorHandler.
- 실패 요청은 12:52:33 KST, query는 Webinar 제목이며 88.461초 소요. 12:54:30의 limit=1 요청은 200, 65.991초.
- 주인님 확인: CEO가 Telegram Hermes에 요청했고 대상 메일은 휴지통에 있었을 가능성이 있다.
- 현재 API는 INBOX를 기본으로 고정한다. 휴지통 미검색과 502 원인은 분리한다. 검색 결과 없음의 정상 출력은 빈 목록이다.
- CEO 메일 및 BOSS AgentProfile은 active이며 연결 user_id가 일치한다. 오류의 사용자 번호 누락은 수집 항목 누락으로 확인했다.
- 개발 조회 전용 환경은 운영 메일 비밀번호를 복호화할 수 없어 InvalidToken으로 외부 조회 전에 중단됐다. 운영 인증 장애의 증거가 아니다.

## 버드뷰

- 메일 링크 → 공통 다운로드 → 사이트 이력서 파일화 → Drive → FileData/Resume/Candidate의 기존 책임을 유지한다.
- 임시 파일은 원천의 대상 판별 단계에서 제외해야 한다. 추출 실패를 숨기거나 가짜 텍스트로 바꾸지 않는다.
- 검색은 사용자별 인증이 필수이고 성공 사이트 결과를 보존한다.
- 메일 API는 사용자에 연결된 메일함만 읽는다. 사용자 번호/에이전트 번호 누락과 실제 연결 실패는 같지 않다.

## 결과 대조와 근본 원인 판정

- 인크루트·사람인·Drive: 연속 질문과 버드뷰가 일치한다.
- 잡코리아: 준비 확인 결함은 확인. 당시 증거가 없어 유일 원인 판정은 보류한다.
- 검색: 로그인 정보 부재 확인. 사용자 등록이 필요한 경계다.
- 메일: 요청 시간·CEO 계정·휴지통 가설로 분석이 확장됐다. 상세 실패 원인은 미확정이다.

## 변경 범위와 최소 구현

- data_extraction/services/resume_uploader.py: Requests 응답 훅으로 Location의 원래 바이트를 percent-encoding. UTF-8/CP949와 기존 percent escape를 함께 보존하며 기존 수동 redirect 상한·허용 주소·내부망 차단 유지.
- auto_posting/sites/saramin.py 및 jobkorea.py: 기존 로그인/추가 인증 전환 대기는 보존하고, 선택 직전에 기존 컨트롤의 표시 대기를 추가. 이름/경력·유일성·원본 검증 보존.
- data_extraction/services/drive_inventory.py: 기존 분류에 Office 임시 파일 제외 추가. 실제 이력서와 지원 포맷 보존.
- 기존 관련 테스트 파일에 실제 실패 조건·변형·정상 사례를 추가한다.
- 최소 구현 게이트: 화면/분류 2단계 재사용, HTTP 주소 5단계 설치된 Requests response hooks 및 표준 urllib.parse. 새 라이브러리/서비스/실행 경로 없음.

## 보호 불변조건과 기준선

- 원본 파일, 업무 DB, 기존 장부, 후보자 신원 매칭, 현재 프로필, 정상 사이트 수집 및 기존 API 권한을 보존한다.
- 운영 DB는 shell-readonly의 exdigm_debug_ro/read_only on으로만 조사했다.
- 수정 전 공식 검사: uploader/incruit/jobkorea/search/operational records 83 passed.
- 추가 기준선: browser resume/Drive inventory/sync_drive_changes 27 passed.
- 실패 재현 검사 추가 → 원래 코드 실패 → 최소 수정 → 같은 검사 통과 → 전체 diff 리뷰 순서로 검증한다.

## 재개 정보

- 상태: 위 제품 코드 4개와 기존 테스트 4개 수정. 확대 검사 235 passed, 차이 축소 뒤 브라우저 경로 42 passed, 보호 계약 194 passed. 코드 리뷰 승인 finding 없음.
- 개발 worktree에 다른 작업의 프로젝트 보드 변경 6개 파일이 새로 나타났다. 해당 파일은 수정·스테이징·커밋 대상에서 제외한다.
- CEO Hermes의 기존 container 로그에서 12:52 요청이 인증 뒤 `company_email_read_failed / 메일 목록을 완전하게 불러오지 못했습니다.`로 끝난 사실을 확인했다. `_fetch_message`가 None을 반환한 분기까지 특정했으나 서버 거절과 UID 소실은 현재 기록으로 구분할 수 없다.
- 오류의 사용자·프로필 ID 기록 보완은 별도 비동기 질문으로 확인 중이다. 아직 해당 코드는 수정하지 않았다.
- 외부 검색 미등록 계정은 bk@exdigm.com이다. 해당 직원의 /accounts/settings/extension/에서 네 사이트 개인 연결이 필요하다. 기존 LinkedIn 성공 결과 15명은 그대로 둔다.
- 다음: 별도 승인 후 운영 반영 및 실패 링크 8건의 공식 장부 재처리를 진행한다. 메일은 읽기 거절/조회 도중 UID 소실을 구분할 운영 근거가 더 필요하다. 휴지통 검색 확장은 별도 제품 범위로 두고 임의 적용하지 않는다.
- 운영 배포, 장부 재처리, 인증 변경은 실행하지 않았다.

## 적용·검증 증거

| 대상 | 수정 전 실패 확인 | 수정 후 확인 |
|---|---|---|
| 사람인 | 지연 표시 조건에서 matches=0, 즉시 표시 성공 | 두 조건 모두 공식 download_resume의 PDF 결과 확인 |
| 잡코리아 | 숨겨진 버튼 조건에서 not unique, 즉시 표시 성공 | 두 조건 모두 공식 download_resume의 암호 ZIP 결과 확인 |
| 인크루트 | CP949 두 변형 UnicodeDecodeError, UTF-8 주소 이중 인코딩; ASCII 성공 | 실제 Requests 처리 계층을 거쳐 업로드 장부 DONE, FileData 연결, 업로드 1회 |
| Drive | 분류 변형 5개 및 공식 sync 단계가 임시 파일을 생성/대기열에 넣음 | 임시 파일 제외, 실제 문서 FileData/manifest 생성, 커서 정상 전진 |

- `scripts/debug_workspace.sh test tests/test_auto_posting_incruit_waits.py tests/test_auto_posting_jobkorea_references.py tests/test_resume_uploader.py tests/test_candidate_sourcing.py tests/test_operational_error_records.py tests/test_auto_posting_browser_runtime.py tests/test_inventory_01db_drive_tree.py tests/test_update_candidates_results.py --tb=short`: 235 passed, 7 warnings, 46.09초.
- 운영 원래 인크루트 링크 4개를 개발 코드의 `_download_resume_link`로 읽기만 재검증했다. UnicodeDecodeError는 사라졌고 인증 경로에 도달했다. 이후 개발/운영 복호화 키 분리로 InvalidToken에 막혔으므로 실제 파일 전달까지 통과했다고 판정하지 않는다.
- 운영 장부 상태를 바꾸거나 운영 비밀번호를 개발에 공급하지 않았다.
- 마지막 코드에서 `scripts/debug_workspace.sh test tests/test_auto_posting_browser_runtime.py --tb=short`: 42 passed.
- `scripts/debug_workspace.sh contracts`: 고정 기준 6ac315e930880406f6f7f9d489322b07b85e380f의 보호 파일 18개 유지, 194 passed.
- `scripts/debug_workspace.sh check`, `uv run --locked python -m tools.code_knowledge catalog_update`, 변경 8개 파일 `ruff check`, `git diff --check`: 모두 통과. 목차 파일 변경 없음.

## 코드 리뷰 계약

1. 원천: 주인님의 DB 오류 수정 요청, 본 문서의 현상 잠금·보호 불변조건, 현재 AGENTS.md 및 해당 기능 스킬.
2. 역할: 메일 이력서 링크를 기존 수집 장부에 전달하고, Drive에서 실제 문서만 기존 처리 대기열에 전달한다.
3. 경계: base 8c2ea773723757da4422e698ac8b34c86a0fd2f8에서 제품 코드 4개와 테스트 4개의 로컬 diff. 직접 호출자인 process_resume_upload/AutoPosting.main/sync_drive_changes 및 직접 분류 소비자까지만 확인한다.
4. 입력: 허용 사이트 HTTPS URL, HTTP Location 원래 바이트, 공식 사이트 페이지와 후보자 힌트, Drive 파일명·확장자·폴더 메타데이터. 기존 인증 필수조건은 유지한다.
5. 절차: 주소 검사 후 수동 제한 이동, 인증 전환 후 대상 유일성 검사와 공식 파일화, Drive 분류 후 기존 DB/manifest 및 커서 처리 순서 보존.
6. 출력: 지원 형식의 실제 이력서 바이트와 이름/MIME, 기존 장부 상태·FileData 연결; 정책 제외 파일은 새 처리 대상이 되지 않고 정상 문서는 계속 전달된다.
7. 보호: 내부 주소 차단, 10MB/이동 상한, 중복 업로드 방지, 정확한 지원자 선택, 기존 인증/추가 인증, 사용자 작업·업무 데이터·기존 오류 기록.
8. 비목표: 메일함 검색 범위 확대, 운영 계정 연결 변경, 운영 배포/장부 재처리, 프로젝트 보드 변경, 전체 이메일 성능 재설계.
9. 검증: 위 재현 테스트와 기존 성공 검사, 공식 debug_workspace 테스트 및 contracts/check, diff 검사. 외부 사이트 인증 뒤 실파일 전달과 실제 메일 서버의 실패 응답 구분은 아직 확인하지 못했다.

리뷰 관점은 변경 diff와 1차 호출/소비 관계다. 변경으로 보호 조건이 깨지는 실행 가능한 사례만 finding으로 승인한다. 알려진 운영 인증 경계와 502의 미확정 원인은 별도 미검증 항목이며 코드 리뷰 통과로 대체하지 않는다.

### 코드 리뷰 결과

- 승인된 finding이 없다. 계약을 바꿔야 하는 열린 리뷰 질문도 없다.
- Requests 응답 훅 이후에도 매 이동 전 HTTPS/주소 검사와 상한이 유지된다. 파일 업로드 장부·중복 처리 경로는 변경하지 않았다.
- 사이트 이름/경력 매칭·유일성·공식 파일 형식 검증은 유지했다. 로그인·추가 인증 관련 기존 대기도 보존했다.
- Drive의 신규 목록 수집과 변경분 수집이 같은 분류를 재사용한다. 제외 표시는 기존 decision_for_row 및 manifest 소비자로 이어진다.
- 운영 인증 뒤 실파일 전달과 당시 IMAP 응답의 상세 실패 조건은 검증하지 못했다.

## 재발 판정과 종료 경계

| 경로 | 판정 | 근거와 남은 일 |
|---|---|---|
| 한글 Location 처리 | 개발 범위 닫힘 / 운영 전체 전달 미검증 | 실제 Requests 회귀 검사, 원래 운영 링크 4개에서 UnicodeDecodeError 제거. 인증 뒤 파일 전달은 개발 키 분리로 미검증 |
| 사람인 준비 대기 | 개발 범위 닫힘 / 운영 전체 전달 미검증 | 원래 화면의 5초 지연과 같은 조건 재현, 공식 엔진 테스트에서 PDF 결과. 운영 장부 재처리 미실행 |
| 잡코리아 준비 대기 | 개발 범위 닫힘 / 과거 단일 원인 미검증 | 같은 오류를 만드는 지연 조건 회귀 통과. 당시 화면 상태는 기록에 없어 단정하지 않음 |
| Drive Office 임시 파일 | 신규 유입 경로 개발 범위 닫힘 | 공식 sync 단계에서 임시 파일 제외와 정상 문서 DB/manifest 전달 검증. 기존 실패 기록은 보존 |
| 외부 검색 | 열림 | 해당 직원의 네 사이트 계정 등록 필요. 다른 직원 인증을 대체 사용하지 않음 |
| CEO 메일 502 | 열림 | 인증 이후 개별 메일 fetch의 None 분기 확인. IMAP 거절과 UID 소실은 기록만으로 구분 불가 |

- 전체 문제해결 게이트는 미완료다. 운영 배포·실제 재처리·사용자 연결이 남아 있으며 완료나 운영 재발 차단으로 보고하지 않는다.
- 제품 커밋·push·운영 배포는 하지 않았다. 원래 운영 main 체크아웃은 여전히 clean이다.
- 사용자/프로필 식별자 기록 추가 질문은 답을 받기 전까지 보류한다. 기존 오류의 주체를 추정해 DB에 소급 기입하지 않는다.
