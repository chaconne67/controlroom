<!-- controlroom:main-server:begin -->
## Main 서버 실행 맥락

이 폴더 `{project}`는 실제 코드 Git 저장소입니다. 이 저장소의 코드·Git·검증 명령은 현재 서버 셸에서 실행합니다. 기존 프로젝트 지침과 코드·배포 계약을 유지합니다.

{references}

공통 지침을 참고할 때 기획 문서의 상대 경로는 그 지침에 명시된 공유 원본을 기준으로 읽습니다. 이 폴더의 `docs`는 제품 저장소가 관리합니다. 현재 서버에 있는 이 코드의 작업에는 현재 서버 셸을 사용하고, 다른 서버 대상 작업에는 그 서버의 SSH 절차를 따릅니다. 프로젝트 스킬은 `.agents/skills`와 `.claude/skills`에 배치됩니다. `controlroom pull`은 이 저장소의 에이전트 지침과 배치 스킬만 갱신합니다.
<!-- controlroom:main-server:end -->
