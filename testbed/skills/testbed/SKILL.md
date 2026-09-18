---
name: testbed
description: FundKeeper 코스콤 RA 테스트베드 작업을 요청했지만 세부 작업 스킬이 정해지지 않았을 때 사용합니다.
---

# Testbed

요청을 아래 키트 스킬 중 하나로 연결합니다. 선택한 스킬의 `SKILL.md`를 읽고 그 절차를 따릅니다.

| 요청 | 사용할 스킬 |
| --- | --- |
| 공통 맥락 또는 백테스트 보고서 | `testbed-base` |
| 알고리즘 설명서 | `testbed-algo-report` |
| ETF 투자 유니버스 | `testbed-etf` |
| 리밸런싱 발생 내역 | `testbed-rebal-report` |

요청이 여러 작업을 포함하면 `testbed-base`의 공통 맥락을 먼저 읽고, 사용자가 요청한 결과 순서대로 해당 스킬을 적용합니다. 요청만으로 어느 결과가 필요한지 구분할 수 없을 때만 짧게 확인합니다.
