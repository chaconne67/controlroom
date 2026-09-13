# 조정실 작업 환경 통합 계획

## 사용자 목적과 완료 기준

2026-09-13 사용자 결정: kmh-agent-kit를 중심으로 조정실·서버·개발환경·프로젝트 관리가 하나의 흐름으로 작동하고 유지·개선하기 쉬워야 한다. 데스크톱·노트북의 Windows·macOS·Linux에서 같은 짧은 명령으로 관리한다. 기기 이동 시 지침·도구·프로젝트·현재 작업 상태가 이어지면 충분하며 대화 원문 동기화는 요구하지 않는다.

새 기기에서 기존 인증을 준비하고 공식 설치 명령을 실행하면 키트, 조정실 프로젝트, 비공개 기획 원본과 연결이 준비되어야 한다. 일상 명령은 kitpull과 kitpush를 유지한다. A에서 변경을 저장하면 B가 같은 공식 명령으로 받아 작업 계획의 재개 정보와 실제 코드 저장소 상태를 대조하고 이어서 작업할 수 있어야 한다.

## 작업 시작 기준선

- 기준 키트 HEAD: e909d582816547e702816b5bfff5e087fe93e490. 기존 사용자 CEO Loan 수정 4개, staged iros-registry 링크 1개, untracked iros-registry 폴더는 보존한다.
- 기존 install.sh/install.ps1, shell/kit-aliases.sh와 windows-control-projects.tsv를 재사용한다. 설치 코드는 3 OS를 처리하지만 연결되는 카드·지침은 Windows 계정의 절대 경로를 사용한다.
- 문서 저장소 control-room-docs의 기준 HEAD는 68ca191이고 clean이다. 문서 79개·전체 93개 복구와 5개 docs 연결을 이미 검증했지만 설치/kitpull/kitpush는 이 저장소를 관리하지 않는다.
- Venture는 main의 별도 로컬 코드 저장소이며 기존 dirty 상태가 있다. 나머지 5개 프로젝트의 코드와 실행 위치는 기존 원격 서버다.
- GBrain의 단순 진행 로그 저장 금지와 구형 reference 분류 5개 보존 방침을 유지한다.

## 통합할 흐름

1. **최초 준비:** 기존 공식 `./install.sh windows-control`과 한 줄 설치 `curl -fsSL https://raw.githubusercontent.com/chaconne67/kmh-agent-kit/main/install.sh | bash -s -- windows-control`을 유지한다. 이 경로에 기획 저장소 복원과 docs 연결을 통합한다. 등록명은 조정실 역할이고 OS는 실행 장비가 결정한다. Git·SSH·셸 및 각 에이전트 앱의 로그인은 장비별 전제이며 비밀값을 저장소로 복제하지 않는다.
2. **프로젝트 복원:** 기존 manifest를 정본으로 사용한다. 비공개 문서 저장소를 docs 종류로 등록하고 기존 profile 및 git 종류와 구분한다. 디렉터리명과 GBrain 역할명 검증을 분리한다. 등록된 사용자 프로젝트 경로를 재설치로 기본 경로에 덮어쓰지 않는다.
3. **설치 연결:** Git 저장소 복원·검증은 공용 셸 경로를 사용한다. Windows는 기존 junction/hardlink, POSIX는 기존 symlink 구현으로 프로필과 docs를 연결한다. 기존의 다른 실제 docs 폴더를 자동 이동·삭제하지 않는다.
4. **kitpull:** 키트와 manifest에 선언된 조정실 Git 저장소를 대상으로 원격 변경을 받는다. 로컬 변경·미전송 커밋·충돌·다른 브랜치는 보존하고 해당 저장소와 필요한 조치를 알린다. 전체 완료를 확인한 뒤 프로젝트 연결을 재검증한다.
5. **kitpush:** 기존 키트의 허용 범위 규칙을 유지한다. docs 저장소는 검토한 기획·재개 정보 변경을 Git으로 저장하고 동기화한다. Venture 같은 코드 저장소는 이미 만든 커밋만 전송하며 코드·고객자료·미추적 작업을 자동으로 stage하지 않는다. 필요한 코드 커밋이 남으면 명시하고 완료로 표시하지 않는다. 원격 서버 코드의 Git·배포는 해당 프로젝트의 기존 절차로 수행한다.
6. **재개:** 기존 작업 계획에 목적·실행 서버/저장소·branch/commit·남은 변경·검증 결과·다음 작업을 짧게 기록하고 프로젝트 docs/README에서 현재 작업으로 연결한다. 병렬 작업은 각 계획에서 관리한다. 중간 진행 로그를 GBrain에 복제하거나 대화 세션을 이식하지 않는다.

