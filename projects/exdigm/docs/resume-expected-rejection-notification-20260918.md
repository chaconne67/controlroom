# 이력서의 정해진 접수 실패와 컨설턴트 보완 안내

작성일: 2026-09-18 KST. 상태: 운영 반영·지정 원본 종결·담당자 웹 알림 1회 전송 및 보존 대조 완료.

## 원하는 결과

주인님의 판단: 원본에 등록 필수 정보가 없는 경우는 정해진 업무상 접수 실패다. 운영 장애나 버그로 분류하지 않고 담당 컨설턴트에게 누락 항목을 안내해 이력서를 다시 받도록 해야 한다.

원본의 정보 부족이 확인된 입력은 구체적인 접수 실패 사유로 종료하고 자동 재시도를 멈춘다. 기존 앱 알림으로 해당 담당자에게 1회 보완 요청을 전달한다. 회사별 경력이 있는 상세 원본을 다시 접수하면 기존 공식 추출·저장 경로로 처리한다.

주인님의 추가 방향: 알림 본문에서 이메일을 지칭하는 **“이정희 입사지원서”라는 텍스트 자체에 링크를 건다.** 이 구절을 누르면 Exdigm의 해당 수신 메일 상세 화면이 열린다. 이 요구는 앞서 검토한 별도 `열기` 버튼 연결 방식을 대체한다. 전체 알림 목록과 상단 알림 미리보기에서 같은 본문 링크를 표시한다.

원본에 있는 사실을 AI가 누락한 경우, 형식·출처 계약 위반, 제공자 장애와 저장 오류는 실행 오류로 보존한다. 오류 문자열만으로 업무상 접수 실패라고 단정하지 않는다.

## 확인 근거

- FileData: `a1d7439b-3428-4fd9-a1f4-4a00d6c08e5c`. 최초 오류: 2026-09-18 11:48:15 KST, `resume_knowledge_contract_failed`, `extracted_content 필수 항목 누락: 경력`.
- 인크루트 이메일 다운로드 링크에서 받은 `.doc`은 UTF-16 HTML이다. 원본 파일 해시가 최초 수신 해시와 같고 원본 표시 텍스트와 보관된 전처리 전 텍스트도 공백/BOM 제외 완전히 같다. 실제 경력 필드는 총 연수·개월 요약뿐이다.
- 담당 계정은 `bk@exdigm.com`, 담당 사용자 표시 이름은 `ChunBK`, 사용자 ID는 `d68a00e8-f297-487a-9818-ffa73a82e973`다. 계정·사용자는 활성 상태이고 앱 알림 전달이 활성화돼 있다. 해당 원본의 보완 안내 알림은 없다.
- 연결된 수신 메일 장부는 `1b3f1f77-f099-40fd-86c2-bb91f380a0d8`, 수신 시각은 2026-09-18 11:46:42 KST다. 텍스트·HTML 본문이 보관돼 있다. 기존 `email_view_detail`의 공식 URL은 `/email-view/1b3f1f77-f099-40fd-86c2-bb91f380a0d8/`다. 공식 읽기 전용 셸에서 실제 담당 사용자로 기존 뷰를 실행해 200 및 메일 본문 영역 표시를 확인했다. HTTPS 로그인 브라우저에서 이 메일을 직접 열어 본 검증과는 구별한다.
- 이 원본의 후보자 연결과 Resume 행은 없고 등록 완료 시각은 비어 있다. 자동 재처리는 종료됐으며 원본과 실패 기록을 보존했다.
- 현재 D8의 필수 내용 검사는 원본의 정보 부족도 ValueError로 중단한다. `runners.text_to_pipeline_result`는 이를 일반 knowledge 계약 실패로 기록한다. 운영 오류 수집기는 종료된 LLM 실패를 수집한다.
- 기존 `data_decision_policy`에는 `missing_career`, `missing_name`, `missing_contact`, `missing_required_fields`가 있다. 연락처 누락의 notify 결정과 Mailplug 원본의 담당자 관계도 존재하지만, 현재 수령 담당자에게 보완 요청을 만드는 연결은 없다. `notify_manual_resume_upload_failed`는 프로젝트 화면에서 수동 업로드한 원본에만 알림을 보낸다.
- 알림 목록 `projects/templates/projects/notifications.html`과 상단 알림 `projects/templates/projects/partials/notification_bell_content.html`은 현재 제목·본문·시각을 하나의 링크로 감싼다. 본문 일부에 링크를 넣을 때 링크가 중첩되지 않도록 해당 알림의 표시 구조를 조정해야 한다. `projects/views/notifications.py`의 `notification_open`은 본인의 알림만 조회하고 읽음 처리 후 `action_url`로 이동한다. 이 진입점을 그대로 재사용한다.

