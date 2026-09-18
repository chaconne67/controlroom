# SMES 벤처포털 공통 도구 모음

이 폴더는 루트의 `tmp_*` 임시 스크립트에서 반복적으로 검증된 패턴만 추려 만든 재사용 도구입니다.

## 전제

1. 포털 로그인/브라우저 세션은 기존 `scripts/web.js`로 열어둡니다.

```powershell
node scripts\web.js --company "회사명" --step login-inspect --debug-port 9331
```

2. 이후 도구는 열린 Chrome CDP 세션에 붙습니다.

공통 옵션:

- `--cdp http://127.0.0.1:9331` 기본값
- `--vnia 신청번호`
- `--company companies/<회사명>`의 회사명

## 1. 현재 포털 화면 검사

```powershell
node scripts\portal-tools\smes_inspect.js --vnia 1184749 --page pds --out .venture-sessions\portal-runs\에브모우\inspect_pds.json
```

`--page` 값:

- `doc`
- `company`
- `representative`
- `finance`
- `summary`
- `pds`
- `growth`
- `attachments`

출력:

- URL/title/body preview
- visible textarea 목록과 입력 길이
- 첨부파일 readonly input의 파일명/fileGrpSn/fileSno
- 전체 control dump

## 2. 장문 사업계획서만 재입력

회사 workspace의 `texts/*.md`를 읽어 포털 장문 textarea만 덮어씁니다. frontmatter와 Markdown 제목은 제거하고, 포털 1,000자 제한 항목은 990자로 보수 절단합니다.

```powershell
node scripts\portal-tools\smes_reinput_long_texts.js --company "에브모우" --vnia 1184749
```

특정 페이지만:

```powershell
node scripts\portal-tools\smes_reinput_long_texts.js --company "에브모우" --vnia 1184749 --pages summary,pds,growth
```

읽는 파일:

- `texts/business_plan_summary.md`
- `texts/problem_background.md`
- `texts/solution.md`
- `texts/tech_progress.md`
- `texts/tech_plan.md`
- `texts/entrepreneurship.md`
- `texts/target_market.md`
- `texts/competition.md`
- `texts/market_progress.md`
- `texts/market_plan.md`
- `texts/funding_plan.md`

주의:

- 이 도구는 장문 textarea만 다룹니다.
- 체크박스, 재무, 대표자, 첨부파일은 건드리지 않습니다.
- 저장 후 재조회해서 보이는 textarea 길이를 검증합니다.

## 3. RAONK 첨부파일 업로드

포털 첨부파일 페이지가 native `input[type=file]`을 노출하지 않고 RAONKUpload만 사용할 때 씁니다.

### 매핑 JSON 방식 권장

예: `attachment-map.json`

```json
[
  { "code": "APLY03", "file": "C:/path/to/business.pdf", "filename": "사업자등록증.pdf" },
  { "code": "APLY06", "file": "C:/path/to/vat.pdf", "filename": "부가가치세과세표준증명원.pdf" },
  { "code": "APLY08", "file": "C:/path/to/finance.pdf", "filename": "재무제표.pdf" }
]
```

실행:

```powershell
node scripts\portal-tools\smes_raonk_upload.js --vnia 1184749 --mapping attachment-map.json --out .venture-sessions\portal-runs\회사명\attachment_verify.json
```

### 단일 합본 PDF를 필수 5개 항목에 반복 업로드

```powershell
node scripts\portal-tools\smes_raonk_upload.js --vnia 1184749 --file "C:/path/to/합본.pdf"
```

주의:

- 업로드 후 약 70초 기다렸다가 reload 검증합니다.
- 성공 시 readonly input에 파일명, `data-filegrpsn`, `data-filesno`가 생깁니다.

## 4. 공통 라이브러리

`smes_common.js`에는 아래 기능이 있습니다.

- CDP 연결
- 신청 단계 URL 생성
- 포털 세션 확인
- 임시저장/저장 후 이동
- visible textarea 요약
- Markdown 정리
- generic selector value set

새 도구를 만들 때는 `tmp_*`를 루트에 만들기보다 이 공통 모듈을 import해서 `scripts/portal-tools/` 안에 추가하세요.

## 운영 원칙

- 최종제출은 이 도구들에서 지원하지 않습니다.
- 사용자 승인 없는 비밀번호/본인인증/결제/최종제출 조작 금지.
- 회사별 후보/미확인 값은 `values.md` status를 기준으로 보수적으로 처리합니다.
- 실행 결과 JSON은 `.venture-sessions/portal-runs/<회사>/` 아래에 보관합니다.