## 구현 경계와 최소 구조

- 공개 키트에는 설치·동기화 코드, 공개 가능한 지침, 프로젝트 연결 계약과 운영 설명을 둔다. 비공개 문서 본문은 control-room-docs에 둔다.
- 단순히 저장소마다 새 동기화 도구를 만들지 않고 기존 shell/kit-aliases.sh의 Git 판단과 기존 두 설치기의 OS 연결 동작을 재사용한다.
- Git 동기화에서 origin이 manifest의 저장소인지 확인하고 강제 push/reset, 사용자 작업의 자동 stash/삭제를 사용하지 않는다. 실패한 단계와 완료한 저장소를 구분한다.
- Windows 고정 사용자 경로는 현재 사용자 홈과 프로젝트 상대 경로로 바꾼다. 서버의 확정된 SSH 경로는 그대로 유지한다.
- 공용 최신 GBrain 문서는 OS 무관 조정실 역할과 현재 흐름을 기록한다. 기존 reference 페이지의 분류나 스키마는 바꾸지 않는다.
- Windows 전용 Chrome/카카오톡 등 기기 고유 기능은 모든 OS에서 동일하게 작동한다고 선언하지 않는다. 본 통합은 공용 작업 환경과 진입 경로를 제공하며 실제 기능 지원·로그인은 장비별 확인 대상이다.

## 보호할 상태

기존 코드·고객자료·미디어·비밀값·인증·프로그램 설정·앱 세션·스킬·Git index 및 미커밋 작업을 보존한다. 서버에 개발 에이전트를 실행하지 않는다. 제품 AI·LLM과 기존 서비스·배포·예약 작업은 유지한다. 기존 custom 프로젝트 등록과 다른 사람이 변경 중인 파일은 덮어쓰지 않는다.

## 검증

- 변경 전 기존 관련 검사를 실행하고 결과·기존 실패를 구분한다. Windows 설치 검사는 임시 HOME만으로 실제 사용자 PATH가 오염되지 않도록 검사 부작용과 복구 범위를 먼저 확인한다.
- 기존 installer/kitpull/kitpush 진입점으로 두 조정실과 bare Git 원격의 실제 왕복 동기화를 검증한다. 키트·기획·재개 정보·Venture 커밋과 프로필/docs 연결을 포함한다.
- dirty 문서, dirty Venture, 다른 origin, detached/다른 branch, 원격 충돌, 인증 실패, 기존 비관리 docs 폴더, custom 프로젝트 경로, 반복 설치의 보존을 확인한다.
- Windows PowerShell/CMD/Git Bash와 Linux의 실제 실행을 구분해 확인한다. macOS의 실제 호스트/CI 검증을 할 수 없으면 POSIX 호환 검사와 실기 검증의 한계를 따로 기록한다.
- 최종 code-review-loop는 주 에이전트가 수행한다. 필요한 결함을 수정하고 같은 경계에서 재검증한다.

## 최종 검증·게시 결과 — 2026-09-13

