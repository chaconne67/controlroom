# Venture Automation

회사 자료를 정리하고 벤처기업확인 신청서 작성부터 SMES 포털 입력·임시저장까지 수행하는 업무용 프로젝트입니다.

## 업무 실행

Venture 프로젝트에서 `venture` 스킬로 시작합니다. 현재 진행 위치는 회사별 `README.md`에서 관리하며, 각 단계의 작업과 완료 조건은 `skills/venture-phase*/SKILL.md`를 따릅니다.

- 전체 진행: [venture 스킬](skills/venture/SKILL.md)
- 신청서 작성 규칙: [작문 규칙](skills/venture/references/writing-rules.md)
- 포털 입력·임시저장: [phase10 스킬](skills/venture-phase10-portal-save/SKILL.md), `scripts/web.js`

## 회사 작업공간

회사별 작업공간은 `companies/V<YYMMDD>-<한글회사명>`입니다. 같은 회사의 여러 신청 회차가 있으면 사용할 폴더를 확인합니다.

- `README.md`: 회사 기본 정보와 진행 상태
- `src/raw`, `src/md`, `distillation.md`: 원본 자료, 추출 텍스트, 정제 정보
- `values.md`, `texts`: 포털 입력값과 신청서 본문
- `.env`: 회사별 `SMES_ID`, `SMES_PW`, 선택 `SMES_URL`

고객 자료와 자격증명은 로컬에서 보존합니다. 회사 작업공간과 실행 상태는 `.gitignore`로 제외합니다. 옛 Venture 저장소의 고객 자료와 Git 이력은 원래 저장소와 전환 전 로컬 백업에 보존하며 새 Controlroom Git에는 이식하지 않습니다. 자격증명을 문서나 Git에 기록하지 않습니다.

## 설치와 동기화

Venture는 `git@github.com:chaconne67/controlroom.git`의 `venture/`에 통합되어 있습니다. 설치기는 `~/controlroom/venture`에 코드·지침·문서를 설치하고 `skills`를 `.claude/skills`와 `.agents/skills`에 실제 파일로 복사합니다. 별도 Venture clone이나 `.git`은 사용하지 않습니다.

처음 실행하는 장비에서는 Venture 폴더에서 의존성을 설치합니다.

```powershell
uv sync
npm ci
```

Venture 코드를 바꾼 뒤에는 검증하고 `kitpush "변경 내용"`으로 공유 변경과 함께 커밋·전송합니다. 다른 장비에서는 `kitpull`로 받습니다. pull은 수정 중인 관리 코드도 백업 후 최신 버전으로 교체합니다. 고객 자료·인증·브라우저 상태는 동기화하지 않으므로 장비별로 준비합니다.

## 검증

```powershell
uv run python -X utf8 -m pytest -q
node --check scripts/web.js
```

포털 입력 검증은 해당 회사의 준비된 자료와 phase10 표준 명령으로 수행합니다. 문서 테스트 통과만으로 실제 포털 입력이나 임시저장이 완료됐다고 판정하지 않습니다.
