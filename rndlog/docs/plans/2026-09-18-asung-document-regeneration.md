# 아성 문서 재작성 및 다운로드 등록

## 요청과 잠금

삭제된 파일의 복구가 아닌 신규 문서 재작성. 2026년 연간 계획, 최근 완료된 3개월 2026.06.01~08.31 기록, RNDLOG 회사 자료 다운로드 등록.
6월 실사는 문제 없이 대응했다는 의뢰인 설명을 관리 이력으로 반영한다. 정확한 실사일과 기술 시험 결과는 만들지 않는다.

정본: main chaconne@49.247.192.127의 /srv/consolidation/data/files-standby/workspace/companies/주식회사 아성/.
회사 PK 5977dd46-cc2b-4282-bf3d-486c96b688fd. 기준 코드 HEAD 994ef3b. 기존 .agents/, .claude/, AGENTS.md, CLAUDE.md 미추적 상태와 모든 제품 코드는 변경하지 않는다.

기준선: 회사 산출물 0, 수신 ZIP 및 압축해제 6건 등록 후 원본 7건. 원본 다운로드의 크기/SHA 일치. 관리 케이스·공개/승인 상태 보호.
최소 구현 게이트 2단계: 공통 rnd_docset/rnd_docx의 계산·문서 블록과 종류별 DOCX 샘플을 재사용하는 작업 폴더 제작 어댑터. 신규 제품 기능·배포 없음.

## 제작 경로

고객 원본 → 리서치 및 회사 데이터 → 공통 DocSet → 연간 계획/현재 재작성일 적용 → 종류별 참조 패키지 기반 DOCX 39건 → packaged render_docx 전체 PNG → canonical 신규 버전 → FileAsset 메타데이터 → 기존 company_detail/개별/전체 ZIP.
실제 인력이 없어 전담 역할 1칸의 산정 모델. 현행 제헌절 복원을 반영하여 6/7/8월 21/22/20일, 168/176/160시간, 합계 504시간. 실제 수행·지급으로 확정하지 않음.

## 현재 결과와 남은 확인

- 원본 7건 DB·정본 보존 및 다운로드 크기/SHA 검증 완료.
- DOCX 39건 작성, 패키지/스타일/주차/금액/모든 XML 속성 검사 완료. 발견한 R1~R7 제작 결함 수정 후 최종 v5 전체 85쪽 렌더·전수 검수. final-qa.json에 최종 DOCX SHA와 모든 PNG를 연결.
- main deliverables/{drafts,final}/20260918_재작성/ 신규 저장. 218개 제작·검증 자료 저장, transfer-manifest의 217개 파일 크기/SHA 일치. 기존 파일 덮어쓰기 없음.
- FileAsset 78개 추가(작업본39 + 내부 다운로드39), 아성 총85개. generated/needs_review/고객 미공개 및 실제 인명 생성자 없음. 회사·케이스·원본7개·타사224개 메타데이터 보호 기준선 동일.
- 공식 company_detail 응답200 및 모든 39개 문서/7개 원본 다운로드 링크 확인. company_download 개별46개 응답200 및 크기/SHA 일치, 전체ZIP 응답200 및 39개 내부 파일명/크기/SHA 일치. 비로그인 요청302. 기존 활성 관리자 역할과 RequestFactory를 사용하는 서버 검증이며 브라우저 인증 검증 아님.
- 실제 핸들러 ZIP을 조정실로 받아 재대조. 1,450,475바이트, SHA a0b27d50917adf618c7de2b4fc6bf98b9e9ba34786a003f2940bb36a3faa08e3. 아성 자료창 ‘산출물 전체 ZIP 다운로드’에 기존 기능으로 연결.
- main research/재작성_20260918_a0b4bce5/db-before.json에 회사·케이스·원본과 타사 FileAsset 224건의 메타데이터 해시 기준선 저장. 컨테이너는 원본 디스크를 직접 마운트하지 않으므로 기준선 파일은 main 호스트에 저장함.
- 숨김 Chrome 전용 프로필은 RNDLOG Google 로그인 화면. desktop/foreground unchanged. 인증 세션을 복제하거나 생성하지 않았음. 전용 PID12284만 stopped=true로 종료. 실제 브라우저 저장은 미검증.
- 운영 코드 HEAD994ef3b2a887fa32d829c96cb19eabfa2fa27660 및 원래 미추적4개 항목 불변, web/nginx running 및 공개HTTPS200. 앱 배포·외부 발송·예약 변경 없음.
- 동일 범위 마지막 코드 리뷰에 승인 finding/열린 material contract question 없음. 등록 후 필수 서버 경로 검증 통과. 제작·등록·서버 다운로드는 완료, 사용자/고객 사실 대조 및 실제 로그인 화면 클릭은 별도 남음.

재개 작업 폴더: C:/Users/chaconne/projects/rndlog/tmp/asung-20260918/.
artifact.md는 사실/서식/범위/리뷰 정본, company-data.json은 내용과 산정 입력, inventory.json은 39건 크기/SHA. 인수 결과는 고객사 research/재작성_20260918_a0b4bce5/acceptance.md 및 verify-result.json 참조. case와 공개/승인 상태는 그대로 유지한다.

다음 재개는 실제 등록 연구원/책임자 및 원시 자료를 받아 사실 대조하거나, 전용 Chrome 프로필의 일회성 로그인 뒤 동일 RNDLOG 자료창의 버튼 클릭·ZIP 저장을 확인하는 범위다. 이미 완료된 등록 명령은 중복 실행하지 않는다. controlroom에는 타 업무 미커밋 변경이 있어 add -A/설치/타 저장소 동기화를 포함한 controlroom push를 실행하지 않았고 원래 작업을 보존했다. 프로젝트 계획은 로컬에 저장하고 고객사 정본에도 인수 결과를 보존했다.

