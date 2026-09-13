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

## 적용·검증 결과 — 2026-09-14

- `control-room-docs`를 `chaconne67/controlroom`으로 이름 변경하고 통합 main에 반영했다. 공개 설정은 기존 private 그대로 유지했으며 공개 범위는 사용자가 별도로 결정한다. 기존 public `kmh-agent-kit`에는 이전 안내만 게시하고 보관 처리했다.
- 두 기존 main 이력은 import merge `9cd6b71`의 부모로 보존했다. 실행 변경은 `aecf805b78b99ce4dfa70dd8f8815d18f43adbf1`에서 검증했다. 이전 문서 저장소 파일 94개가 이력에 보존되며, 현재 문서·출처 파일 92개는 원본 blob과 바이트 단위로 일치한다. `.gitignore`와 `.gitattributes` 두 관리 파일만 통합 프로젝트 구조에 맞춰 조정했다.
- [통합 main의 Windows·macOS·Linux 검사](https://github.com/chaconne67/controlroom/actions/runs/34770102230)가 통과했다. 운영체제별 설치 검증, POSIX 기존 명령 검사 12개, 운영체제별 통합 동기화·실패 보존 검사 9개를 확인했다.
- 실제 Windows 설치기를 사용한 격리 환경 두 곳에서 `controlroom.cmd push/pull`로 도구·기획·검토된 코드 커밋 전달을 확인했다. 기존 `kitpush.cmd`도 같은 경로로 작동하며 미커밋 코드가 있으면 이를 보존하고 완료하지 못한 대상을 표시했다. 테스트가 바꾼 사용자 PATH는 기존 값과 형식 그대로 복원됐다.
- 현재 PC는 `C:\Users\chaconne\controlroom`으로 접근한다. 실행 중인 프로그램이 옛 키트 폴더를 점유하므로 실제 체크아웃은 기존 `kmh-agent-kit` 폴더에서 통합 main으로 갱신했고, 새 이름은 그 폴더를 가리키는 정션이다. 두 이름이 같은 파일을 가리키며 기존 문서 경로도 통합 `projects`에 연결된다. 옛 문서 체크아웃과 통합 전 Git bundle은 전환 작업의 보관 자료로 유지한다.
- 다섯 프로젝트의 docs 정션과 AGENTS.md 하드링크를 실제 원본과 대조했다. IROS, CRETOP, CRETOP scraping, hidden-desktop-browser 스킬은 통합 저장소에 포함되어 있다.
- 실제 PC의 `controlroom pull`은 통합 저장소 수신·설치를 완료했다. Venture는 기존 미커밋 작업 때문에 갱신을 보류하여 전체 명령은 종료 코드 1이다. 기존 변경·미추적 파일 452개와 HEAD·스테이징·diff가 보존됐으며, 이것을 전체 프로젝트 동기화 성공으로 표시하지 않는다. 해당 작업을 검토·커밋할 때까지 기존 상태를 유지한다.
- 최종 코드 리뷰에서 승인된 finding과 열린 계약 질문은 없다. 원격 제품 코드·서비스·인증값을 변경하거나 배포하지 않았다. 공용 GBrain 운영 맥락에 새 정본과 장기 운영 계약을 기록하고 기존 본문 보존을 재조회로 확인했다.

다른 데스크톱·노트북에서는 README의 설치 절차를 사용한다. 해당 장비의 인증·앱 로그인과 기존 미전송 작업은 장비별 확인 대상이며 이번 PC 설치가 다른 장비를 자동으로 바꾼 것은 아니다.
