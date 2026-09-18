# 조정실 컨트롤타워

- 현재 장비는 전체 프로젝트의 조정실이다. Windows·macOS·Linux 데스크톱과 노트북에서 같은 역할을 사용하며, `windows-control`은 기존 설치와 연결되는 호환 등록명이다. venture는 여러 프로젝트 중 하나이며 조정실에서 실행하는 로컬 프로젝트다.
- 원격 프로젝트는 선택한 조정실 장비에서 조정한다. 2026-09-17 22:33 KST 이후 Coconut/FundKeeper·RNDLOG·CEO Loan·ZiiN 코드는 main `chaconne@49.247.192.127`의 `/home/chaconne/projects/<프로젝트>`에 있으며, 운영 DB·자료·GBrain 본체와 공통 Compose/복구 설정은 `/srv/consolidation`에 있다. Exdigm 앱은 기존 전용 서버에 유지한다.
- 실제 운영 인계는 2026-09-17 22:30~22:33 KST, 전체 172.469초에 복구 절차까지 끝났다. 2026-09-18 00:35 KST 가비아 권한 DNS 3곳과 Google/Cloudflare 각각에서 공개 DNS 14개 이름 모두 main을 가리킴을 확인했다. 2026-09-18 옛 공개 입구·GBrain CLI·SQL·자료·인증서 전달을 중지했고 현행 연결은 main을 직접 사용한다. 현행 코드·자료·실행 책임과 검증·복구 정보는 현재 조정실 루트의 `.controlroom/docs/production-server-consolidation-20260916.md` 최신 절과 프로젝트 AGENTS.md를 우선한다. 옛 서버 writer는 정지·읽기 전용이며 재개하거나 그곳에 배포하지 않는다. 주인님의 가비아 DNS 수정은 완료됐다. 실제 저장공간·일일 전체 DB 복원 결과는 통합 문서20절, 정상 예약·인증서 전달의 당시 결과는21절, 기억8개 저장·Coconut 캐시 마감과백업3일 보관은22절, 옛 서버 잔여 정리·Hermes 세 사용자·Codex 구독 인증·조정실 독립 복구 보관은23절을 따른다. 옛 서버는 정지 보관 상태이며 삭제/해지는 별도 지시로 처리한다. 추가 vdb 저장 배치는 2026-09-18 후속 지시에 따라 통합 문서20절에서 적용했다.
- 사용자가 대화하는 조정실은 로컬 데스크탑이다. main(`49.247.192.127`)에는 PC가 꺼져 있을 때도 승인된 자동 수정 작업을 수행하는 서버 조정실을 둔다. 두 조정실은 같은 controlroom Git의 지침·스킬·계획과 공용 GBrain을 사용한다. PC·노트북·메인서버 모두 같은 설치 경로로 `~/controlroom`에 공통 원본과 모든 프로젝트 조정실을 둔다. Exdigm처럼 main에 코드가 없는 프로젝트도 지침·문서·스킬을 설치한다. 운영 저장소의 코드·Git·문서·지침·스킬은 해당 제품의 작업 절차로 관리하며, Controlroom 설치·동기화 대상에서 제외한다.
- Exdigm은 main의 Codex에서도 SSH로 전용 서버의 debug worktree를 수정·검증하고 기존 공식 경로로 배포한다. main의 다른 제품도 프로젝트별 개발·검증·배포 경계를 유지한다. 서버 조정실 설치는 운영 데이터 변경·배포·예약 실행의 포괄 승인이 아니다. Exdigm 등 다른 제품 서버에는 개발 에이전트를 추가 설치하지 않으며 제품 기능의 기존 AI·LLM 실행은 보존한다.
- 기획·리서치·작업 계획의 공유 원본은 Controlroom Git의 `<프로젝트>/docs`다. 모든 OS의 PC·노트북·main 서버 원본 루트는 `~/controlroom`이며 공통 도구는 그 안의 `.controlroom`이다. main의 기존 제품 `docs`는 제품 저장소 소유이며 공유 기획 원본으로 교체하지 않는다. `~`는 Windows의 `USERPROFILE`, macOS·Linux의 `HOME`이다. 코드·테스트가 읽는 자료와 코드와 함께 바뀌는 기술 계약은 서버 코드 저장소에 둔다.
- 비밀값은 실제 사용·복구에 필요한 양쪽에서 관리할 수 있다. 값의 교체 기준을 하나로 두고 필요한 실행 환경에만 공급하며 문서·Git·GBrain·로그에 값을 넣지 않는다.
- 전역 GBrain은 공용 `default` 소스를 사용한다. venture 개인 공간을 전역 기본값으로 사용하지 않는다.
- 프로젝트 지침이 별도 GBrain 카드·개인 공간을 지정하면 그 프로젝트 안에서 해당 설정을 사용한다. 개인 기록을 공용으로 복사하지 않는다.

