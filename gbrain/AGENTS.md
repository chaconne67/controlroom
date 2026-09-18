# GBrain 조정실

- 지침·문서의 진입점은 모든 OS의 `~/controlroom/gbrain`이며 공유 Git은 `git@github.com:chaconne67/controlroom.git`이다.
- 실제 GBrain 서비스는 main `chaconne@49.247.192.127`에서 실행한다. 공식 CLI는 `/srv/consolidation/infra/gbrain-host`, 역할별 정책 CLI는 같은 폴더의 `gbrain-policy-host`다. 사용 전 `~/.gbrain-agent.md`와 `agent/gbrain-operating-protocol`을 읽는다.
- 2026-09-19 확인한 실행 코드 위치는 main `/srv/consolidation/data/gbrain-runtime/gbrain`이다. `production-gbrain-http-1` 컨테이너의 `/runtime/gbrain`으로 읽기 전용 연결된다. Git origin은 `git@github.com:garrytan/gbrain.git`, 현재 작업 브랜치는 `codex/upgrade-v0.50.0.0-kmh`다. 원본 업데이트는 설치·동기화와 별도 작업이다.
- 운영 PostgreSQL DB는 main의 `gbrain`이다. 런타임 상태는 `/srv/consolidation/data/files-standby/gbrain-state`에서 관리한다. DB 접속 비밀값은 서버의 기존 설정을 사용하고 조정실 Git으로 복사하지 않는다.
- 제품 소스의 docs·skills·에이전트 정의는 패키징·테스트 계약과 함께 서버 저장소에 유지한다. Controlroom 설치는 GBrain 런타임·DB·정책·개인 공간을 변경하지 않는다.
