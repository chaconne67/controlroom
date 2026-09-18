---
name: iros-registry
description: 인터넷등기소(IROS) 부동산 조회, 결제 승인 경계, 등기 PDF 수령과 구조 검증이 필요한 작업에 사용한다.
---

# IROS 등기부 추출

## 역할

이 스킬은 IROS 도메인층이다. 조정실 Windows에서 실제 Chrome을 사용할 때 `$hidden-desktop-browser`를 함께 적용한다. 공용 스킬은 숨은 데스크톱·Chrome 프로필·캡처·종료를 맡고, 이 스킬은 주소 식별, 등기 신청 단계, 결제 승인, PDF 수령과 등기 구조 검증을 맡는다.

## 정본과 현재 경로

작업 전에 프로젝트 지침, GBrain `project/ceoloan-operating-context`, 현재 원격 저장소의 `scripts/iros_ssp.py`와 `scripts/iros_dom.py`, 관련 테스트를 확인한다. 현재 코드와 기록이 다르면 코드를 기준으로 다시 판정한다.

- 공식 코드 정본은 CEO Loan 저장소의 `scripts/iros_ssp.py`와 `scripts/iros_dom.py`다.
- `iros_ssp.py local-registry`는 현재 사용자 데스크톱의 전용 Chrome과 좌표 조작을 사용하므로 공용 숨은 실행층에 통합된 상태가 아니다. 사용자가 PC를 쓰는 동안 비간섭 실행으로 사용하지 않는다.
- `iros_dom.py`는 공용 `hidden_browser.HiddenBrowser`가 숨은 데스크톱에 띄운 실제 Chrome(설치된 Google Chrome)에 Playwright로 접속하는 경로다(2026-09-13 전환). 실행 이름은 고정 `ceoloan-iros-registry`, 프로필은 `C:\Users\chaconne\.hidden-browser\profiles\ceoloan-iros-registry`다. `--run-id`는 결과·증거 폴더 구분용이고 실행 이름에 넣지 않는다. `--headed`는 호환용 옵션이며 동작을 바꾸지 않는다.
- 호출마다 `open()`으로 Chrome을 열고, 끝나면(실패 포함) 그 호출이 연 Chrome만 `stop()`한다. 같은 이름의 실행이 이미 살아 있어 `open()`이 실패하면 그 Chrome을 건드리지 않고 오류로 끝난다. adapter에는 주소·단계·결제·PDF 가로채기·검증만 있으며 브라우저 수명주기 코드를 다시 넣지 않는다.

## 도메인 계약

IROS 작업은 현재 코드의 단계와 성공 조건을 읽어 실행한다. 일반 흐름은 로그인, 부동산 검색, 대상 1건 확정, 용도 선택, 공개 범위 선택, 결제 대상 확인, 결제, 신청 결과 열기, PDF 저장 순서다. `--until`과 `--view-only`의 정확한 범위는 현재 CLI와 `stage_sequence()`에서 확인하며 스킬에 복사한 과거 단계 목록으로 실행하지 않는다.

- 주소는 정규화한 뒤 결과 행의 주소나 부동산 고유번호로 정확히 한 건을 확정한다. 부분 문자열의 첫 행을 선택하지 않는다.
- `view-only`는 이미 결제한 신청 결과를 다시 받는 경로에만 사용한다. 새 결제를 우회하는 값으로 사용하지 않는다.
- 결제 버튼을 누르기 전 주소, 대상 수, 열람·발급 종류, 금액, 결제 수단과 사용자 승인을 다시 확인한다.
- 보안문자, OTP, 추가 인증은 사람이 처리해야 하는 중단 조건이다.
- 비밀번호·결제 비밀번호·쿠키·토큰·입력값을 화면 요약, JSON, 로그, 오류 증거에 기록하지 않는다.

## 공용 숨은 Chrome 적용

화면 조사와 UI 통합 검증은 다음 계약을 따른다.

1. `$hidden-desktop-browser`를 함께 읽고 adapter와 같은 고정 이름 `ceoloan-iros-registry`를 사용한다. adapter 실행과 수동 조사를 같은 이름으로 동시에 열지 않는다(이름 잠금으로 한쪽이 거부된다).
2. 공용 `open`으로 실제 Chrome을 열고 입력 데스크톱과 전경 창이 유지됐는지 확인한다.
3. 공용 `snapshot`으로 IROS 화면과 접근성 요소를 확인한다.
4. IROS에만 필요한 단계와 결과 판정은 이 스킬과 공식 adapter에 둔다.
5. 범용 입력·선택·다운로드 관찰 기능이 부족하면 프로젝트용 복사본을 만들지 않고 공용 스킬에 추가해 검증한다.
6. 도메인 결과와 화면 증거를 같은 `run-id`로 연결한 뒤 공용 `stop`으로 소유한 Chrome만 정리한다.

adapter는 이 계약을 직접 호출한다(2026-09-13 전환 검증: `--view-only --until save` 전후 결과 동일, 전경 창 변경 0, 잔여 Chrome 0). 실제 IROS 자동 추출의 완료 보고는 공식 명령의 summary·registry 결과로만 한다.

## 완료 조건

다음이 모두 확인돼야 IROS 등기부 추출이 완료된다.

1. 요청 주소와 선택한 부동산이 정확히 일치한다.
2. 결제가 필요했다면 승인된 조건과 실제 결제 결과가 일치한다.
3. PDF가 해당 실행의 결과 경로에 존재하고 열 수 있다.
4. 파싱 결과의 표제부·갑구·을구와 부동산 식별값이 PDF와 일치한다.
5. 최종 summary가 각 단계와 PDF·구조 검증 결과를 함께 반영한다.
6. 실패하면 마지막 성공 단계, 실패 단계, 비밀값을 제거한 증거와 재개 조건이 남는다.
