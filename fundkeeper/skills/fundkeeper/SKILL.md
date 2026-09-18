---
name: fundkeeper
description: Use when developing, diagnosing, or operating the FundKeeper/Coconut portfolio, account, rebalancing, trading, reporting, or in-product Codex features.
---

# FundKeeper

FundKeeper는 모멘텀에셋의 자산배분·리밸런싱 서비스이고, 사용자 서비스명은 Coconut이다. 운영 도메인은 `coconut.ai.kr`이다.

## 작업 라우팅

- 수동계좌 잔고 반영: `fundkeeper-client-balance`를 함께 사용한다.
- UI·UX·템플릿·Tailwind 작업: `fundkeeper-design-system`을 함께 사용한다.
- 배포·운영 상태·복구 작업: `fundkeeper-deploy`를 함께 사용한다.
- 코스콤 RA 테스트베드 작업: `testbed-base`를 함께 사용한다.

## 실행 환경

| 항목 | 값 |
|---|---|
| SSH | `chaconne@49.247.38.186` |
| 저장소 | `/home/chaconne/fundkeeper` |
| 호환 경로 | `/home/work/fundkeeper` |
| GitHub | `reneesoft/fundkeeper` |
| 기준 브랜치 | `master` |
| Python | `.venv/bin/python` (프로젝트 요구사항 3.12 이상) |
| 운영 | Docker Swarm `Coconut`, Nginx, Gunicorn |
| 도메인 | `https://coconut.ai.kr` |
| DB | MySQL `fundkeeper`(Django ORM), `price`(시장 가격) |

중앙에는 코드 복제본을 만들지 않는다. 검색·수정·검증·Git 작업은 SSH를 통해 이 저장소에서 수행한다.

## 핵심 도메인

- `Fkuser`: 사용자와 인증의 중심이다.
- `MyPortfolios`: 사용자가 선택한 전략 포트폴리오다.
- `MyPortfolioManager`: Mix 포트폴리오와 하위 전략·비중을 연결한다.
- `Backtest`와 관련 모델: 전략의 종목 구성과 성과·비중 결과를 보관한다.
- `MyAccount`: KIS API와 연결되는 증권계좌다. 인증정보·현금흐름·거래·가치 이력·자동매매 실행과 연결된다.
- `ClientAccount`: 외부 자료로 관리하는 수동계좌다. `ClientCash`, `ClientTicker`와 함께 전체 잔고를 이룬다.
- `RebalancingSchedule`: 리밸런싱 기준일과 거래일을 정한다. `OrderAccounts`, `OrderList`, 테스트베드 잔고와 연결된다.
- `Asset`: 티커·ISIN·시장·자산군·위험도·연금 구분의 종목 정본이다.

AWT, BAA, Mix는 각각 별도 전략 앱이지만 공통 시뮬레이션과 포트폴리오 모델을 사용한다. Mix 변경은 하위 전략 비중과 리밸런싱 날짜 전파를 함께 확인한다.

## 코드 탐색 기준

- 설치 앱의 정본은 `fundkeeper/settings/base.py`의 `INSTALLED_APPS`다. 현재 `client_manager`를 포함한다.
- Django 설정은 `fundkeeper/settings/local.py`와 `deploy.py`로 나뉜다. 둘 다 실제 운영 DB나 외부 서비스 설정을 읽을 수 있으므로 실행 명령의 부작용을 먼저 확인한다.
- 예약 작업은 `xmodules/sh/`를 직접 호출할 수 있다. 파일 하나를 고칠 때도 cron·실행 사용자·작업 디렉터리를 먼저 찾는다.
- 증권 주문, 결제, 계좌 동기화, 테스트베드 잔고 저장은 데이터나 외부 시스템을 바꾸므로 명시 승인 없이 실행하지 않는다.
- 파일 목록·줄 수·모델 필드는 이 문서의 오래된 목록보다 현재 코드를 기준으로 찾는다.

## 앱 내 Codex 실행 계약

`support/views.py`의 상담원과 `xmodules/system/description_convertor.py`의 자산명 변환기가 Codex CLI를 호출한다.

- 컨테이너는 호스트 `/home/chaconne/.codex`를 `/root/.codex:ro`로 마운트한다.
- 각 호출은 임시 `CODEX_HOME`을 만들고 `auth.json`, `config.toml`, `installation_id`가 있으면 복사한다.
- 호출은 `/home/work/fundkeeper`에서 read-only sandbox, ephemeral 모드로 실행된다.
- 모델은 `CODEX_MODEL`로 정하며 현재 이미지 기본값은 `gpt-5.5`다.
- 상담원 역할·RAG·사용자 데이터 규칙은 애플리케이션 프롬프트가 정본이다.

따라서 원격 호스트의 Codex 설정을 순정 상태로 유지한다. 프로젝트 지침·스킬·GBrain을 원격에 설치하면 제품 런타임 프롬프트와 컨텍스트가 오염될 수 있다.

## 구현과 검증

1. `git status --short --branch`로 기존 변경을 확인한다.
2. 현재 호출 경로와 모델·설정·템플릿을 읽는다.
3. 요청 범위만 수정한다.
4. `.venv/bin/python manage.py check --settings=fundkeeper.settings.deploy`를 기본 검사로 실행한다.
5. 관련 테스트는 운영 DB·외부 API·파일을 바꾸지 않는지 확인한 뒤 대상만 실행한다.
6. 변경 파일의 diff와 원격 상태를 다시 확인한다.

운영 헬스체크는 `https://coconut.ai.kr/health/`이며 정상 본문은 `ok`다. 배포는 이 스킬에서 실행하지 않고 `fundkeeper-deploy`를 따른다.
