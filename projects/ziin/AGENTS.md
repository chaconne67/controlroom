# ZiiN 프로젝트

## 조정실

- 작업 위치는 이 프로필을 연결한 현재 프로젝트 폴더이며 기본값은 `~/projects/ziin`입니다. `~`는 Windows의 `USERPROFILE`, macOS·Linux의 `HOME`입니다. 이미 등록된 사용자 지정 경로를 우선합니다.
- 개발 에이전트는 선택한 조정실 장비에서만 실행합니다. 아래 서버의 코드·Git·검증·배포 경로는 SSH로 사용하며 제품 기능의 기존 AI·LLM 실행은 보존합니다.
- 새 세션은 `~/.gbrain-agent.md`를 읽고, 공용 최신 `project/windows-control-tower-operating-context`와 `project/ziin-operating-context`를 확인합니다.
- 아래 Linux 경로와 명령은 명시된 원격 호스트의 셸에서 실행합니다. 조정실 OS에 맞춰 서버 경로를 바꾸거나 운영 코드를 조정실에 복제하지 않습니다.
- 기획·리서치·작업 계획은 `docs/README.md`에서 찾습니다. `docs`는 비공개 문서 저장소의 `ziin/docs`에 연결되며 기본 정본은 `~/projects/_control-docs/ziin/docs`입니다.
- 작업을 이어받을 때는 `docs/README.md`의 진행 중 작업 링크와 해당 계획의 재개 정보를 읽고 실제 서버 Git 상태와 대조합니다. 작업을 마치거나 옮기기 전에 그 계획에 재개 정보를 갱신하며 병렬 작업은 각 계획에서 관리합니다.

## 역할

- 이 폴더는 ZiiN의 조정실입니다. 실제 코드·실행 및 검증 자료·코드 Git·배포는 DB 서버 `chaconne@49.247.45.243:/home/chaconne/projects/ziin`에 유지합니다.
- ZiiN은 Exdigm에서 운영 중인 헤드헌팅 업무 시스템을 다른 헤드헌팅 회사에도 제공할 수 있도록 범용화한 제품입니다.
- 제품 사실의 최종 기준은 검증된 Exdigm 운영 코드입니다. ZiiN 문서와 코드가 다르면 실제 코드를 확인한 뒤 문서와 GBrain을 갱신합니다.
- 조정실 에이전트가 SSH로 DB의 `/home/chaconne/projects/ziin`에서 개발·검증합니다. `docs/implementation/`과 `docs/product/`의 기획 원본은 조정실 문서 경로이며, 나머지 코드·디자인·운영 문서 경로는 원격 저장소 기준입니다. 배포는 별도 명시적 요청이 있을 때 기존 `scripts/deploy.sh`로 실행합니다.

## 정본

| 구분 | 정본 |
|---|---|
| 작업·배포 루트 | `/home/chaconne/projects/ziin` |
| GitHub | `git@github.com:chaconne67/ziin.git` |
| 목표 브랜치 | `main` |
| 운영 도메인 | `https://www.ziin.site` |
| 구축·배포 지시 | `docs/implementation/지니-챗봇-작업지시.md` |
| 디자인 시스템 | `docs/design/design.md` |
| 제품 사실 | `docs/product/지인-시스템-소개.md`와 검증된 Exdigm 코드 |
| 랜딩 문구 | `docs/product/랜딩-문구.md`, `docs/product/카피액기스.md` |
| 확정 랜딩 원본 | `docs/design/final/시안-D.html` |
| 확정 대화창 원본 | `docs/design/final/지니-대화창UI.html` |
| 배포 진입점 | `scripts/deploy.sh` |
| 운영 구조 | `docs/operations/deployment.md` |

- 공개 제품명은 `ZiiN`, AI 이름은 `지니`입니다.
- 과거 문서의 `Ziin`, `G-in`, `지인`은 검색용 별칭으로만 취급합니다.

## 작업 전 GBrain

- 먼저 전역 GBrain 카드 `~/.gbrain-agent.md`를 읽고 그 규칙을 따릅니다.
- 아래 문서를 작업과 직접 관련된 범위에서 조회합니다.
  - `project/ziin-operating-context`
  - `project/ziin-landing-page`
  - `feedback/ziin-copy-and-design-rules`
  - `project/ziin-design-assets`
  - `project/ziin-chatbot-deploy`
