# 이력서 검수 마크다운 표시 수정 — 2026-09-18

상태: 개발 수정·실제 화면 검증·코드 리뷰 완료. Exdigm 수정본은 디버깅 서버에 커밋했으며, 운영 배포는 별도 승인 대기다.

## 요청과 범위

주인님의 요청은 첨부 후보자 상세 화면의 “마크다운 포맷 표시 버그” 수정이다. “이력서 데이터 검수 → 종합 판단”에 저장된 검수 결과의 굵게 표시와 목록 기호가 문자 그대로 노출됐다.

수정 목표는 기존 원문을 유지하며 강조와 목록을 정상 표시하는 것이다. 수정 범위는 후보자 상세의 검수 출력, 기존 검색 모달의 마크다운 함수, 공용 스크립트 로딩과 직접 회귀 검사다. 추출·검수 AI 프롬프트·후보자 데이터·검색 상태·운영 서비스는 변경하지 않았다.

## 기준선과 보호 조건

- SSH: chaconne@49.247.202.197.
- 운영 /home/chaconne/exdigm: 시작 시 clean main 4df3adb6663df138ac4a07c2813095ae0f43576a.
- 디버깅 /home/chaconne/exdigm-debug: 같은 clean detached HEAD. origin/main도 동일했다. fetch와 detached 갱신 후 수정했다.
- 추가 성공조건: 첨부와 같은 굵게 표시·별표 목록을 정상 표시하고, 첫 로딩과 실제 HTMX 부분 갱신에서 같은 결과를 낸다.
- 보호 조건: 저장된 summary·후보자 정보·검색 동작·사용자 입력의 문자 출력·코드 내부와 이스케이프된 별표·임의 HTML 비실행.
- 기준선 검증: 아래 직접 영향 검사 19개를 수정 전 실행하고 수정 후 같은 검사를 재실행했다.
- 조정실 controlroom의 다른 변경과 동시에 작성된 이력서 접수 실패 안내 문서·README 링크를 보존한다. 이 작업의 문서와 README 추가 행만 저장한다.

## 최소 구현과 공식 경로

최소 구현 게이트: 2단계에서 멈춤 — 기존 renderAssistantMarkdown을 재사용했다.

실제 rg 검색에서 projects/templates/projects/partials/candidate_search_modal.html의 renderer가 유일한 제품 마크다운 구현임을 확인했다. 별도 파서나 의존성을 만들지 않고 candidates/static/candidates/assistant-markdown.js로 옮겨 두 화면이 함께 사용하게 했다. Tailwind의 candidates/static/**/*.js 검색 범위도 확인했다.

공식 표시 순서:

1. 기존 candidate_latest_verification이 후보자의 최신 검수 기록을 선택한다.
2. candidate_detail_content.html이 summary를 Django의 기본 HTML 이스케이프 상태로 출력한다.
3. common/base.html이 공용 표시 스크립트를 로드한다.
4. DOMContentLoaded 또는 htmx:load가 지정된 검수 영역만 렌더링한다.
5. 공용 renderer가 text node·strong·em·code·목록 요소를 생성한다. HTML은 해석하지 않는다.

검색 모달의 기존 addBubble도 같은 공용 renderer를 호출한다. 사용자 입력은 기존 textContent 출력을 유지한다. 이미 렌더링한 영역은 다시 파싱하지 않아 코드 안의 별표와 캐시된 표시 상태를 보존한다. 기존 하이픈 목록에 첨부에서 사용한 별표 목록 처리를 추가했다. 문단·제목·목록은 부모 영역의 글자색을 상속해 기존 화면 색상을 유지한다.

변경 프로그램 파일은 아래 다섯 개다.

- candidates/static/candidates/assistant-markdown.js
- candidates/templates/candidates/partials/candidate_detail_content.html
- projects/templates/projects/partials/candidate_search_modal.html
- templates/common/base.html
- tests/test_voice_frontend_shared_module.py