## 변경 범위와 공식 경로

서버: `chaconne@49.247.202.197`. 수정 위치: `/home/chaconne/exdigm-debug`. 운영 위치: `/home/chaconne/exdigm`.

현재 경로는 FileData 원문 → `runners.text_to_pipeline_result` → D8 원천 항목 지도·내용 추출 → 필수 내용 검사 → 후보자 필드 변환 → 공통 저장이다. 이번 변경은 원본의 필수 정보 부족이 확인된 분기를 기존 접수 판정과 알림으로 연결한다.

1. `projects/services/recommendation_resume_ssp.py`의 기존 원천 지도와 출처가 있는 추출 결과를 사용해 필수 정보 부재와 출력 계약 위반을 구별한다. 원본에 경력 근거가 없다는 판정은 기존 AI 의미 해석에 맡긴다. 경력 숫자·회사명을 스크립트가 추정하지 않는다. 실제 정보 부재를 직접 호출자가 식별할 수 있는 구조로 전달하고 정상 생성·형식·출처 검사는 유지한다.
2. `data_extraction/services/runners.py`에서 확인된 자료 부족을 기존 데이터 사유로 종료한다. 이 분기를 LLM 재시도 실패로 기록하지 않는다. 원문·원본 정보·기존 후보자 소유권과 실제 실행 오류 분기는 보존한다.
3. `data_extraction/services/filedata_candidate_context.py`의 기존 알림 기능을 재사용한다. Mailplug 원본의 수령 담당자를 `MailplugUploadRecord.account.user`로 찾고 수동 유입은 확인된 업로더를 사용한다. 사용자·원본 기준으로 중복을 막고 누락 항목과 이력서 재수령 행동을 알린다. 메일 유입의 `action_url`은 확인된 `MailplugUploadRecord.message_check_id`로 `reverse("email_view_detail", kwargs={"pk": message_check_id})`를 사용해 만든다. 메일 번호·원본 번호·본문에서 링크로 표시할 정확한 구절을 기존 `callback_data`에 기록한다. 본문은 일반 텍스트로 유지한다. 기존 메일 상세 뷰의 본인 계정 조회 제한을 유지한다. 담당자나 메일 연결을 확인할 수 없으면 이를 추정해 링크나 수신자를 만들지 않는다.
4. `projects/services/operational_errors.py`에서 확인된 업무상 자료 부족 사유를 운영 오류 수집에서 제외한다. 일반 `resume_knowledge_contract_failed`와 실제 계약·제공자·저장 실패는 그대로 수집한다.
5. `projects/models.py`의 Notification 표시 기능과 두 알림 템플릿에서 본문 링크를 연결한다. 본문을 링크 앞 텍스트·지정 구절·뒤 텍스트로 나누는 최소한의 공통 표시 처리를 둔다. 지정 구절의 링크는 기존 `projects:notification_open`을 사용해 읽음 처리와 메일 이동을 유지한다. 링크가 있는 본문을 다른 링크 안에 넣지 않으며 일반 알림의 기존 열기·읽음·다운로드 동작을 유지한다. 상단 미리보기의 본문 길이 제한이 구절의 링크를 깨뜨리지 않도록 한다. HTML을 본문에 저장하거나 전체 본문에 `safe`를 적용하지 않고 Django의 자동 이스케이프를 유지한다. 새 DB 필드나 의존성을 추가하지 않는다.
6. 위 직접 분기와 소비자의 기존 테스트에 회귀 검사를 추가한다. 필요한 경우 기존 저장 종료 분기의 알림 호출만 같은 범위에서 연결한다. 기존 데이터 판정·이름/연락처 매칭·학력 선택 정책을 바꾸지 않는다.