- 제품 기능을 다룰 때는 관련 Exdigm 문서와 실제 운영 코드까지 확인합니다.
- 권위 순서는 검증된 실제 코드·운영 상태, 최신 사용자 결정과 작업 지시, 프로젝트 문서, GBrain입니다.

## 공식 작업 경로

1. SSH로 DB의 실제 저장소 Git 상태와 기존 사용자 변경, 보호할 원본을 확인합니다.
2. GBrain과 해당 작업 지시를 읽습니다.
3. 변경 범위·보호 불변조건·검증 기준을 잠그고 일괄 승인을 받습니다.
4. 핵심 외부 연동은 구현 전에 실제 환경에서 짧게 검증합니다.
5. 승인된 단일 실행 경로를 구현하고 같은 경로로 테스트합니다.
6. 실행 동작·데이터·권한·외부 효과·배포 경로를 바꾸면 `code-review-loop`를 수행합니다.
7. 검증된 코드만 커밋합니다.
8. 배포한 커밋과 운영 결과를 직접 확인합니다.

- 직접 확인하지 못한 상태를 성공으로 보고하지 않습니다.
- 운영 배포는 RNDLOG·Exdigm·CEO Loan에서 검증된 공통 원칙인 단일 진입점, clean `main`, 이미지 커밋 대조, 마이그레이션 분리, 상태 검사를 따릅니다.

## 랜딩과 지식 경계

- UI를 만들거나 고치기 전에 `docs/design/design.md`를 읽고, 변경 뒤 같은 기준으로 다시 검증합니다.
- `docs/design/final/시안-D.html`과 `docs/design/final/지니-대화창UI.html`은 확정 원본이므로 수정하지 않습니다.
- 서비스용 `index.html`은 확정 랜딩 원본의 정확한 복사본에 로컬 위젯 스크립트 한 줄만 추가합니다.
- 공개 지식에는 검증된 제품 기능·도입·가격 원칙·확정 카피만 넣습니다.
- 경쟁사명, 내부 코드·서버·인증 정보, 내부 범용화 메모는 공개 지식에서 제외합니다.
- 문서나 코드에 없는 제품 사실을 만들지 않습니다.

## 운영 안전 경계

- 같은 호스트의 Exdigm, MySQL, Portainer, rndlog와 공유 네트워크는 보호 대상입니다.
- ZiiN 컨테이너와 `ziin` 데이터베이스·롤만 만들거나 변경합니다.
- Exdigm 데이터베이스의 데이터·설정·비밀번호는 읽지 않습니다.
- 새 호스트 포트는 80·443만 사용합니다.
- 기존 컨테이너 재시작, 전체 compose 종료, 이미지·볼륨·네트워크 정리를 하지 않습니다.
- `.env`의 비밀값은 출력·로그·Git·GBrain에 남기지 않습니다.
- 공개 방문자 입력은 도구가 없는 선택된 LLM 공급자 API로만 보냅니다. 개발용 에이전트 실행기와 그 지침·자격 증명을 공개 런타임에 연결하지 않습니다.
- LLM 공급자 장애 때 다른 공급자로 자동 우회하지 않습니다.
- 기본 공급자는 Gemini이며 기본 모델은 `gemini-3.7-flash`입니다. OpenAI는 환경변수로 명시했을 때만 선택합니다.

## Git

- 현재 조정실의 `AGENTS.md`는 로컬 KMH Agent Kit의 지침에 연결합니다. 원격 저장소의 기존 지침 링크·Git 제외 상태는 이번 이전에서 변경하지 않습니다.
- `.env`, 인증서, 런타임 상태 파일을 커밋하거나 이미지에 넣지 않습니다.
- 강제 푸시, 기존 이력 삭제, 사용자 변경 되돌리기를 하지 않습니다.

## GBrain 기록

- 검증된 사실, 반복할 결정, 사용자 피드백, 재현·원인이 확정된 디버깅 결과만 기록합니다.
- 원문 로그, 대화 전문, 비밀값, 개인정보, 검증되지 않은 추측은 기록하지 않습니다.
- 디버깅 문서는 재현 조건과 근본 원인이 확정된 뒤에만 만듭니다.
