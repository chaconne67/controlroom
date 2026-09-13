# CRETOP 회사별 실패 복구 후 계속 진행 계획

## 목표

회사 수집 중 페이지 만료가 아닌 오류가 발생하면 실패 화면을 보존하고 중앙 확인 버튼을 처리한 뒤, 같은 회사의 상세 화면과 사업자번호를 확인하고 홈으로 초기화하여 다음 회사를 계속 수집한다.

## 변경 계약

1. 회사별 일반 예외 발생 즉시 현재 화면을 캡처한다.
2. 재로그인 최종 확인 버튼과 같은 중앙 좌표를 한 번의 공용 좌표로 사용한다.
3. 중앙 좌표 클릭 뒤 복사 텍스트에서 상세 레이아웃과 현재 회사 사업자번호를 확인한다.
4. 상세 상태가 확인되면 기존 홈 초기화를 실행한다.
5. 현재 회사는 성공으로 만들지 않고 오류·화면 증거·복구 결과를 기록한다.
6. 복구된 홈 상태를 다음 회사의 검색 시작 상태로 넘긴다.
7. 캡처·상세 확인·홈 초기화가 실패하면 다음 회사를 안전하게 시작할 수 없으므로 배치를 중단한다.

## SSP 병합 위치

- 현재 경로: `collect_batch_fast()` 회사 루프의 일반 예외 → 오류 기록 → 전체 배치 중단
- 병합 위치: 같은 일반 예외 분기
- 대체 경로: 일반 예외 → 캡처 → 중앙 확인 → 상세 확인 → 홈 초기화 → 오류 기록 → 다음 회사
- 유지 경로: 프리플라이트 실패, 첫·두 번째 페이지 만료 처리, 정상 회사 수집, 성공 냉각

## 수정 범위

- `scripts/cretop_agent.py`
- `scripts/test_cretop_agent.py`
- `scripts/cretop_detail_collection.py`
- `scripts/test_cretop_detail_collection.py`
- `docs/cretop/final_collection_procedure.md`
- `/home/chaconne/.codex/skills/cretop-automation/SKILL.md`
- GBrain `agents/rndlog/private/cretop-company-failure-continue-20260715`

## 검증

- 일반 실패 뒤 캡처·중앙 확인·상세 확인·홈 초기화 순서를 검증한다.
- 첫 회사 실패 뒤 두 번째 회사가 처리되는 상태 계약을 검증한다.
- 복구 실패 시 배치가 중단되는 안전 계약을 검증한다.
- 원격 결과에 포함된 실패 화면 PNG가 `remote-batch-fetch`에서 로컬 증거로 회수되는 계약을 검증한다.
- CRETOP 관련 전체 로컬 테스트, Ruff, `py_compile`, diff 검사를 통과한다.
- 코드리뷰 뒤 의도한 저장소 파일만 커밋한다.

## 원격 경계

로컬 구현에서는 원격 배포와 배치 재실행을 하지 않는다. 커밋 뒤 주인님의 별도 실행 지시가 있을 때 공식 `batch-script-only-collect` 경로로 검증한다.
