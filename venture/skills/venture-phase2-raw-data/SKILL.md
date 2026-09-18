---
name: venture-phase2-raw-data
description: README.md의 홈페이지 URL과 src/raw 원본 자료를 읽어 src 추출 문서를 생성할 때 사용한다.
---

# 실행

## 사전 준비

- 아래 `companies/<회사>`의 `<회사>`는 `V<YYMMDD>-<한글회사명>` 형식의 회사 폴더명이다. 사용자가 한글회사명만 말하면 `companies/`에서 `V*-<한글회사명>` 폴더를 찾아 쓰고, 날짜가 다른 폴더가 둘 이상이면 임의로 고르지 말고 어느 것을 쓸지 사용자에게 확인한다.
- 입력 파일과 원본 보관 위치를 확인한다.
  - `companies/<회사>/README.md`
  - `companies/<회사>/src/raw/`
- Markdown 파일 읽기와 쓰기는 항상 UTF-8을 명시한다.
- Python으로 파일을 읽거나 쓸 때는 `encoding="utf-8"`을 명시한다.
- PowerShell에서 한글 파일을 확인할 때는 먼저 `[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)`를 실행한 뒤 `Get-Content -LiteralPath <path> -Encoding UTF8`로 읽는다.

## 입력 내용

- `companies/<회사>/README.md`
- `README.md`의 `homepage_url`
- `companies/<회사>/src/raw/`의 원본 자료 파일

## 작업 내용

- 실행 명령: `uv run python scripts/extract_sources_to_src.py <회사명>`
- 스크립트는 `scripts/documents.py`의 `extract_text()`를 사용해 HWP, HWPX, 텍스트 PDF, TXT, MD의 텍스트를 추출한다.
- 이미지 파일과 이미지 PDF는 PyMuPDF 페이지 캡처와 Codex CLI 이미지 판독으로 텍스트를 추출한다.
- 원본 자료별 추출 결과를 `src/<source_id>_<원본파일명>.md`로 저장한다.
- `homepage_url`이 있으면 공식 홈페이지 텍스트를 `src/homepage.md`로 저장한다.
- 자동 텍스트 추출에 실패한 이미지 PDF는 `src/raw/<source_id>_<원본파일명>_captures/`에 PyMuPDF 캡처 이미지를 생성한다.
- 캡처 이미지는 Codex CLI로 판독하고, 대응 Markdown 파일의 `## 추출 텍스트`에 판독 텍스트를 기록한다.
- Codex CLI 판독까지 성공한 원본은 `status: ready`로 기록한다.
- 추출하지 못한 원본은 `failed`, `missing`, `unsupported` 중 해당 상태와 실패 사유를 기록한다.
- `README.md`에 `추출 문서` 표를 만들고, 추출된 Markdown 문서 위치를 기록한다.
- 추출 실패 자료가 있어도 `README.md`의 진행 상태를 `venture-phase3-distillation`으로 바꾼다.
- 추출 실패 자료의 활용 여부와 추가 자료 요청 여부는 후속 산출물 품질을 보고 주인님이 판단한다.

## 출력 내용

- `companies/<회사>/src/homepage.md`
- `companies/<회사>/src/<source_id>_<원본파일명>.md`
- `companies/<회사>/src/raw/<source_id>_<원본파일명>_captures/`
- `README.md`의 `추출 문서` 표
- `README.md`의 `자료 위치`에 `src: src/`

## 사후 처리

- `README.md`의 `추출 문서` 표에 생성된 Markdown 문서 위치와 상태가 기록되어 있는지 확인한다.
- `homepage_url`이 있으면 `src/homepage.md`가 생성되어 있는지 확인한다.
- 생성된 추출 문서에 한글 깨짐 흔적이 없는지 확인한다.

## 완료 조건

- `companies/<회사>/src/`가 있음
- `companies/<회사>/src/raw/`에 원본 자료 파일이 있음
- `README.md`의 `추출 문서` 표에 생성된 Markdown 문서 위치가 있음
- `homepage_url`이 있으면 `src/homepage.md`가 있음
- `README.md`에 `src: src/` 위치가 기록되어 있음
- `README.md`의 `추출 문서` 표에 각 문서의 상태가 기록되어 있음
- 추출 실패 문서는 대응 Markdown 파일에 실패 상태와 사유가 기록되어 있음
- `status: visual_review_required`가 남아 있지 않음
- `README.md`의 `current_phase`가 `venture-phase3-distillation`임
- 한글 깨짐 흔적이 없음
