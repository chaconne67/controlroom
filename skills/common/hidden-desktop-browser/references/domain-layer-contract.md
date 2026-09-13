# 도메인 스킬 결합 계약

## 목적

프로젝트별 스킬은 사이트 업무를 설명하고, 숨은 데스크톱과 Chrome 제어는 `hidden-desktop-browser` 하나가 담당한다. 이 경계를 지키면 한 PC에서 여러 프로젝트를 작업해도 브라우저 실행 코드를 복제하지 않고 사용자의 현재 화면을 건드리지 않는다.

## 적용 대상과 제외 대상

- 대상: Windows 조정실 PC에서 실행하는 모든 브라우저 작업 — 스크래핑·추출, 게시·입력, 다운로드, 원격 개발 서버의 화면 검증.
- 제외: 서버에 상주하며 서버 IP·프로필·잠금 계약에 묶인 자동화(예: exdigm 오토포스팅의 xvfb Chrome + CDP), 원격 Windows PC의 좌표 조작 경로. 이들은 자기 경로를 유지하며 이 스킬로 옮기지 않는다.

## 도메인 스킬이 시작할 때

1. `hidden-desktop-browser`를 함께 읽는다.
2. 프로젝트·사이트·작업을 구분하는 실행 이름을 정하고, 방식(`uia`·`playwright`)을 SKILL.md의 선택표로 고른다.
3. 공용 `open` 결과에서 입력 데스크톱과 전경 창이 유지됐는지 확인한다.
4. 도메인 스킬의 URL·로그인·탐색·입력·결과 계약을 수행한다.
5. 공용 `snapshot`·`text`와 도메인 결과를 같은 `--run-id`로 연결해 검증한다.
6. 후속 작업이 없으면 공용 `stop`으로 그 실행이 소유한 Chrome만 정리한다.

## 라이브러리 계약 (adapter 코드)

CLI로는 세션 안의 요소 핸들을 이어 쓸 수 없으므로, 여러 단계를 한 프로세스에서 수행하는 adapter는 모듈을 import한다.

```python
import sys
sys.path.insert(0, r"<skill-folder>\scripts")   # 키트 정본. 프로젝트에 복사하지 않는다.
from hidden_browser import HiddenBrowser

browser = HiddenBrowser("<project>-<site>-<purpose>", run_id=run_id)
browser.open(url, backend="uia")                  # 또는 "playwright"
with browser.uia_session() as (window, document): ...        # pywinauto 래퍼
with browser.playwright_session() as (page, observed): ...   # Playwright page
browser.fill(value, automation_id="...")           # 값이 프로세스 목록·결과에 남지 않는다
browser.stop()
```

- 의존성(`pywinauto`, `playwright`, `pywin32`, `pillow`)은 모듈 머리의 `uv` 스크립트 메타데이터와 같아야 한다. adapter를 `uv run --script`로 실행하거나 같은 버전을 가진 환경에서 실행한다.
- `uia_session()`은 **호출한 스레드**를 숨은 데스크톱에 붙인다. 그 스레드에서 pywinauto·comtypes·tkinter 같은 GUI 모듈을 import하기 전에 첫 호출해야 한다(창이나 훅을 가진 스레드는 `SetThreadDesktop`이 실패한다). 같은 스레드의 반복 호출은 붙어 있는 데스크톱을 재사용하고, 데스크톱 핸들은 프로세스가 끝날 때까지 도구가 보관한다. 같은 프로세스에서 다른 이름을 쓰려면 새 스레드에서 호출한다. 붙어 있는 스레드에서 다른 이름을 요청하면 `RuntimeError`가 난다.
- `playwright_session()`은 접속만 만들고 끝나면 접속만 끊는다. Playwright 객체는 스레드 간 공유가 보장되지 않으므로 각 세션은 호출 스레드에서 생성·사용·종료하고 `page`를 다른 스레드로 넘기지 않는다.
- 화면 전환 직후 요소가 다시 만들어지는 사이트에서는 요소를 행동마다 새로 찾는다. 잡아 둔 요소를 재사용하지 않는다.
- 도메인 adapter가 결과 본문을 만들 때는 공용 `text`처럼 편집 영역을 제외한 본문을 쓰고, 로그인 계정 식별자 같은 값이 본문에 포함되면 저장 전에 제거한다.

## 기능을 추가할 위치

| 필요한 기능 | 추가 위치 |
|---|---|
| 모든 사이트에서 쓸 수 있는 입력·선택·스크롤·창 조회·다운로드·관찰 | 공용 실행층 |
| 특정 사이트의 화면 이름·단계·팝업·로그인 복구 | 도메인 스킬 또는 domain adapter |
| 결과 파싱·완전성 검사·업무 모델 연결 | 도메인 adapter |
| 결제·발송·업로드·DB 저장 승인 | 도메인 스킬과 프로젝트 지침 |

공용 조작이 부족하다는 이유로 프로젝트 폴더에 Win32 데스크톱 생성, Chrome 프로필 관리, 전체 Chrome 종료, 캡처 기능을 다시 만들지 않는다. 먼저 공용 실행층에 추가할 수 있는 범용 기능인지 판정하고, 추가하면 `scripts/verify_hidden_browser.py`로 두 방식을 다시 검증한다.

## 기존 runner를 전환할 때

기존 runner가 브라우저 수명주기와 도메인 절차를 함께 가진 경우 한 번에 두 경로를 겹쳐 실행하지 않는다.

1. 기존 성공 사례와 결과 계약을 잠근다.
2. 공통 수명주기를 `HiddenBrowser`로 교체한다. 기존 runner의 데스크톱 이름·프로필 경로는 공용 이름·경로로 바뀌므로, 보존할 로그인 상태가 있으면 전환 전에 프로필 복사를 따로 결정한다.
3. 도메인 adapter에는 사이트 조작과 결과 처리만 남긴다.
4. 기존 성공 사례, 같은 원인의 실패 변형, 사용자 데스크톱 비간섭을 함께 검증한다.
5. 검증된 뒤 중복된 수명주기 코드를 제거한다.

전환이 끝나지 않았으면 도메인 스킬에 현재 호환 경로와 미통합 부분을 밝히고, 공용층을 사용한다고 보고하지 않는다.
