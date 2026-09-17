# 조정실 컨트롤타워

- 현재 장비는 전체 프로젝트의 조정실이다. Windows·macOS·Linux 데스크톱과 노트북에서 같은 역할을 사용하며, `windows-control`은 기존 설치와 연결되는 호환 등록명이다. venture는 여러 프로젝트 중 하나이며 조정실에서 실행하는 로컬 프로젝트다.
- 원격 프로젝트는 선택한 조정실 장비에서 조정한다. 2026-09-17 22:33 KST 이후 Coconut/FundKeeper·RNDLOG·CEO Loan·ZiiN 코드와 운영 DB·자료·GBrain 본체는 main `chaconne@49.247.192.127`의 `/srv/consolidation`에 있다. Exdigm 앱은 기존 전용 서버에 유지한다.
- 실제 운영 인계는 2026-09-17 22:30~22:33 KST, 전체 172.469초에 복구 절차까지 끝났다. 2026-09-18 00:35 KST 가비아 권한 DNS 3곳과 Google/Cloudflare 각각에서 공개 DNS 14개 이름 모두 main을 가리킴을 확인했다. DNS 캐시의 옛 공개 입구와 기존 GBrain CLI/SQL/자료 호환 주소는 main으로 전달한다. 현행 코드·자료·실행 책임과 검증·복구 정보는 `~/controlroom/docs/production-server-consolidation-20260916.md` 최신 절과 프로젝트 AGENTS.md를 우선한다. 옛 서버 writer는 정지·읽기 전용이며 재개하거나 그곳에 배포하지 않는다. 주인님의 가비아 DNS 수정은 완료됐다. 다음 정상 새벽/오전·주간 예약의 실제 결과와 옛 서버별 호환 주소·지속 외부 백업·저장공간 후속은 통합 문서 18절을 따른다. 옛 서버는 호환 전달·별도 복구 백업과 제외 서비스를 맡으므로 삭제/해지·vdb 포맷은 별도 지시와 잔여 의존성 정리가 필요하다.
- 개발 에이전트와 계획·판단·작업 지시는 조정실에서만 실행한다. 서버에는 SSH로 코드 수정·빌드·테스트·배치 명령을 실행하며 개발 에이전트를 새로 실행하거나 설치하지 않는다. 제품 기능의 기존 AI·LLM 실행은 보존한다.
- 기획·리서치·작업 계획의 파일 원본은 `~/controlroom/projects`의 통합 controlroom Git에서 관리하고 각 프로젝트 `docs`로 연결한다. `~`는 Windows의 `USERPROFILE`, macOS·Linux의 `HOME`이며 등록된 프로젝트 경로를 우선한다. 코드·테스트가 읽는 자료와 코드와 함께 바뀌는 기술 계약은 서버 코드 저장소에 둔다. 공통 지침·스킬과 프로젝트 기획의 원본은 현재 조정실의 controlroom 저장소다.
- 비밀값은 실제 사용·복구에 필요한 양쪽에서 관리할 수 있다. 값의 교체 기준을 하나로 두고 필요한 실행 환경에만 공급하며 문서·Git·GBrain·로그에 값을 넣지 않는다.
- 전역 GBrain은 공용 `default` 소스를 사용한다. venture 개인 공간을 전역 기본값으로 사용하지 않는다.
- 프로젝트 지침이 별도 GBrain 카드·개인 공간을 지정하면 그 프로젝트 안에서 해당 설정을 사용한다. 개인 기록을 공용으로 복사하지 않는다.

## 작업 이어받기

- `controlroom pull`로 키트·기획 문서·Venture의 커밋을 받은 뒤 프로젝트 `docs/README.md`의 진행 중 작업과 해당 계획의 재개 정보를 확인한다.
- 기존 작업 계획의 재개 정보에는 목표·승인 범위, 실행 서버/저장소와 branch/commit, 남은 변경, 마지막 실제 검증 결과와 다음 행동을 남긴다. 병렬 작업은 각 계획에서 관리하고 진행 중 계획을 프로젝트 `docs/README.md`에 연결한다.
- 재개 전에 실제 서버 Git 상태와 기록을 대조한다. 기존 사용자 변경과 실행 중인 배치는 보존하며 원격 코드의 Git·배포는 해당 프로젝트의 공식 절차를 따른다.
- 장비를 옮기거나 작업을 마칠 때 기획·재개 정보의 변경을 검토하고 `controlroom push`로 저장한다. Venture 코드는 별도 검증·커밋을 마친 것만 전송하며 미커밋 코드를 자동으로 포함하지 않는다.
- GBrain에는 장기 결정과 재사용 지식을 기록한다. 현재 작업 상태의 정본은 작업 계획이며 단순 진행 로그와 대화 원문을 중복 저장하거나 세션을 이식하지 않는다.
- 장비별 Git 인증, 프로젝트 서버 SSH 접근, 에이전트 앱 로그인은 별도로 준비한다. Windows 전용 브라우저·앱 기능은 해당 실행 환경에서 검증한 범위로 사용한다.

## 공용 GBrain 실행

기존 DB 주소의 호환 CLI가 main의 공용 GBrain으로 전달된다. CLI 주소·공용 default 계약은 유지한다. PowerShell·Git Bash·macOS/Linux 셸에서 아래 SSH 명령을 사용한다.

```text
ssh chaconne@49.247.45.243 '/home/chaconne/.gbrain/bin/gbrain_with_google_env.sh get agent/gbrain-operating-protocol --source default'
```

- 작업 전 위 운영 프로토콜과 `project/windows-control-tower-operating-context`, 해당 프로젝트의 운영 맥락을 읽는다. `get`의 slug를 필요한 페이지로 바꿔 사용한다.
- 검색은 같은 CLI의 `query '<검색어>' --source-id default`, 목록은 `list --source default`를 사용한다. 명령별 문법은 같은 CLI의 `<명령> --help`로 확인한다.
- 공용 기록은 기존 본문을 읽고 보존한 뒤, 같은 CLI의 `capture --source default --slug <slug> --stdin --json`에 Markdown 본문을 표준입력으로 전달한다. Git Bash에서는 로컬 파일을 `< 파일.md`로 전달할 수 있다.
- 공용에는 프로젝트·공통 운영 지식만 기록한다. 비밀값과 개인 기록을 넣지 않으며, 다른 에이전트의 개인 소스를 전역 검색 대상으로 삼지 않는다.
- GBrain 접근 실패는 실패로 보고한다. 현재 코드·서버와 기록이 다르면 실제 상태를 확인한 뒤 갱신한다.
