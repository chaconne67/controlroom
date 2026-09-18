# Venture 로컬 프로젝트

- Venture 코드·지침·스킬·문서는 모든 OS의 `~/controlroom/venture`에 설치한다. Git 정본은 `git@github.com:chaconne67/controlroom.git`의 `venture/`이며 `kitpull`·`kitpush`로 함께 동기화한다. 별도 Venture Git을 만들지 않는다.
- 포털 자동화의 기존 성공 환경은 Windows다. 다른 OS의 설치 성공은 해당 OS의 브라우저·포털 업무 검증을 뜻하지 않는다. 실행 전 이 프로젝트 README의 의존성과 해당 업무 스킬을 확인한다.
- 회사별 자료·인증은 로컬 `companies/` 또는 사용자가 지정한 Google Drive 연결을 사용한다. 정확한 장비별 경로는 아래 개인 GBrain 카드와 기록에서 확인하고 Git에는 넣지 않는다.
- main의 기존 `/home/chaconne/projects/venture`는 보존 대상이다. Controlroom 동기화가 그 운영 코드·Git을 가져오거나 갱신하지 않는다.
- GBrain 사용 전 전역 `~/.gbrain-agent.md`를 읽고, 이 프로젝트의 개인 공간 규칙은 `~/controlroom/.controlroom/gbrain-cards/venture.md`를 읽어 적용한다.
- 이 프로젝트의 GBrain 명령은 Git Bash의 `gbrain-venture`다. 기본 공간은 `venture`이며, 개인 기록을 컨트롤타워 공용 공간으로 옮기지 않는다.
- 작업 전 `gbrain-venture get agents/venture/private/project-venture-writing-guide`와 `gbrain-venture get agents/venture/private/project-venture-companies-path`를 읽는다.

## 한글 파일 처리

- 한글 의미가 중요한 Markdown·JSON·스킬 파일은 UTF-8로 읽고 쓴다.
- PowerShell에서 한글이 깨져 보이면 내용을 해석하지 말고 UTF-8 출력을 지정해 다시 확인한다.

## 검증된 포털 자동화 보호

- 성공 기록이 있는 브라우저·세션·로그인·팝업 처리·메뉴 진입 경로는 변경 전 기준선으로 잠근다.
- 기존 경로를 바꿔야 하면 성공 기록과 충돌하는 지점, 변경 범위, 같은 공식 명령으로 검증할 방법을 먼저 밝힌다.
- 조사 중 수동 조작이나 임시 우회가 성공해도 완료로 판정하지 않는다. 수정한 공식 스크립트 경로로 기존 성공 사례와 변경 조건을 다시 검증한다.
