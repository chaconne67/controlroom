# controlroom 저장소 통합

사용자 승인: 두 저장소를 controlroom으로 합친다. 공개·비공개 설정은 사용자가 나중에 결정하므로 변경하지 않는다.

기존 private control-room-docs를 controlroom으로 이름 변경하고 public kmh-agent-kit의 코드·이력을 가져온다. 원래 공개 키트는 이전 안내를 남긴 보관 저장소로 전환한다. 비공개 자료를 기존 공개 저장소에 올리지 않는다.

- 기준선: kit 50030c2, docs 5915f9d, 두 작업 폴더 clean. 이전 대화의 미커밋 스킬은 다른 작업에서 이미 커밋됐다.
- 보존: 두 Git 이력, 문서 94개 원문, 사용자 등록 경로·Venture 작업·로그인·키·서버 데이터·기존 스킬 실행.
- 구조: 키트 코드는 루트, 공통 설명은 docs, 문서 저장소의 파일은 projects 아래에 이식한다. 프로젝트의 기존 지침/스킬과 docs가 같은 저장소에 있게 한다. 문서 루트 README·provenance·원문 보관 규칙도 함께 보존한다.
- 명령: controlroom pull/push를 공식 이름으로 추가하고 kitpull/kitpush는 호환 진입점으로 유지한다. Git 로컬 설정 키는 기존 등록을 보존해 재사용한다.
- 실행 경로: 셸 명령 → 통합 저장소 main 수신/저장 → 기존 OS 설치기 → 프로젝트 docs 연결/검증 → Venture 기존 커밋 동기화. 별도 기획 저장소 clone·commit·push 단계는 제거한다.
- 최소 구현: 기존 install.sh/install.ps1, shell/kit-aliases.sh와 Git 병합 기능을 재사용한다. 새 동기화 서비스·데몬·DB를 만들지 않는다.
- 검증: 변경 전 관련 검사를 기록하고, 변경 후 Windows/macOS/Linux 설치·Git 왕복, 문서 원문/이력 보존, 새 명령과 호환 명령, 실제 PC의 프로젝트 연결과 작업 보존을 확인한다. code-review-loop로 같은 변경 범위를 검토한다.
- 전환: 임시 체크아웃에서 구현·검증 후 GitHub 이름을 바꾸고 게시한다. 로컬 기존 체크아웃은 복구 가능한 위치로 보존하고 공식 controlroom 경로와 기존 경로 호환 연결을 설치한다.
- 완료: GitHub controlroom main, 두 이력 포함, 통합 문서/도구 수신, 실제 설치/동기화 검증, 이전 저장소 보관 안내를 확인한다. 공개 범위는 원래 private 대상 설정 그대로 둔다.
