---
name: hidden-desktop-browser
description: Use when a web page must be opened, operated, extracted, downloaded from, or visually verified on the Windows control-room PC without taking over the user's current desktop.
---

# 숨은 데스크톱 브라우저

## 역할

사용자가 작업 중인 Windows 데스크톱을 전환하지 않고 별도의 Win32 데스크톱에 전용 프로필의 실제 Chrome을 생성한다. 사용자의 입력 데스크톱·전경 창·마우스·키보드·클립보드를 사용하지 않는다.

같은 수명주기 위에 두 실행 방식을 제공한다.

| 방식 | 조작·읽기 | 캡처 | 고르는 경우 |
|---|---|---|---|
| `uia` (기본값) | Windows UI Automation (Invoke·Select·Toggle·SetValue, TextPattern) | `PrintWindow` | 사이트가 Playwright·CDP·webdriver 흔적을 검사해 거부할 때(예: CRETOP dynaPath `[8004]`), 네이티브 셀렉트 박스·팝업 창을 다뤄야 할 때 |
| `playwright` | Chrome이 CDP 포트를 열고 명령마다 Playwright가 접속·해제. Chrome과 페이지 상태는 유지 | `page.screenshot` | DOM 추출, 표, 콘솔 오류·실패 요청·응답 증거, 다운로드, 계산된 스타일·overflow 측정, 웹 개발 화면 검증, contenteditable 편집기 입력 |

이 스킬의 [scripts/hidden_browser.py](scripts/hidden_browser.py)와 [scripts/run-hidden-browser.ps1](scripts/run-hidden-browser.ps1)이 공용 실행 경로다. 프로젝트 폴더에 같은 스크립트나 별도 runner를 만들지 않는다.

## 계층 계약

이 스킬은 Windows 브라우저 실행층이다. 프로젝트·사이트별 스킬은 이 스킬을 함께 적용하고 도메인 절차만 소유한다.

| 공용 실행층이 소유하는 것 | 도메인 스킬이 소유하는 것 |
|---|---|
| 숨은 데스크톱과 실제 Chrome 생성·조회·캡처·종료, 이름별 잠금 | 시작 URL, 로그인 조건, 사이트 탐색 순서 |
| 이름별 전용 프로필·CDP 포트·실행 상태·증거 폴더 | 입력 데이터와 화면별 성공·실패 판정 |
| 두 방식의 범용 조작(클릭·입력·대기·본문 추출·다운로드·JS 평가)과 관찰 기록 | 셀렉터·automation id, 추출 결과의 형식과 품질검사 |
| 사용자 데스크톱·기존 Chrome 보호, 입력값 미출력 | 결제·전송·DB 저장 같은 외부 효과와 승인 경계 |

기존 도메인 runner 안에 데스크톱·Chrome 수명주기 코드가 남아 있으면 공용 실행층을 사용하는 상태로 간주하지 않는다. 자세한 분리 기준과 라이브러리 계약은 [도메인 스킬 결합 계약](references/domain-layer-contract.md)을 따른다.

## 실행

Windows, Google Chrome, `uv`가 현재 호스트에 있어야 한다. 하나라도 없으면 대체 runner나 가상환경을 만들지 말고 누락 항목을 보고한다. 첫 실행은 `uv`가 Playwright 등 의존성을 받는 데 1~2분 걸린다.

```powershell
$runner = '<skill-folder>\scripts\run-hidden-browser.ps1'
& $runner --name <task-name> open '<url>' --backend playwright
& $runner --name <task-name> click --role button --accessible-name '<name>' --exact
& $runner --name <task-name> stop
```

모든 명령은 `--name <task-name>` 뒤에 오고 JSON 한 개를 출력한다. 대상 요소는 `--role`+`--accessible-name`(두 방식), `--automation-id`(uia), `--selector`(playwright, CSS)로 지정한다.

