# Troubleshooting

## 동기화 명령의 현재 계약

`controlroom pull`과 `kitpull`은 최신본 확보·검사 → 교체 대상 압축 백업·검사 → 적용·검증 순서입니다. 로컬 변경·미전송 커밋·다른 브랜치가 남아 있어도 백업 후 최신 main으로 갱신합니다. 공유할 변경은 먼저 검토하고 `controlroom push "변경 설명"`으로 저장합니다.

```bash
git -C ~/projects status --short --branch
controlroom verify
```

다운로드나 백업 확인에 실패하면 기존 설치가 유지됩니다. 적용 중 파일 잠금·권한 문제 등이 발생하면 이전 상태를 자동 복구하고 백업 경로를 표시합니다. 원인을 해결한 뒤 같은 설치기 또는 pull을 다시 실행합니다. 복구가 불완전하다고 표시되면 해당 ZIP과 실패 파일을 보존하고 그 원인을 먼저 확인합니다.

## push 충돌 또는 다른 브랜치

push는 main에서 검토한 변경을 전송합니다. 원격과 같은 부분을 바꾼 경우 rebase를 취소해 로컬 커밋을 유지합니다. 강제 전송하지 않고 양쪽 내용을 확인해 정리합니다.

```bash
git -C ~/projects fetch origin
git -C ~/projects diff origin/main...main
```

## Windows 명령이 보이지 않는 경우

기존 장비에서는 아래 설치기를 실행하고 터미널을 새로 엽니다. 처음 설치하는 장비에서는 README의 다운로드한 `install.ps1`을 실행합니다.

```powershell
& "$env:USERPROFILE\projects\.controlroom\install.ps1" -Agent windows-control
Get-Command controlroom, kitpull, kitpush
```

설치기는 기존 사용자 PATH 값을 유지하며 필요한 `.local\bin` 항목만 추가합니다. PowerShell·CMD·Git Bash 명령은 같은 Python 업데이트 경로를 사용합니다.

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