## 프로젝트 진입 구조

- 조정실: 모든 OS에서 `~/controlroom/<프로젝트>`를 사용한다. Windows의 `~`는 `%USERPROFILE%`이다. 에이전트 작업은 조정실 프로젝트에서 지침·스킬·재개 문서를 읽고 시작한다. 실제 코드 위치와 접속·검증·배포 방법은 해당 프로젝트 지침을 따른다.
- main: `/home/chaconne/projects/fundkeeper`, `rndlog`, `ceoloan`, `ziin`. 각 폴더가 실제 코드·`.git`을 가진 독립 저장소이며 여기에서 SSH로 수정·검증·커밋·기존 GitHub 원격 푸시를 수행한다. FundKeeper의 기존 `master`와 CEO Loan의 기존 원격 이름 `ceoloan`을 유지한다.
- PC·노트북의 접속은 `ssh chaconne@49.247.192.127` 후 `/home/chaconne/projects/<프로젝트>`로 이동한다. 이미 main의 해당 코드 폴더에서 실행 중이면 현재 서버 셸을 사용한다. 프로젝트 AGENTS.md의 실제 저장소·원격·브랜치·검증·Compose 정의를 따른다.
- RNDLOG 프로젝트 루트는 실제 코드 저장소다. 회사별 제출·연구자료는 main `/srv/consolidation/data/files-standby/workspace/{companies,resources}`에 있고 자료 접속 코드는 프로젝트 `deploy/workspace_storage_gateway.py`다. 프로젝트 루트를 자료에 연결하는 symlink는 사용하지 않는다.
- Exdigm은 전용 서버의 기존 실제 저장소·개발 서버를 유지하며 main 통합 프로젝트로 옮기지 않는다. Venture는 `~/controlroom/venture`에서 코드·지침·스킬·문서를 함께 관리한다. Controlroom 한 Git에 통합하며 중첩 Git과 별도 Venture 원격 동기화를 사용하지 않는다. main의 기존 `~/projects/venture` 코드·Git은 보존한다.
- 현행 구조·접속·복구 안내는 통합 문서 19절을 우선하며 앞 절의 당시 경로는 이력이다. 조정실의 공통 지침·프로젝트 기획 원본과 실제 설치 구조는 controlroom 저장소에서 관리한다.

## 작업 이어받기

- `kitpull` 후 Controlroom 원본의 프로젝트 `docs/README.md`에서 진행 중 작업과 재개 정보를 확인한다. 모든 설치에서 Venture를 포함한 Controlroom 한 저장소를 동기화한다. main 서버의 기존 `~/projects` 제품 Git은 동기화하지 않는다.
- 기존 작업 계획의 재개 정보에는 목표·승인 범위, 실행 서버/저장소와 branch/commit, 남은 변경, 마지막 실제 검증 결과와 다음 행동을 남긴다. 병렬 작업은 각 계획에서 관리하고 진행 중 계획을 프로젝트 `docs/README.md`에 연결한다.
- 재개 전에 실제 서버 Git 상태와 기록을 대조한다. 기존 사용자 변경과 실행 중인 배치는 보존하며 원격 코드의 Git·배포는 해당 프로젝트의 공식 절차를 따른다.
- 장비를 옮기거나 작업을 마칠 때 기획·재개 정보의 변경을 검토하고 `kitpush`로 저장한다. Venture 코드 변경도 같은 커밋에 포함되므로 전송 전에 변경과 테스트를 확인한다. 고객 자료·비밀값·브라우저 상태는 공유 대상에서 제외한다.
- GBrain에는 장기 결정과 재사용 지식을 기록한다. 현재 작업 상태의 정본은 작업 계획이며 단순 진행 로그와 대화 원문을 중복 저장하거나 세션을 이식하지 않는다.
- 장비별 Git 인증, 프로젝트 서버 SSH 접근, 에이전트 앱 로그인은 별도로 준비한다. Windows 전용 브라우저·앱 기능은 해당 실행 환경에서 검증한 범위로 사용한다.