## 실제 검증

- 수정 전 직접 영향 19개 통과, 수정 후 동일 검사와 페이지/HTMX 초기화 회귀 검사 총 20개 통과.
- 추가 공용 헤더 검사 6개 통과.
- 공식 contracts: 승인 기준 6dd406439be5a52d5ce1f1660ebd05ca621df715의 보호 파일 18개 보존, 기존 216개 검사 통과. 검사와 기대값을 완화하지 않았다.
- Django check, Ruff, diff 검사 통과. catalog_update는 current / local.valid=true / broken_references=[].
- 기본 강조·제목/목록·중첩 강조·코드 내부 별표·이스케이프·닫히지 않은 표시·HTML 비실행의 기존 7사례를 그대로 검증했다.
- 개발 DB exdigm_debug / 역할 exdigm_debug를 확인했다. 첨부의 운영 후보자는 현재 1,000명 개발 사본에 없어 운영 DB를 수정하지 않고 임시 검수 예시를 만들었다.
- 실제 공식 runserver와 https://dev.exdigm.com/candidates/0e2c0f3d-f02c-4946-8dd6-8fee8c988c32/에서 데스크톱 1440px·모바일 390px을 확인했다.
- 변경 전 strong=0 / li=0, 변경 후 strong=7 / li=5 / ul=3. 목록의 계산된 스타일은 disc, 기존 Pretendard와 rgb(30, 41, 59) 유지, 문서 가로 넘침 없음.
- “Back to Talent Pool → 검증 후보자 카드”의 실제 클릭 흐름에서 HX-Request=true와 HTTP 200을 확인했다. 부분 갱신 뒤에도 같은 표시 결과다.
- 새 공용 스크립트와 CSS는 실제 브라우저에서 HTTP 200으로 받았다. 상세 직접 로딩의 콘솔 오류는 0개였다.
- 검증 후 DB의 임시 summary가 생성 당시 원문과 완전히 같음을 확인했다.
- 숨은 실제 Chrome을 공용 hidden-desktop-browser 라이브러리로 운영했다. 입력 데스크톱과 전경 창 유지 확인. 사용자 Chrome과 인증을 복사하거나 조작하지 않았다.

기존 별도 실패: 확대 검사의 음성 검수 4개는 ActionType 기본 항목이 없어 실패했다. 수정 전 clean 부모 판본의 별도 worktree에서도 동일한 4개가 실패했다. 후보자 목록의 사진 HTTP 404 12개도 부모 판본과 수정본에서 URL 집합이 완전히 동일했다. 이번 표시 수정의 회귀로 처리하지 않았으며 별도 문제를 고쳤다고 보고하지 않는다.

부모 판본의 화면 비교는 임시 worktree에서 같은 공식 runserver로 수행했다. 임시 위치에서는 부속 개발 게시 worker의 상대 운영 설정 경로가 달라 SECRET_KEY 키 조회 오류가 났지만, foreground 화면 서버의 상세·목록·부분 갱신은 정상 응답했다. 게시 실행은 하지 않았고 비교용 자원은 종료한다.

화면·HTTP·계산된 스타일 증거는 조정실 C:/Users/chaconne/.hidden-browser/evidence/exdigm-markdown-20260918/에 보존한다. before, parent-partial, partial 하위 폴더를 참조한다. partial/report.json과 parent-partial/report.json의 404 URL 집합을 직접 대조했다.

## 코드 리뷰 계약과 결과

주 에이전트가 code-review-loop를 직접 수행했다.

