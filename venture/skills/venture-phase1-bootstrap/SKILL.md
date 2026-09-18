---
name: venture-phase1-bootstrap
description: 벤처인증 회사 작업공간과 README.md 초기 파일을 생성할 때 사용한다.
---

# 실행

## 사전 준비

- 필수 입력값을 확인한다.
  - 회사명
  - SMES 포털 아이디
  - SMES 포털 비밀번호
  - 회사 홈페이지 주소
  - 기초 원본 자료 파일 또는 폴더 경로
- 선택 입력값을 확인한다.
  - 회사별 사업계획서 작성 방향성
- Markdown 파일 읽기와 쓰기는 항상 UTF-8을 명시한다.
- Python으로 파일을 읽거나 쓸 때는 `encoding="utf-8"`을 명시한다.
- PowerShell에서 한글 파일을 확인할 때는 먼저 `[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)`를 실행한 뒤 `Get-Content -LiteralPath <path> -Encoding UTF8`로 읽는다.
- 회사 작업공간 폴더명은 `companies/V<YYMMDD>-<한글회사명>` 형식이다.
- `<YYMMDD>`는 작업공간을 만드는 날짜다. 사용자가 날짜를 지정하지 않으면 오늘 날짜가 쓰인다.
- 같은 한글회사명 폴더가 하나이고 날짜를 지정하지 않으면 스크립트가 그 폴더를 재사용한다. 날짜가 다른 폴더가 둘 이상이면 기존 작업은 phase1을 실행하지 말고 사용할 폴더를 확인해 다음 phase에서 이어간다. 새 작업공간을 만들 때만 새 날짜를 `--date`로 지정한다.
- 사용자가 회사명과 함께 초기화, 재시작, 새로 시작을 명시하면 `--force`로 실행한다.
- 초기화 지시가 없고 `companies/<회사>/README.md`가 이미 있으면 덮어쓰지 않는다.

## 입력 내용

- 회사명
- SMES 포털 아이디
- SMES 포털 비밀번호
- 회사 홈페이지 주소
- 기초 원본 자료 파일 또는 폴더 경로
- 회사별 사업계획서 작성 방향성

## 작업 내용

- `skills/venture/scripts/bootstrap_company.py <한글회사명>`를 실행한다. 스크립트가 `companies/V<YYMMDD>-<한글회사명>` 폴더를 만든다.
- 사용자가 작업공간 날짜를 지정하면 `--date <YYMMDD>`로 전달한다. 지정이 없으면 전달하지 않는다.
- SMES 포털 아이디는 `--smes-id <아이디>`로 전달한다.
- SMES 포털 비밀번호는 `--smes-pw <비밀번호>`로 전달한다.
- 회사 홈페이지 주소는 `--homepage <홈페이지>`로 전달한다.
- 기초 원본 자료 파일 또는 폴더 경로는 `--source <자료경로>`로 전달한다.
- 자료가 여러 개이면 `--source`를 여러 번 사용한다.
- 회사별 사업계획서 작성 방향성이 있으면 `--writing-direction <작성방향성>`으로 전달한다.
- 원본 자료는 `companies/<회사>/src/raw/`에 복사한다.
- 원본 자료의 외부 경로는 `README.md`에 기록하지 않는다.
- 홈페이지 주소와 회사별 작성 방향성은 `README.md`에 기록한다.
- 포털 아이디와 비밀번호는 스크립트가 `companies/<회사>/.env`에 기록한다. git에 올라가지 않도록 `README.md`를 비롯한 다른 산출물에 옮겨 적지 않는다.
- 다음 단계가 `venture-phase2-raw-data`임을 `README.md`에 기록한다.

## 출력 내용

- `companies/<회사>/README.md`
- `companies/<회사>/.env`
- `companies/<회사>/src/raw/`

## 사후 처리

- `README.md` 생성 뒤 반복 물음표(`??`) 또는 대체문자(`�`)가 남아 있는지 확인한다.
- 한글 깨짐이 발견되면 원 입력값을 UTF-8 기준으로 다시 확인한다.

## 완료 조건

- 회사 폴더명이 `V<YYMMDD>-<한글회사명>` 형식임
- `companies/<회사>/README.md`가 있음
- `README.md`의 `work_dir`가 실제 회사 폴더 경로와 같음
- `companies/<회사>/src/raw/`에 원본 자료가 복사되어 있음
- `README.md`에 기본 정보와 진행 상태가 있고, 포털 자격증명은 들어 있지 않음
- `.env`에 `SMES_ID`와 `SMES_PW`가 있음
- `README.md`의 `current_phase`가 `venture-phase2-raw-data`임
- 한글 깨짐 흔적이 없음