## 2026-09-19 회사 목록 기본정보 누락 보완

사용자 화면 제보 및 `수정해` 승인으로 확인된 기본정보 빈칸을 보완한다. 기존 문서 재작성·DB 파일 등록을 재실행하지 않는다. 문서에 확인된 사실을 넣고도 회사 정보 보존 조건을 빈 값에 일괄 적용하여 목록 등록을 누락한 것이 원인이다.

승인 범위: 아성 ClientCompany의 비어 있는 사업자번호(7208602130), 법인번호(2850110462303), 대표(양세훈), 사업장 주소만 채우고 updated_at을 갱신한다. ResearchUnit에 원본 인정서 그대로 연구개발전담부서/제2024153619호/최초 인정 2024-05-23/소재지를 신규 1건 연결한다. 현행 유효성을 별도로 조회한 것이 아니므로 조직 상태는 기본 needs_check이며 확인일을 만들지 않는다. 연구소장·전담부서장·연구인원·승인·고객 공개·회사 관리 상태·연락처는 변경하지 않는다.

기준선: 2026-09-19 조회에서 위 회사 4칸은 빈 값, 연구조직0, 파일85(원본7), 관리중이다. main Git 미추적 .agents/.claude/AGENTS.md/CLAUDE.md 보존. 모든 research_management 모델의 다른 회사/기존 조직/파일/관리/승인 데이터를 행별 정렬 SHA로 잠그고 아성 회사 전체와 조직0을 복구 가능한 JSON으로 보관한다. 원본7의 물리 파일 SHA도 쓰기 전에 확인한다.

최소 구현 게이트 4단계: 회사 폼/뷰와 management 명령 검색에서 일반 사실 보완 API는 없고 기존 상태 편집만 확인. 기존 Django 모델·필드 검증·transaction과 공식 accounts.views.rndlog_shell/company_download 소비자를 재사용한다. 작업 폴더 update_company_facts.py만 추가하며 제품 코드·새 API·의존성·배포 없음.

공식 연결: 원본2건 → 명시적인 확인 사실 → 기존 ClientCompany/ResearchUnit 단일 트랜잭션 → /rndlog/ accounts.views.rndlog_shell의 recognized_units Prefetch → index.html 목록. ZIP은 기존 company_download→자료 게이트웨이에서39건 모두 크기/SHA 대조. 기준선 변경·다른 기존 값·중복 조직이면 쓰지 않고 중단하고, 커밋 전 소비자 검증 실패는 트랜잭션 전체 롤백한다.

리뷰 계약: base는 새 작업 스크립트 없는 현 상태, head는 update_company_facts.py. 경계는 스크립트와 기존 모델/공식 목록/다운로드 소비자. 입력은 승인된 정식 회사 ID와 원본 사실이며 부서장/인원 추정은 금지. 보호 기준선/권한·프로필·원본·타회사 불변과 정확한3개 목록 값 및 기존39문서 ZIP을 필수 검증한다. 변경 diff·1차 소비자·지침 검토를 주 에이전트가 직접 수행한다. 숨은 Chrome 프로필 로그인 미확보 시 서버 목록 검증과 실제 로그인 화면 검증을 구별한다.

사전 리뷰 R1: 새 스크립트에서 전체 ZIP URL을 company_download_all 이름으로 조회하면 실제 accounts/urls.py의 company_zip과 불일치하여 커밋 전 검사가 NoReverseMatch로 실패한다. 기존 company_zip 이름을 사용하도록 수정했다. 사용자 목적·기준 base·범위는 그대로이며 수정한 파일 전체를 재리뷰한다.

사전 검증/리뷰 R2: readonly preflight에서 company_download 응답.close가 request_finished를 보내고, Django close_if_unusable_or_obsolete가 atomic의 autocommit 차이를 감지하여 DB 연결을 닫았다. 그 뒤 메타데이터 조회가 `the connection is closed`로 실패했다. 운영 이미지의 두 함수 구현을 직접 확인했다. 응답 수명을 transaction 종료 뒤 finally로 연결해 성공/실패 모두 자원을 정리하되 커밋 전 연결을 닫지 않게 했다. 첫 시도는 읽기 전용 단계로 회사/조직 DB 쓰기0이며 빈 검사 폴더만 남았다. 실패 stderr를 정확히 보이게 했고, 빈 폴더만 읽기 전용 검사를 재개할 수 있으며 기존 검사 결과 덮어쓰기는 금지한다.

수정 전 검증: 수정한 공식 preflight 종료0. 전체14개 research_management 모델의 보호 SHA와 회사 전체/연구조직0을 preflight.json에 저장했다. 공식 회사 목록200/빈 칸 행과 공식 ZIP200/문서39개 각각 크기/SHA 통과. 응답 종료 순서 수정 후 DB 연결 오류가 재현되지 않았다. 마지막 코드 리뷰는 변경 파일 전체와 기존 모델/뷰/라우트/응답 종료 직접 소비자를 확인했고 승인 finding0, 열린 material contract question0이다. R1/2는 수정·검증됨.

현재 단계: 수정 전 기준선 보관·사전 검증·코드 재리뷰 완료, apply 실행 대기. 고객사 research/기본정보보완_20260919_a0b4bce5/에 preflight/apply 결과를 보관한다.