최소 구현 게이트: 접수 실패 판정과 담당자 연결은 2단계에서 멈춤. 실제 `rg`와 파일 조회로 `data_decision_policy.DataState`, D8의 `source_map.work_experience.records`, `MailplugUploadRecord.account.user`, 기존 `create_notification` 및 원본별 수동 알림 중복 검사와 운영 오류 수집을 확인했다. 이 구현을 재사용하며 새 알림 채널·모델·의존성·DB 테이블·별도 반복 작업을 만들 필요가 없다. 식별 가능한 자료 부족 전달과 기존 담당자 알림 연결을 추가한다.

최소 구현 게이트: 본문의 부분 링크 표시는 4단계에서 멈춤. `body_parts|body_link|display_body` 검색과 Notification 및 두 알림 템플릿 조회로 기존 알림에 부분 링크 표시 기능이 없음을 확인했다. 이미 있는 `callback_data`, `action_url`, `notification_open`과 Django 템플릿의 링크·자동 이스케이프를 재사용한다. 본문을 안전하게 나누는 공통 처리와 직접 소비 템플릿만 추가·조정한다. 전체 본문을 HTML로 바꾸는 기능이나 별도 이동 경로는 필요하지 않다.

## 기준선과 보호 조건

- 시작 상태: 운영 main과 debug detached HEAD 모두 clean, 커밋 `4df3adb6663df138ac4a07c2813095ae0f43576a`. 조정실 controlroom의 다른 작업 6개 수정은 보존한다. 이 계획과 README 색인만 이번 문서 범위다.
- 보호: 원본 파일과 원문, 후보자 매칭·수동 입력·대표 이력서 선택, 기존 정상 추출과 저장, 학력 선택 정책, 실제 오류의 수집과 재시도, 일반 알림의 열기·읽음·다운로드, 알림 본문의 HTML 이스케이프, 기존 검사 기대값, DB 권한과 외부 인증.
- 변경 전 공식 검사: `scripts/debug_workspace.sh test tests/test_realtime_file_status_source.py tests/test_operational_alerts.py data_extraction/tests_data_decision_policy.py tests/test_optional_resume_education.py tests/test_application_resume_upload.py --tb=short` → **90 passed, 8 warnings**.
- 추가 성공조건: 실제 원본의 정보 부족은 한 번 판정 후 재시도하지 않고 후보자/이력서를 만들지 않는다. 정확한 담당자에게 보완 알림 1개가 전달된다. 알림 목록과 상단 미리보기의 본문에서 **“이정희 입사지원서” 자체가 링크로 표시되고**, 클릭하면 읽음 처리 후 그 원본을 받은 수신 이메일이 열린다. 메일 목록이나 다른 메일을 대상으로 삼지 않는다. 같은 입력의 반복 실행·큐 재분류에서도 알림이 중복되지 않고 운영 오류가 새로 생기지 않는다. 정보가 있는 정상 원본과 실제 출력 누락·제공자 장애는 기존 결과를 유지한다. 메일 링크의 본인 계정 제한은 `tests/accounts/test_email_views.py`의 기존 권한 검사로 보존한다.
- 승인 후 수정 전후 같은 기준선 및 직접 영향 D8/알림·메일 권한 검사, 보호 계약, Django check·catalog_update와 메인 에이전트의 code-review-loop를 수행한다. 변경 전 일반 알림의 목록·상단 표시 기준선도 확인한다. UI는 같은 개발 runserver의 `https://dev.exdigm.com`에서 본문 링크와 실제 메일 이동을 직접 확인한다. 실제 원본과 원인이 다른 정상 원본을 공식 처리 경로에서 대조하며 운영 쓰기는 분리한다.

