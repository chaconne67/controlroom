# Windows 컨트롤타워

- 이 Windows PC는 전체 프로젝트의 조정실이다. venture는 여러 프로젝트 중 하나이며 로컬에서 실행한다.
- 원격 프로젝트는 Windows에서 조정하고 기존 서버의 코드·Git·검증·배포 경로를 SSH로 사용한다. DB 서버는 DB·GBrain 본체와 ZiiN 운영·개발 저장소를 계속 유지한다.
- 개발 에이전트와 계획·판단·작업 지시는 조정실에서만 실행한다. 서버에는 SSH로 코드 수정·빌드·테스트·배치 명령을 실행하며 개발 에이전트를 새로 실행하거나 설치하지 않는다. 제품 기능의 기존 AI·LLM 실행은 보존한다.
- 기획·리서치·작업 계획의 파일 원본은 `C:\Users\chaconne\projects\_control-docs`의 비공개 Git에서 관리하고 각 프로젝트 `docs`로 연결한다. 코드·테스트가 읽는 자료와 코드와 함께 바뀌는 기술 계약은 서버 코드 저장소에 둔다. 공통 지침·스킬은 Windows의 기존 kmh-agent-kit가 원본이다.
- 비밀값은 실제 사용·복구에 필요한 양쪽에서 관리할 수 있다. 값의 교체 기준을 하나로 두고 필요한 실행 환경에만 공급하며 문서·Git·GBrain·로그에 값을 넣지 않는다.
- 전역 GBrain은 공용 `default` 소스를 사용한다. venture 개인 공간을 전역 기본값으로 사용하지 않는다.
- 프로젝트 지침이 별도 GBrain 카드·개인 공간을 지정하면 그 프로젝트 안에서 해당 설정을 사용한다. 개인 기록을 공용으로 복사하지 않는다.

## 공용 GBrain 실행

DB의 기존 메인 CLI를 Windows에서 SSH로 호출한다. PowerShell과 Git Bash에서 같은 명령을 사용할 수 있다.

```text
ssh chaconne@49.247.45.243 '/home/chaconne/.gbrain/bin/gbrain_with_google_env.sh get agent/gbrain-operating-protocol --source default'
```

- 작업 전 위 운영 프로토콜과 `project/windows-control-tower-operating-context`, 해당 프로젝트의 운영 맥락을 읽는다. `get`의 slug를 필요한 페이지로 바꿔 사용한다.
- 검색은 같은 CLI의 `query '<검색어>' --source-id default`, 목록은 `list --source default`를 사용한다. 명령별 문법은 같은 CLI의 `<명령> --help`로 확인한다.
- 공용 기록은 기존 본문을 읽고 보존한 뒤, 같은 CLI의 `capture --source default --slug <slug> --stdin --json`에 Markdown 본문을 표준입력으로 전달한다. Git Bash에서는 로컬 파일을 `< 파일.md`로 전달할 수 있다.
- 공용에는 프로젝트·공통 운영 지식만 기록한다. 비밀값과 개인 기록을 넣지 않으며, 다른 에이전트의 개인 소스를 전역 검색 대상으로 삼지 않는다.
- GBrain 접근 실패는 실패로 보고한다. 현재 코드·서버와 기록이 다르면 실제 상태를 확인한 뒤 갱신한다.