1. 원천: 이번 첨부 화면과 버그 수정 요청, 적용 AGENTS.md, 작업 전 코드 및 위 기준선.
2. 상위 역할: 저장된 검수 결과와 AI 답변의 표시만 담당한다.
3. 경계: base 4df3adb6부터 이번 다섯 파일 diff와 후보자 최신 검수 선택·상세 뷰·검색 addBubble·공용 base의 직접 연결.
4. 입력: Django가 이스케이프한 저장 summary와 기존 AI 답변 텍스트. HTML 문자열도 데이터다.
5. 절차: 공용 스크립트 선행 로드 → 첫 로딩/HTMX 초기화 → 안전한 DOM 생성. 재초기화는 기존 표시를 보존한다.
6. 출력: 강조·목록이 표시되며, 저장·AI 재실행·검색 상태 변경·외부 메시지 생성은 없다.
7. 보호 조건: 위 기준선의 원문·사용자 입력·기존 성공 구문·HTML 비실행·색상 보존.
8. 비목표: 전체 CommonMark 확장, 검수 판단 변경, 사진 경로와 음성 검수 기본 데이터, 운영 배포.
9. 근거: 실제 diff와 직접 호출부, 동일 회귀 검사, 공식 보호 검사, 첫 로딩/부분 갱신의 실제 Chrome 결과.

최종 검토의 승인 finding과 열린 계약 질문은 없다. 임시·중복 파서는 남기지 않고 공식 공용 표시 구현으로 통합했다.

## 저장 상태와 재개

Exdigm 개발 커밋: 4ac2f0b26027c58c96fda142e8c7e690eb340539. 디버깅 detached 상태를 유지한다. 운영 main과 origin/main은 작업 시작 판본을 유지한다. 애플리케이션 push·운영 배포·DB 인프라·Hermes 배포는 실행하지 않았다.

운영 승인 경계의 원천은 GBrain default:project/exdigm-deploy-workflow의 “2026-09-11 보호 기준과 별도 배포 승인”이다.

> 구현·검증 승인은 운영 배포 승인을 대신하지 않는다.

주인님이 이 수정본의 운영 배포를 지시하면 실제 Git 상태와 커밋을 다시 확인하고 공식 scripts/deploy/deploy.sh prod로 반영한다. 원래 첨부의 운영 후보자 상세에서 기존 검수 결과를 새로 표시해 확인하되, 검수 재실행이나 원문 교체는 필요하지 않다.

정리: 임시 검증 후보자·Application·검수 결과만 삭제하고, 부모 비교 worktree·이번 숨은 Chrome·소유한 개발 runserver를 종료한다. 증거 파일과 전용 프로필은 보존한다. 종료 확인은 작업 끝에 이 문서에 반영한다.


종료 확인: 검증 후보자·Application·검수 결과와 비교용 worktree를 정리했다. Candidate의 보호 관계 때문에 최초 삭제가 중단되어 트랜잭션이 취소됐고, 이번에 만든 검수 결과 → Application → 후보자 순서로 삭제해 각각 부재를 확인했다. 원래 후보자·프로젝트는 삭제하지 않았다. 전용 Chrome stopped=true, 입력 데스크톱·전경 창 유지, 개발 runserver inactive 및 운영·디버깅 Git clean을 확인했다. 실제 개발 URL은 종료 상태이며 화면 증거는 파일로 보존한다.


최종 상태 갱신: 2026-09-18 13:13:21 KST에 디버깅 HEAD가 4ac2f0b2에서 4df3adb6로 checkout된 것을 Git reflog에서 확인했다. 이번 에이전트가 실행한 정리 명령에는 해당 checkout이 없으며 실행 주체는 미확인이다. 현재 기본 디버깅 worktree와 운영 main은 clean 4df3adb6다. 검증한 수정본 4ac2f0b26027c58c96fda142e8c7e690eb340539는 서버의 refs/heads/control-room/markdown-display-20260918에 별도로 보존하고 참조 값을 확인했다. 이 참조는 HEAD·운영·origin/main을 바꾸지 않는다. 위 검증 결과는 4ac2f0b2의 실제 실행 증거이며 현재 기본 worktree에 수정이 적용돼 있다고 보고하지 않는다. 운영 승인 후에는 이 참조를 기준으로 다른 진행 작업을 보존하며 통합하고, 같은 공식 검증·배포 경로로 반영한다.
