---
name: testbed-base
description: Use for FundKeeper KOSCOM RA testbed work involving reports, investment-universe workbooks, TestBed2 data, Google Drive storage, or portal submissions.
---

# FundKeeper 코스콤 RA 테스트베드

코스콤 RA 테스트베드 서류를 생성·검증·보관하고 필요할 때 포털에 제출한다. 최종 서류의 정본은 Google Drive다.

## 작업 시작 계약

- Google Drive 파일을 다룰 때 `google-drive` 스킬을 함께 읽는다.
- 작업을 시작하기 전에 차수, 전략 폴더, 원본 파일, 새 산출물 이름, Drive 업로드 여부, DB 저장 여부, 포털 제출 여부를 한 계획에 적어 승인받는다.
- 승인된 계획 안의 작업은 다시 승인받지 않는다. 대상 폴더나 외부 효과가 달라지면 중단하고 새 승인을 받는다.
- 차수·전략·원본이 둘 이상이고 사용자의 선택을 근거로 확정할 수 없으면 후보와 메타데이터를 제시하고 선택을 기다린다.
- 인증값은 환경변수 `TESTBED_ID`, `TESTBED_PW`에서만 읽고 출력하지 않는다.
- 실행 전에 `uv`, `/usr/bin/google-chrome`, 업무별 Python import, Drive 연결을 확인한다. 누락된 의존성을 저장소에 추가하지 않는다.

## Google Drive 단일 성공 경로

다음 순서만 공식 경로로 사용한다.

1. Drive에서 `MOA` 폴더를 검색하고 폴더 ID를 확인한다.
2. `MOA/테스트베드{차수}/준비서류/{전략}`을 `list_folder`로 한 단계씩 확인한다.
3. 파일명, MIME 형식, 수정 시각, 부모 폴더를 비교해 원본 Office 파일을 확정한다.
4. `WORK_DIR=$(mktemp -d /tmp/testbed-work.XXXXXX)`로 작업 디렉토리를 만들고 `fetch(download_raw_file=true, include_base64=false)`로 원본을 받는다. 반환된 인증 `file_uri`를 작업 디렉토리에 materialize하고 Office 확장자를 보존한다.
5. 원본 확장자를 유지한 로컬 파일을 해당 워크플로 스크립트로 처리한다.
6. 산출물의 구조·값·서식을 검증하고 승인 계획의 파일명과 일치하는지 확인한다.
7. 전략 폴더를 다시 조회한다. 같은 이름이 이미 있으면 덮어쓰지 말고 중단한다.
8. `upload_file`로 산출물을 같은 전략 폴더에 새 파일로 올린다. `parent_folder_id`에는 확인한 전략 폴더 ID를 넣는다.
9. 업로드 결과의 파일 ID로 메타데이터를 다시 읽어 이름, MIME 형식, 크기, 부모 폴더를 확인한다.
10. 포털 제출까지 승인된 작업이면 로컬 산출물로 dry-run과 제출을 마친 뒤 작업 디렉토리를 정리한다. Drive 저장만 승인됐으면 9단계 뒤 정리한다.

Drive 업로드와 메타데이터 재확인이 끝나야 산출물 생성이 완료된 것이다. 업로드가 실패하면 로컬 파일은 복구용 임시본일 뿐 최종 산출물이 아니며, 경로를 보고하고 완료로 처리하지 않는다.

## Drive 파일 계약

- 최종 위치: `MOA/테스트베드{선택 차수}/준비서류/{선택 전략}/`.
- XLSX와 PPTX는 Google Sheets·Slides로 변환하지 않고 원래 Office MIME 형식으로 보관한다.
- 알고리즘설명서의 Linux 공식 산출물은 PDF다. 원본 PPTX는 Drive에서 변경하지 않는다.
- 최신 파일은 파일명 날짜만으로 단정하지 말고 Drive 수정 시각과 업무상 기준일을 함께 확인한다.
- 기존 파일을 갱신할 때도 새 날짜 파일을 만든다. `update_file`로 기존 바이트를 교체하지 않는다.
- 기존 파일명 패턴에서 새 이름을 확정할 수 없으면 이름을 만들지 말고 사용자에게 확인한다.
- Drive 루트, `Downloads`, Windows Drive 스트리밍 경로, 프로젝트 폴더를 최종 저장소로 사용하지 않는다.