## 승인받을 운영 조치와 이번 안내 문구

코드 수정·검증·리뷰·기록·커밋을 수행하고 검증된 판본을 공식 `scripts/deploy/deploy.sh prod`로 운영에 반영한다. 이 계획에 명시한 한 원본만 복구 가능한 백업과 직전 상태 비교 후 기존 공식 접수 실패·알림 경로로 처리한다. 이번 원본을 후보자 등록 성공으로 바꾸거나 다른 종료 원본을 일괄 재처리하지 않는다.

수신자: **ChunBK / bk@exdigm.com**. 전달 방식: 기존 Exdigm 앱 알림 및 활성화된 웹 알림 전달.

제목: **이력서 보완 요청 — 경력 상세 누락**

내용: 인크루트에서 받은 **[이정희 입사지원서](https://office.exdigm.com/email-view/1b3f1f77-f099-40fd-86c2-bb91f380a0d8/)**에는 총 경력 기간만 있고 회사별 경력 상세가 없어 후보자 등록을 보류했습니다. 회사별 근무기간과 담당업무가 포함된 상세 이력서를 다시 받아 업로드해주세요. 대상 파일: 이정희_입사지원서_20260918.doc.

본문의 **“이정희 입사지원서” → 원래 수신한 이메일**: `https://office.exdigm.com/email-view/1b3f1f77-f099-40fd-86c2-bb91f380a0d8/`. 실제 알림에서는 기존 알림 열기 경로를 거쳐 읽음 처리 후 이 URL로 이동한다. 수신 계정인 ChunBK로 로그인한 상태에서 확인한다. 기존 알림과 메일 상세 화면을 재사용하며 새 메일 화면이나 외부 Mailplug 링크 규칙을 만들지 않는다.

현재 운영 오류 `43c83942-4630-ca5d-999b-fba09c80c6a1`의 최초 발생 기록은 보존하고, 실제 보완 안내가 전달된 뒤에만 정해진 접수 실패로 처리했다는 후속 결과를 추가한다. 후보자 등록은 상세 이력서 재접수 이후의 별도 업무다.

## 재개 정보

- 승인: 본문 링크 방향을 포함한 통합 계획에 대해 주인님이 `수정해`로 실행 지시했다. 코드·검증·리뷰·커밋·공식 운영 배포·지정 원본 1건 보완 알림 범위를 진행한다.
- 변경 전 서버 기준선: 운영은 clean main `4df3adb6`. debug에 별도 미배포 화면 커밋 `4ac2f0b2`가 있어 `refs/heads/preserve/resume-verification-markdown-20260918`에 보존했다. 이번 수정은 기존 운영 `4df3adb6`의 detached HEAD에서 분리했고 앞선 미배포 커밋은 운영에 포함하지 않았다. 보존 참조는 계속 `4ac2f0b26027c58c96fda142e8c7e690eb340539`다.
- 수정 전 기준선: 기존 추출·저장 90개 통과. 알림·메일 소비자까지 확장한 동일 검사 142개에서는 139개 통과 및 기존 실패 3개를 확인했다. 두 알림 테스트는 `submit_to_client` ActionType 기준 데이터가 없고, 휴지통 메일 테스트는 기존 구현의 `BODY.PEEK[]`와 검사 기대값 `RFC822`가 다르다. 기존 검사·기대값은 유지한다.
- 구현: 원문 경력 기록 부재를 확인한 intake 분기를 별도 자료 부족 판정으로 연결했다. 원문 경력이 있는 출력 누락은 일반 계약 실패로 유지한다. 기존 자료 부족 저장 분기에도 담당자 보완 안내를 연결했다. Notification의 기존 JSON 연결 정보와 두 템플릿으로 본문 구절에 링크를 표시하며 기존 읽음·메일 권한 경로를 사용한다.
- 확인된 실제 수신 메일 제목은 `[지원자 알림] 이*희 / 재경총괄 임원`으로 마스킹돼 있다. 표시 문구는 확인된 원본 파일명에서 날짜 접미사·확장자를 제외해 `이정희 입사지원서`로 사용하며 후보자 신원 매칭에는 사용하지 않는다.
- 실제 AI 대조: 문제 원본의 기존 추출 경로는 경력 필수 항목 누락 ValueError를 재현했다. 수정 경로는 `missing_career` 자료 부족으로 종료했다. 원인이 다른 실제 정상 원본은 회사별 경력 1건을 포함한 완성 knowledge를 생성했다. 원문은 `.debug`의 0600 파일로만 보관하며 문서·GBrain·Git에 넣지 않았다.
- 화면 확인: 공식 개발 runserver의 알림 목록과 상단 미리보기에서 `이정희 입사지원서` 본문 링크를 실제 클릭해 정확한 수신 메일로 이동했다. 읽음 처리·HTML 이스케이프·본인 메일/알림 권한 제한은 직접 검사로 확인했다. 1440/390px 화면·CSS 200·파란색 및 밑줄·가로 넘침 없음과 숨은 데스크톱/전경 창 유지 확인. 기존 개발 사본의 직원 아바타 미디어 누락 404와 페이지 이동에 따른 heartbeat 취소는 이번 변경과 별도로 확인·보존했다.
- 검토: `4df3adb6`를 기준으로 이번 10파일 및 직접 소비자를 메인 에이전트가 검토했다. 과거 메일 파일을 수동으로 재사용했을 때 이전 메일 수신자를 먼저 고르는 결함을 회귀 검사로 재현·수정했다. 명시된 수동 업로더를 우선하며 자료 부족 저장·알림 생성은 같은 DB transaction으로 처리한다. 갱신 diff 재리뷰에 남은 승인 finding과 계약 질문은 없다.
- 최종 검사: 기존 90개를 포함한 직접 영향 101개, 기존 알림 목록/열기/다운로드와 메일 상세 소비자 44개, 고정 보호 계약 216개 통과. 기존 알림 테스트 2건은 운영·개발 데이터를 바꾸지 않고 개발 테스트 DB에 기존 `submit_to_client` 기준 데이터만 준비해 같은 기대값으로 통과했다. 메일 휴지통의 기존 `BODY.PEEK[]`/`RFC822` 차이는 변경 범위 밖으로 남겨 두었다. Django/Ruff/diff 검사 통과, 코드 지도 current/valid·broken references 없음.
- 프로그램 커밋: `4795d1ece34cf64502f4642295bdccf34da5e0bf` — `fix(extraction): notify owners of incomplete resumes with inline email links`. 공식 `scripts/deploy/deploy.sh prod`가 2026-09-18 13:34:52 KST에 `prod ok 4795d1ec`로 종료했다. GitHub main·운영 main·debug detached HEAD가 같은 판본이며 clean 상태다. 실제 앱·SSE·알림 전달 컨테이너의 `/app/.source-commit`도 이 판본이다. Swarm 서비스 5개는 1/1, 운영 작업자·지원 11개 active/drain off, HTTPS 응답 200이다.
- 운영 조치 직전 공식 읽기 전용 DB에서 역할 `exdigm_debug_ro`, transaction read-only on을 확인했다. FileData 전체 행 SHA-256 `925510146aea64a8626cf82c863a7d7af7e371120760c22aa016bf86ab87982d`가 최초 기준선과 같았다. 담당자·메일 관계 1건, 보완 알림 0건, 후보자·Resume 0건과 기존 오류 pending/이력 0건을 다시 확인했다.
- 복구 백업: 운영 서버 `/home/chaconne/exdigm/runtime/expected-rejection-20260918-approved-one/backup.json`에 변경 전 FileData·메일 업로드 장부·운영 오류와 변경하지 않은 SourceArtifact·수신 메일 참조 스냅샷을 보관했다. 디렉터리 0700/파일 0600이며 SHA-256은 `0d56d8d792b656076b635dba3e45e4ee51b9d1f109e7ba39510d73b865418145`다. `receipt.json`은 이번에 생성한 알림·dispatch ID와 결과를 포함한다. 복구 시 변경한 세 행의 필드만 before 값으로 되돌리고 이번 알림 ID만 삭제한다. 이미 전달된 웹 이벤트는 회수되지 않는다.
- 백업 준비의 nullable FK outer join에 전체 FOR UPDATE를 적용한 조회는 PostgreSQL이 거절했다. 원본 상태 변경과 알림 생성 이전에 transaction이 종료됐으며 빈 백업 디렉터리만 남았다. 장부 자체로 행 잠금을 제한하는 Django `select_for_update(of=('self',))`로 준비 조회를 바꾼 뒤 동일 기준선 비교·백업을 완료했다. 제품 추출 경로는 이 준비 쿼리를 사용하지 않는다.
- 지정 원본만 기존 `close_resume_for_missing_fields`로 `missing_career` 종결했다. 자동 처리 큐 false·재시도 false·LLM 실패 표식 해제·후보자/Resume 미생성을 확인했다. 새 알림 ID는 `d34293e5-095e-4f50-b3c2-b533d6117ddb`, 웹 dispatch ID는 `498e309d-27d4-48d7-bd69-960ec378f49f`다. 실제 수신자 ChunBK, 본문 링크 문구 `이정희 입사지원서`, 원래 수신 메일 상세 URL을 확인했다. 별도 메일·Telegram은 보내지 않았다.
- 실제 전달: 알림은 2026-09-18 13:38:01.597 KST 생성됐고 기존 운영 알림 전달기가 13:38:05.033 KST에 web/SENT·오류 없음으로 기록했다. 전송 확인 뒤에만 기존 `record_processing_result`로 운영 오류 `43c83942-4630-ca5d-999b-fba09c80c6a1`에 처리 성공 이력 1회를 추가했다. 이 결과는 자료 부족 종결과 안내 전달이다. 후보자는 미등록 상태로 유지된다.
- 독립 사후 조회: 같은 공식 read-only 경로에서 보완 알림 정확히 1개·web/SENT·담당자 일치·미열람 상태와 큐 종료를 확인했다. FileData는 선언한 종결 관련 필드만, 메일 업로드 장부는 안내 시각 관련 필드만 변경됐다. SourceArtifact·원문·수신 메일 행은 그대로다. 최초 운영 오류의 내용·유형·발생 시각은 그대로이며 processing_status·processing_history·updated_at만 바뀌었다. 실제 담당자 권한으로 기존 메일 뷰를 실행해 200·본문 표시를 확인했다. 담당자 로그인 HTTPS 브라우저에서 원본 메일을 클릭한 검증이나 담당자의 실제 열람을 주장하지 않는다.
- 정리: 이번 개발 runserver와 소유 posting worker를 종료했고 개발 전용 검증 사용자·계정·메일·파일·알림 2개 및 임시 로그인 정보 파일만 제거했다. 기존 개발 사본과 미배포 UI 커밋, 사용자 작업은 보존했다. 숨은 브라우저 세션은 정지했으며 화면 증거는 남겼다.
- 공유 기록: GBrain `incident/exdigm-incruit-summary-resume-missing-work-20260918`, `project/exdigm-extraction-pipeline`, `project/exdigm-resume-intake-domain-handoff`의 기존 내용을 보존하면서 기대 실패·담당자 책임·본문 링크 계약과 실제 배포/전송 근거를 반영했고 다시 조회해 저장을 확인했다.
- 남은 업무: 담당 컨설턴트가 회사별 경력 상세가 포함된 이력서를 다시 받아 업로드한다. 이번 승인 범위의 구현·검증·운영 반영·안내 전달은 끝났으며 다른 원본의 일괄 재처리나 후보자 등록은 실행하지 않았다.
