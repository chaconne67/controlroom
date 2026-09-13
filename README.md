# 조정실 프로젝트 문서

개발 에이전트는 조정실에서만 실행합니다. 기획·리서치·작업 계획은 이 비공개 저장소에서 관리하며, 서버의 코드·데이터·미디어와 실행·검증 명령은 기존 SSH 경로로 사용합니다. 공통 지침·스킬은 kmh-agent-kit가 정본입니다.

## 위치와 사용

- 실제 문서 원본의 기본 위치: `~/projects/_control-docs/<project>`. `~`는 Windows의 `USERPROFILE`, macOS·Linux의 `HOME`이며 프로젝트는 해당 장비에 등록된 경로를 사용합니다.
- 각 조정실의 `docs`는 해당 원본의 `docs`를 연결합니다. 그 경로에서 문서를 편집하면 같은 파일이 바뀝니다.
- 프로그램·테스트가 읽는 파일, 코드와 함께 바뀌는 기술 계약, 제품 자체로 배포되는 스킬은 코드 저장소에 유지합니다.
- 보관 위치 변경은 오래된 계획을 다시 승인하거나 운영 코드를 배포한 것을 뜻하지 않습니다.
- 비밀값·고객 원본·DB·미디어·실행 산출물은 이 저장소에 추가하지 않습니다. 필요한 비밀값은 승인된 실행·복구 용도에 따라 양쪽에서 사용하되 교체·복구 기준을 하나로 관리합니다.

## 프로젝트

- [ceoloan](ceoloan/docs/README.md)
- [exdigm](exdigm/docs/README.md)
- [fundkeeper](fundkeeper/docs/README.md)
- [rndlog](rndlog/docs/README.md)
- [ziin](ziin/docs/README.md)
- [venture](venture/docs/README.md)
- [gbrain](gbrain/docs/README.md)
- [im-not-ai](im-not-ai/docs/README.md)
- [kmh-agent-kit](kmh-agent-kit/docs/README.md)

## 이력과 다른 조정실에서 복구

편집할 때 변경 문서와 비밀값 혼입 여부를 검토합니다. Git 원격은 비공개 `chaconne67/control-room-docs`입니다. 통합 중인 조정실 명령 `kitpush`는 검토한 기획·재개 정보를 저장하고 `kitpull`은 다른 장비에서 이를 받는 경로입니다. 직접 Git을 사용할 때는 해당 경로만 `git add -- <경로>`로 추가하고 기존 사용자 변경을 함께 올리지 않습니다.

첫 설치의 기존 공식 경로는 `curl -fsSL https://raw.githubusercontent.com/chaconne67/kmh-agent-kit/main/install.sh | bash -s -- windows-control`이며, 이미 받은 키트에서는 `./install.sh windows-control`입니다. 이 경로에서 비공개 문서 저장소 복원과 각 프로젝트 `docs` 연결까지 함께 수행하도록 통합 중입니다. 공개 키트 다운로드와 별개로 비공개 Git 인증이 필요하며 각 프로젝트 서버의 SSH 인증은 따로 준비합니다.

기존 문서 복구 방식인 인증된 Git clone과 docs 연결은 이 설치 경로에 통합합니다. 이미 있는 자료는 내용과 이력을 비교하기 전에 덮어쓰지 않습니다. 이 저장소의 이력·원격 저장은 프로젝트 코드·고객자료·비밀값의 백업을 대신하지 않습니다.

현재 구현·검증 상태는 [조정실 작업 환경 통합 계획](kmh-agent-kit/docs/seamless-workspace-plan.md)에서 확인합니다. Windows의 로컬 설치·동기화 검증은 수행했지만 공개 검증 브랜치 게시와 3 OS CI, 통과 후 main 반영은 남아 있어 통합 중입니다. 현재 공개 main의 설치 명령으로 새 통합 기능까지 전달됐다고 판단하지 않습니다.

## 현재 작업 이어받기

기존 작업 계획의 재개 정보에 목표·승인 범위, 실제 실행 서버/저장소와 branch/commit, 남은 변경, 마지막 검증 결과, 다음 행동을 남깁니다. 각 프로젝트 `docs/README.md`의 진행 중 작업에서 해당 계획을 연결하고 병렬 작업은 각각의 계획에 기록합니다.

새 장비에서는 공용 GBrain의 최신 운영 맥락을 읽은 뒤 계획의 재개 정보와 실제 코드 저장소 상태를 대조합니다. GBrain에는 장기 결정과 재사용 지식을 남기며 현재 작업 상태나 대화 원문을 중복 저장하지 않습니다.

원문 79개의 전송 해시를 검증한 뒤, 첫 커밋 전에 키 리터럴 1개 제거·코드 참조 링크 9개 연결·기존 누락 링크 1개 표시·비밀값 보관 규칙을 정리했습니다. `provenance.json`에 원본과 저장본의 SHA-256 및 변경 이유를 구분해 기록했습니다.