## 업무 선택

| 요청 | 읽을 지침 | 최종 산출물 |
|---|---|---|
| 11번 알고리즘설명서 | [algo-report.md](references/algo-report.md) | PDF |
| 12번 투자유니버스·ETF 확인 | [etf.md](references/etf.md) | XLSX |
| 14번 백테스팅결과분석자료 | [backtest-report.md](references/backtest-report.md) | XLSX |
| 21번 리밸런싱 발생내역 | [rebal-report.md](references/rebal-report.md) | XLSX |

요청한 업무의 지침만 읽는다. 여러 서류를 함께 만들 때도 차수와 전략 폴더를 각각 확정하고, 모든 최종 파일을 각 원본이 있던 전략 폴더로 되돌린다.

## 펀드 코드

| 유형 | 1(350만) | 2(500만) | 3(650만) |
|---|---|---|---|
| 안정추구 | R26233 | R26234 | R26235 |
| 위험중립 | R26236 | R26237 | R26238 |
| 적극투자 | R26239 | R26240 | R26241 |

이 값은 국내 ETF 2차 포털의 고정 식별자다. 다른 차수나 전략에 재사용하지 않는다.

## TestBed2 계약

```python
tb2 = TestBed2(schedule_id=N)
tb2.모델포트폴리오(pk_list)
tb2.잔고내역불러오기(pk_list)
tb2.거래내역기반잔고추정(pk_list, target_date=...)
```

- `모델포트폴리오`는 출력만 하고 `None`을 반환하므로 결과가 필요하면 stdout을 캡처한다.
- `잔고내역불러오기`는 선행 `TestBedBalance`가 없으면 `None`을 반환한다.
- 거래 실행일은 `rday` 전후 10일의 `TradeHistory`에서 확인한 마지막 거래일이다.
- 모델포트폴리오 생성일과 거래 실행일을 같은 날짜로 가정하지 않는다.
- 잔고 저장과 리밸런싱 데이터 수집은 운영 DB를 바꿀 수 있다. 승인 계획에 DB 저장이 포함된 경우에만 실행한다.

## 제출 전 공통 검사

11번 원본 PPTX와 21번 새 XLSX가 함께 있으면 통과 기준을 검사한다.

```bash
uv run --with openpyxl --with python-pptx \
  python /absolute/path/to/testbed-base/verify_pass_criteria.py \
  "$WORK_DIR/11-source.pptx" \
  "$WORK_DIR/21-output.xlsx"
```

- 자산종류별 `|실제잔고비중 - 목표비중|` 합계는 그룹·회차별 20% 미만이어야 한다.
- 실제 위험도는 11번의 위험도 범위 안에 있어야 한다.
- 21번 목표 자산종류 비중은 11번의 허용 범위 안에 있어야 한다.
- 위반이 하나라도 있으면 Drive 업로드와 포털 제출을 중단한다.

## 포털 제출

Drive 저장을 먼저 완료한다. 포털 제출도 승인된 경우에만 다음을 실행한다.

```bash
uv run --with playwright \
  python /absolute/path/to/testbed-base/portal_upload.py \
  --url "https://www.ratestbed.kr:7443/cop/bbs/forUpdate.do?nttId=XXX&algrthSn=YYY" \
  --file "$WORK_DIR/report.pdf" \
  --title "제목_YYYYMMDD" \
  --content-append "변경 이력" \
  --dry-run
```

- dry-run의 JSON 결과로 로그인, 대상 폼, 파일을 확인한다.
- 실제 제출은 승인 계획에 포함된 URL, 파일, 제목, 이력 문구가 모두 같을 때만 `--dry-run`을 빼고 실행한다.
- 실패 원인을 확인하기 전에 수동 브라우저 제출로 우회하지 않는다.
