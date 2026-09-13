# Troubleshooting

## kitpush Says There Is No Upstream Branch

현상:

```text
ERROR: 현재 브랜치의 원격 추적 브랜치가 없습니다.
```

이전 동기화 함수가 현재 checkout 상태와 upstream에 의존해 발생한 오류입니다. 현재 버전은 `main ↔ origin/main`을 공식 경로로 사용하고 upstream을 자동 복구합니다.

먼저 현재 브랜치와 작업 파일을 확인합니다.

```bash
git -C ~/controlroom status --short --branch
```

`main`이 아니거나 `HEAD detached`라면 로컬 변경을 보존한 상태에서 `main`으로 돌아간 뒤 설치기를 한 번 실행합니다.

```bash
git -C ~/controlroom switch main
~/controlroom/install.sh <등록 이름>
source ~/.bashrc
kitpush
```

## kitpull Stops Because Local Work Exists

`kitpull`은 로컬 변경이나 아직 push하지 않은 커밋을 덮지 않습니다. 현재 변경을 공유하려면 `kitpush`를 먼저 실행합니다.

```bash
git -C ~/controlroom status --short --branch
kitpush "변경 설명"
```

변경을 버릴지는 자동으로 결정하지 않습니다. 불필요한 변경이라면 내용을 확인한 뒤 사용자가 직접 정리합니다.

## kitpush Reports A Rebase Conflict

원격과 로컬에서 같은 부분을 바꾸면 `kitpush`가 재배치를 취소하고 로컬 커밋을 보존합니다. 원격 상태를 확인해 충돌을 수동으로 정리한 뒤 `kitpush`를 다시 실행합니다.

```bash
git -C ~/controlroom fetch origin
git -C ~/controlroom diff origin/main...main
```

## Windows Commands Are Missing

PowerShell에서 등록 이름으로 설치기를 다시 실행한 뒤 터미널을 새로 엽니다.

```powershell
git clone https://github.com/chaconne67/controlroom.git "$env:USERPROFILE\controlroom"
& "$env:USERPROFILE\controlroom\install.ps1" -Agent '<등록-이름>'
Get-Command kitpull, kitpush
```

설치기는 사용자 PATH에 `.local\bin`을 추가하고, PowerShell·CMD용 명령과 Git Bash의 셸 설정을 함께 구성합니다.

## Bun Install Fails Because unzip Is Missing

현상:

```text
error: unzip is required to install bun
```

해결:

```bash
sudo apt-get update
sudo apt-get install -y unzip
curl -fsSL https://bun.sh/install | bash
```

## GBrain Uses The Wrong Database

현상: Exdigm `.env`의 `DATABASE_URL`이 GBrain subprocess에 섞여 들어갑니다.

해결: 직접 `gbrain`을 실행하지 말고 래퍼를 사용합니다.

```bash
~/.gbrain/bin/gbrain_with_google_env.sh doctor --fast
```

래퍼는 `DATABASE_URL`과 `OPENAI_API_KEY`를 제거하고, GBrain 실행 전에 안전한 작업 디렉토리로 이동합니다. Exdigm 프로젝트 디렉토리에서 실행하면 Bun/GBrain이 현재 디렉토리의 `.env`를 다시 읽어 Exdigm DB URL이 섞일 수 있기 때문입니다.

## Embedding Is Disabled

현상:

```text
embed=0%
embedding_disabled: true
stale chunks
```

원인: 검색용 임베딩 설정이 꺼져 있거나 provider/dimensions/schema가 맞지 않습니다. Distillation 모델 설정과는 별개입니다.

확인:

```bash
~/.gbrain/bin/gbrain_with_google_env.sh config show
~/.gbrain/bin/gbrain_with_google_env.sh embed --stale --dry-run
~/.gbrain/bin/gbrain_with_google_env.sh doctor --fast
```

## Daily Report Keeps Asking

`memory_distill.py check-pending`은 `~/.gbrain/reports/index.json`의 `last_prompted_date`를 보고 같은 날짜에는 한 번만 묻습니다.

리뷰 후 상태 표시:

```bash
python3 ~/.gbrain/bin/memory_distill.py mark YYYY-MM-DD --status reviewed --decision "accepted"
```