| 명령 | uia | playwright | 결과의 핵심 |
|---|---|---|---|
| `open <url> [--backend]` | ○ | ○ | `backend`, `cdp_port`, `data_root`, 창 목록 |
| `status` | ○ | ○ | `alive`, `windows`, `cdp_ready` |
| `snapshot` | PNG + UIA 요약 | PNG + 요소 목록 | 화면 판단용 요약 `text`(중복 제거, 기본 5,000자)와 `interactive` |
| `text` | TextPattern 전체 | `innerText` 전체 | 추출용. 중복 제거·자르기 없음 |
| `goto <url>` | – | ○ | 이동 중 `observed` |
| `click` | role·이름 또는 `--automation-id` | role·이름 또는 `--selector`, `--download-to` | 정확히 1개만 맞아야 실행 |
| `fill --value` | ValuePattern이 있는 컨트롤(role `textbox`·`combobox`·`spinbutton`) | 모든 입력·편집기 | 값은 결과에 없음 |
| `wait --text` | ○ | ○ | 0.5초 폴링, `--timeout`까지 |
| `eval --js` | – | ○ | 함수식 결과 JSON |
| `stop` | ○ | ○ | 실패하면 `ok=false`, 종료 코드 1 |

- 모든 결과에 `input_desktop_unchanged`와 `foreground_unchanged`가 붙는다. 전경 창은 사용자의 정상 조작으로도 바뀌므로, 간섭 판정은 바뀐 창의 PID가 도구가 만든 Chrome 프로세스인지로 한다(`scripts/verify_hidden_browser.py`가 이 기준으로 기록한다).
- `playwright` 명령의 `observed`는 그 접속 구간에서 관찰한 `console_errors`·`failed_requests`·`responses`·`downloads`다. 클릭이 일으키는 실패 요청은 그 `click` 결과에서 본다.
- `--name`에는 영문·숫자·점·밑줄·하이픈만 쓴다. 도메인 스킬은 `<project>-<site>-<purpose>` 형태를 정해 같은 작업에서 유지한다. `--run-id`를 주면 증거만 `evidence/<name>/<run-id>`로 나뉘고 프로필은 같다.
- `snapshot`의 PNG는 이미지로 직접 확인한다. JSON의 텍스트·요소 목록은 이미지 판단을 보조한다.
- 좌표 클릭이나 현재 데스크톱의 마우스·키보드·클립보드 입력으로 대체하지 않는다. 그 입력은 사용자의 입력 데스크톱으로 가서 사용자 작업을 가로챈다.
- 완료하거나 실패하면 `stop`으로 정리한다. 전체 Chrome 종료 명령을 사용하지 않는다.

## 입력값 보호

- 도구가 자동으로 만드는 출력(`snapshot`, `fill`·`click`·`wait` 뒤 요약, 오류 메시지)은 입력 컨트롤의 값을 읽지 않는다. `playwright` 요약은 `.value`와 편집 영역 텍스트를 수집하지 않고, `uia` 요약은 편집 컨트롤 안의 텍스트를 제외한다.
- `text`는 본문에서 편집 영역(Edit·ComboBox·Spinner 컨트롤, 키보드 포커스가 가능하고 TextEdit 패턴을 가진 Group·Custom·Text·Pane, `isContentEditable` 요소)의 텍스트 범위를 제거한다. 네이티브 `select`의 표시 옵션은 본문에 남는다.
- `eval`은 호출자가 명시적으로 요청한 추출이므로 값 제거를 적용하지 않는다. 비밀값을 고르지 않을 책임은 호출자에게 있다.
- 화면 캡처와 보이는 텍스트에 고객정보가 있으면 작업 증거 범위에서만 보존한다.

## 동시 실행과 정리

- `open`과 `stop`은 `state/<name>.lock`을 배타 점유한 상태에서 실행된다. 같은 이름의 실행이 살아 있으면 `open`은 실패한다. 다른 에이전트(Claude Code·Codex)가 같은 이름을 동시에 열어도 하나만 성공한다.
- 실패 정리는 그 실행이 만든 프로세스 트리에만 적용한다. 숨은 데스크톱에 이미 창이 있으면 종료하지 않고 실패만 보고한다.
- `stop`은 상태 파일의 PID가 기록된 Chrome 실행 파일이고 그 데스크톱의 창을 소유할 때만 종료한다.

## 프로필·데이터 경로·로그인