- 사용자가 두 GitHub 저장소의 push와 3 OS CI 통과 후 키트 main 반영을 승인했다. 검증 브랜치 `e4ab16d8a2305240fcbe0d21759bfc18d042ef79`와 비공개 문서 `ce93329f823caa9261c61bf6e73f49924f4a7680`를 게시하고 원격 일치를 확인했다. 앞서 공개 push와 Linux 서버 SCP가 자동 승인 심사에서 거절된 기록은 과거 경과다. SCP로 우회하지 않았으며 승인 후 GitHub의 공식 CI를 사용했다.
- 최종 판본 `db275cb1ad48871c55e7337b8d1703d7babe7f86`의 [3 OS CI](https://github.com/chaconne67/kmh-agent-kit/actions/runs/34754868442)가 모두 성공했다. Windows·Linux·macOS에서 실제 설치기 진입점과 두 조정실 간 동기화·실패 시 작업 보존을 검증했다. 기존 POSIX 명령 검사는 Linux·macOS에서 실행했으며 Windows에서는 해당 단계만 예정대로 제외했다. 공개 main 게시 후 같은 SHA의 [자동 재실행](https://github.com/chaconne67/kmh-agent-kit/actions/runs/34755052958)도 3 OS 모두 성공했다.
- CI에서 확인한 Windows 경로의 8.3 표기 차이는 `Get-Item.FullName`으로 경로를 비교하도록 수정했다. macOS Bash의 변수 뒤 한글 경계 문제는 두 곳의 `$file`을 `${file}`로 명시해 수정했다. 검사의 바이트 진단과 기대 정본 경로는 유지했다.
- 최종 검증한 판본을 공개 키트 main에 게시하고 실제 원격 SHA가 `db275cb1ad48871c55e7337b8d1703d7babe7f86`과 일치함을 확인했다. 최종 code-review-loop를 마쳤으며 남은 finding은 없다.
- 현재 Windows PC의 키트 main은 `c73ca499621f145188bb8e99ffe730a5259d9f84`다. 별도 브라우저 작업 `4d9fec762d9bcce3114fc785e50aec1f256e3ec9`의 3파일을 보존하며 게시 판본을 병합한 결과다. 이번 통합의 15파일은 게시 판본과 같고 사용자 staging·모든 변경 파일 바이트와 동시에 진행된 CRETOP 변경도 보존했다. 현재 PC 전체와 공개 main이 같은 판본이라고 간주하지 않는다.
- Windows 중간 검증 이력은 workspace 9/9 통과(168.838초), 기존 KitSync 8/8 통과(41.810초), 스킬 검사 50개 통과다. 검증 브랜치 e4ab16d8를 만들 당시에는 기존 main e909d582와 사용자 index를 유지했다. 당시 CMD 재실행은 81.64초였으며 아래 최종 왕복 검증으로 갱신했다.
- 최종 실제 `kitpush.cmd`·`kitpull.cmd` 왕복은 74.536초에 통과했다. 성공한 push/pull에서 실제 설치기 완료는 각각 3회/2회였고, 두 Windows 시험 조정실의 키트·문서·Venture 커밋, docs 연결 10개와 문서 바이트가 일치했다. dirty 코드 사례에서는 명령이 완료로 처리되지 않았고 코드 index·작업트리·HEAD를 보존하면서 독립된 문서 변경은 저장했다. 시험 원격은 로컬 bare Git이며 SSH는 성공 대체물을 사용했다.
- 최종 현재 PC 설치 재실행은 exit 0, 전체 검증 통과다. 프로젝트 프로필 5개의 AGENTS 원본·docs 원본 연결, 공용 GBrain 카드와 CMD 래퍼 2개가 정확했고 키트·문서·Venture의 Git·변경 파일 상태가 전후 동일했다. 실제 DB의 GBrain SSH 조회도 통과했다.
- 리뷰에서 동기화 후 원본 연결 검증 누락과 별도 pushurl 전송 대상 검사 누락을 재현해 수정했다. 최신 Windows 검사 9개, 공식 CMD 왕복, 3 OS CI와 최종 리뷰에서 같은 범위를 다시 확인했다.
- 공용 GBrain 운영 계약은 capture 후 다시 읽어 저장 내용과 기존 본문 보존을 확인했다. 저장본 SHA-256은 `79359cda14ea9a23921df58e3c4cfd152bc312752d3f5b8af6a4f13faa8216dd`다. 실행별 진행 로그는 추가하지 않는다.

## 작업 목록

- [x] 현재 코드와 프로젝트/GBrain 연결 감사
- [x] 사용자의 기기 간 이어받기 범위 확인
- [x] 기준선·보호할 사용자 변경과 파일 상태 잠금
- [x] manifest·복원·docs 연결 통합
- [x] kitpull·kitpush의 조정실 저장소 동기화 통합
- [x] OS 무관 지침과 작업 계획 재개 정보 연결
- [x] Windows 설치·공식 CMD 왕복·dirty 작업 보존 확인
- [x] 리뷰 지적 2개 재현·수정과 최신 Windows 검사 재검증
- [x] 기존 사용자 index와 분리한 로컬 검증 브랜치 커밋
- [x] 공용 GBrain 운영 계약 저장 및 기존 본문 보존 검증
- [x] 사용자 승인 후 공개 검증 브랜치와 비공개 문서 게시·원격 확인
- [x] Windows·Linux·macOS CI 실행과 필요한 수정·재검증
- [x] 최종 code-review-loop 종료
- [x] 검증한 키트 main 게시·원격 확인과 별도 로컬 작업 보존
- [x] 게시 판본 반영 후 현재 Windows 조정실 설치·연결·작업 보존 검증

## 재개 정보

확인일: 2026-09-13. 통합 구현, 3 OS CI, 최종 리뷰, 공개 main 게시와 현재 Windows 조정실 적용을 완료했다. 아래 Git 상태는 확인 시점의 기록이며 후속 작업 시작 시 실제 상태를 다시 대조한다.

- 목표·승인 범위: OS가 다른 조정실 사이에서 기존 설치·kitpull·kitpush로 키트, 기획 문서, 프로젝트 진입점과 현재 작업을 이어받는다. 대화 원문·프로그램 설정·인증값 복제와 원격 제품 배포는 포함하지 않는다.
- 코드 위치·ref: 현재 조정실의 `~/kmh-agent-kit`. 공개 main은 `db275cb1ad48871c55e7337b8d1703d7babe7f86`, 현재 PC main은 별도 브라우저 작업을 보존한 `c73ca499621f145188bb8e99ffe730a5259d9f84`다. 이번 통합의 15파일만 게시 판본과 일치함을 검증했다. 실제 브랜치·작업트리·index를 확인하고 다른 사용자 작업은 자동 포함하거나 되돌리지 않는다.
- 문서 위치·상태: 비공개 `chaconne67/control-room-docs`의 기본 위치는 `~/projects/_control-docs`다. 초기 구조 정리 68ca191의 원문 79개·전체 93개와 이후 통합 계획을 보존한다. 앞선 문서 판본 ce93329는 원격 일치를 확인했다. 이 최종 기록의 최신 판본·전송 여부는 문서 저장소의 HEAD·origin/main과 실제 원격 main ref를 대조해 확인하며 자체 커밋 SHA를 미리 기록하지 않는다.
- 마지막 실제 검증: 위 결과 절의 3 OS CI와 main CI 재실행, 최종 CMD 왕복 74.536초, 현재 PC 설치·연결·작업 보존과 실제 DB GBrain SSH 조회, 최종 리뷰 종료를 기준으로 한다. CI 성공은 각 OS의 모든 제품 앱·로그인이나 사용자 소유 Mac/Linux 장비까지 검증했다는 뜻은 아니다.
- 근거 위치: 작업을 수행한 Codex 작업 폴더의 `work/seamless-kit-audit/`. `publication-verification.json`, `main-ci-verification.json`, `installed-cmd-sync-verification.json`, `live-install-verification.json`, `guidance-verification.json`, `gbrain-capture-verification.json`과 사용자 상태 보존 증거를 참조한다. 문서 전송 결과는 `private-publication-verification.json`에 남긴다. 로컬 증거 파일 자체의 새 장비 동기화는 보장하지 않으므로 확인 결과는 이 계획에도 기록했다.
- 보호 상태: CEO Loan 기존 사용자 파일·staged IROS 링크·신규 IROS 스킬, Venture 미커밋 코드, 별도 브라우저 3파일 커밋과 동시 CRETOP 작업을 보존했다. 설치 전후 키트·문서·Venture Git 상태가 동일했다. 새 작업자는 최신 Git 상태를 대조하고 사용자 변경을 자동 stage·삭제·초기화하지 않는다.
- 다음 작업 진입점: 새 장비에서는 해당 장비의 Git·SSH·앱 인증을 준비하고 공식 `windows-control` 설치 경로를 실행한다. 기존 장비는 `kitpull` 결과와 실제 Git 상태를 확인한 뒤 프로젝트 docs/README의 진행 중 계획을 연다. 계획의 재개 정보와 원격 코드 상태를 대조한 뒤 해당 작업을 계속한다.
- 남은 범위: 이번 통합의 구현·검증·게시를 막는 승인 대기는 해소됐다. 개별 장비 인증, OS 전용 기능과 제품 기능·배포는 각 프로젝트의 기존 검증·승인 계약을 따른다. 별도 사용자 미커밋 작업과 로컬 브라우저 커밋의 후속 처리는 이번 통합과 구분해 보존한다.