## 공용 GBrain 실행

공용 default 계약을 유지하며 main의 공용 GBrain에 직접 접속한다. 이전 호환 주소 대신 아래 현행 명령을 사용한다. PC·노트북의 PowerShell·Git Bash·macOS/Linux 셸에서는 SSH로 실행한다. 이미 main에서 실행 중이면 SSH 접속 없이 `/srv/consolidation/infra/gbrain-host`부터 같은 명령을 실행한다.

```text
ssh chaconne@49.247.192.127 '/srv/consolidation/infra/gbrain-host get agent/gbrain-operating-protocol --source default'
```

- 작업 전 위 운영 프로토콜과 `project/windows-control-tower-operating-context`, 해당 프로젝트의 운영 맥락을 읽는다. `get`의 slug를 필요한 페이지로 바꿔 사용한다.
- 검색은 같은 CLI의 `query '<검색어>' --source-id default`, 목록은 `list --source default`를 사용한다. 명령별 문법은 같은 CLI의 `<명령> --help`로 확인한다.
- 공용 기록은 기존 본문을 읽고 보존한 뒤, 같은 CLI의 `capture --source default --slug <slug> --stdin --json`에 Markdown 본문을 표준입력으로 전달한다. Git Bash에서는 로컬 파일을 `< 파일.md`로 전달할 수 있다.
- 공용에는 프로젝트·공통 운영 지식만 기록한다. 비밀값과 개인 기록을 넣지 않으며, 다른 에이전트의 개인 소스를 전역 검색 대상으로 삼지 않는다.
- GBrain 접근 실패는 실패로 보고한다. 현재 코드·서버와 기록이 다르면 실제 상태를 확인한 뒤 갱신한다.

## 보관 디스크·일일 DB 백업

- Main 코드/Git은 각 `~/projects/<프로젝트>`, 운영 DB·앱 런타임·현재 캐시/업로드·다운로드는 기존 정본 경로다. 실시간 사용이 아닌 이미지·파일 원본·자료는 `/mnt/data/files`, 복구 시험/보관 이미지 사본은 `/mnt/data/archive`, 초기 Git bundles는 `/mnt/data/imports`에 둔다.
- DB 백업은 기존 단일03:40 Asia/Seoul timer로 `/mnt/data/backups/daily/YYYY-MM-DD`에 하루 한 완료 묶음만 생성한다. 전체 PG 접속 가능 비템플릿 DB와 MySQL 저장 스키마를 포함하고 같은 날 재호출은 기존 SHA 확인 뒤 중단한다. 2026-09-18 후속 지시에 따라 최근3일분 완료 백업만 보관한다. 현재 일일 백업은9월18일 한 묶음이다. 고정 UUID/mount 확인이 실패하면 시스템 디스크에 대신 쓰지 않는다.
- `/srv/consolidation/{work,backups,incoming}` 및 미사용 초기 `/srv/consolidation/data/rndlog-workspace`는 기존 복구 접속용 bind mount다. 실제 보관은 추가 디스크의 같은 파일이며 프로젝트 코드 루트에 자료 symlink를 만들지 않는다.
- RNDLOG 회사별 자료는 제출 원본·수신기록·리서치·보고서 작업본/완료 산출물·공통 resources다. 현재 자료 정본은 기존 files-standby/workspace이며 DB를 뜻하지 않는다. 저장 기준과 실제 검증·복구 증거는 통합 문서20절과 main infra README를 따른다.