- 기본 데이터 경로는 `%USERPROFILE%\.hidden-browser\{profiles,state,evidence}\<name>`이다. AppData 밖에 두는 이유: Codex 데스크톱 앱은 패키지 앱이라 `AppData\Local`이 `...\Packages\OpenAI.Codex_...\LocalCache\Local`로 가상화되어, 같은 `--name`이 Claude Code와 다른 프로필을 가리키게 된다. 2026-09-13 이전에 만들어진 프로필은 그 가상 경로의 `Codex\hidden-browser\profiles`에 보존돼 있고 자동 승계하지 않는다.
- `--name`마다 별도 Chrome 프로필을 유지한다. 같은 작업은 같은 이름을 재사용해 로그인 세션을 보존하고, 서로 다른 사이트나 계정을 섞지 않는다.
- 로그인 화면이 나오면 개인 Chrome의 프로필·쿠키·비밀번호를 복사하지 않는다. 전용 프로필의 일회성 로그인이 필요하다고 보고한다. 사용자 화면에 로그인 창을 열어야 한다면 그 동작을 요청받은 뒤 실행하며, 이후 확인은 다시 숨은 데스크톱에서 수행한다.
- 자격증명은 `fill --value`로 넣되 결과·로그·증거에 값이 남지 않는다. 명령줄 인수는 프로세스 목록에 노출되므로, 도메인 adapter는 라이브러리 계약(`fill(value)`)을 쓰는 편이 안전하다.

## 실패 판정

- `ERR_CONNECTION_REFUSED`는 숨은 데스크톱 실패로 단정하지 않는다. Windows에서 대상 개발 서버나 SSH 터널에 접속할 수 있는지 확인한다.
- Chrome이 열렸지만 접근성 문서가 없으면 새 runner를 만들지 않고 URL 로드 상태와 Chrome 접근성 옵션을 확인한다.
- `uia`의 `fill`이 "found 0"이면 role이 다른 경우가 대부분이다. HTML `input[type=number]`는 `spinbutton`(Spinner), `role=combobox`인 입력은 `combobox`, contenteditable은 ValuePattern이 없어 `playwright`로만 입력한다.
- 숨은 데스크톱 Chrome에 CDP 포트를 여는 조합은 이 PC에서 정상 동작을 확인했다(2026-09-13). 이전 기록의 "CDP를 붙이면 크래시" 판정을 이유로 `playwright` 방식을 피하지 않는다. CDP를 검사하는 사이트에만 `uia`를 쓴다.
- 결과 JSON 자체를 파싱하지 못하면 `uv` 의존성 해결 실패나 PowerShell 실행 정책 문제다. 프로젝트에 가상환경을 만들지 말고 누락 항목을 보고한다.

## 검증

수정 뒤에는 같은 진입점으로 다음을 실행한다. 테스트 페이지는 `scripts/fixtures/test-page.html`이다.

```powershell
uvx ruff check <skill-folder>\scripts
python -m unittest discover -s <skill-folder>\scripts -p 'test_hidden_browser.py'
uv run --script <skill-folder>\scripts\verify_hidden_browser.py --backend playwright
uv run --script <skill-folder>\scripts\verify_hidden_browser.py --backend uia
```

`verify_hidden_browser.py`는 CLI 전체 흐름, 입력값 감시 문자열 미출력, 라이브러리 계약(`verify_library_contract.py`), 같은 이름 동시 `open` 경합, 전경 창 변경의 PID 분류를 한 번에 확인하고 보고서를 `evidence/<name>/verify-*.json`에 남긴다.

## 완료 조건

다음이 모두 확인돼야 숨은 데스크톱 화면 작업이 완료된다.

1. 실행 내내 입력 데스크톱이 유지되고, 전경 창 변경이 있었다면 도구가 만든 프로세스의 창이 아니다.
2. 대상 Chrome 창이 지정한 숨은 데스크톱에 존재한다.
3. 요청한 화면의 PNG와 접근성·요소 결과가 같은 상태를 가리킨다.
4. 필요한 조작 뒤 변경된 화면을 다시 캡처했다.
5. 결과·증거에 입력값이 없다.
6. 전용 Chrome만 종료됐고(`stopped: true`) 기존 Chrome은 유지됐다.
