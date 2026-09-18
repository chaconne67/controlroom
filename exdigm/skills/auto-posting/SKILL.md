---
name: auto-posting
description: "Use when working on the Exdigm auto_posting app — 공고 자동 게시, auto posting 실행/수정/검증/디버깅, 채용 사이트(businesspeople, exdigm, incruit, jobkorea, peoplenjob, saramin) 자동화 코드 작업, posting workflow 연동 시. 사이트별 최종 성공 단일 경로(SSP)만 남기며 진화시킨다."
---

# Auto Posting (SSP Evolution Loop)

## Core Rule — SSP (Single Success Path)

사이트별로 최종 성공 단일 경로 하나만 남긴다. 이 스킬의 목표는 실험 흔적을 쌓는 것이 아니라 `auto_posting` 앱이 실제로 워킹하는 단일 경로를 완성·유지하는 것이다.

- 우회로, 폴백, 고아 패치, 케이스 땜빵, 임시 러너, 별도 실행 스크립트를 추가하지 않는다.
- 실패하면 우회로를 만들지 말고 최종 경로 안의 해당 단계를 견고하게 고친다.
- 변경은 기존 요소를 교체·병합·삭제하는 방식으로 한다. 파일·분기·코드량이 순증가만 하는 변경은 적용하지 않는다. 성장이 불가피하면 같은 변경에서 기존 복잡도를 제거해 경로가 더 작아졌음을 보여라.
- 성공 판정은 선언된 최종 경로를 직접 실행해서만 한다. 임시 스크립트·수동 보정·바이패스로 얻은 성공은 성공이 아니다.

## Final Path (선언된 최종 경로)

```text
python manage.py autoposting --site <site> --mode <dry|test|publish> [--payload <json>] [--email ...] [--keep-open] [--timeout ms]
→ auto_posting/management/commands/autoposting.py   (명령어 진입점, mode 게이트)
→ auto_posting/autoposting.py :: AutoPosting.main()  (실행 메인 파일 1개, 사이트 클래스 디스패치)
→ auto_posting/common.py :: AutoPostingCommon        (공통 도구 파일 1개: env, timeout, site_maps, payload)
→ auto_posting/sites/<site>.py :: <Site>.run()       (사이트별 클래스 1파일)
```

구조 계약: 실행 메인 1개(`autoposting.py`) + 공통 도구 1개(`common.py`) + 사이트별 클래스 1파일. 이 구조 밖에 새 파일·러너·헬퍼 모듈을 만들지 않는다. 필요한 로직은 이 세 위치 중 하나에 병합한다.

최종 사이트 목록(코드 레지스트리가 SSOT): `businesspeople`, `exdigm`, `incruit`, `jobkorea`, `peoplenjob`, `saramin`. 새 사이트는 명시적 사용자 지시 없이 추가하지 않는다.

## Wrapper-Command Rule (웹조작 규칙)

웹조작은 브라우저 툴을 직접 조작하지 말고 래퍼 명령어를 통해서만 한다. 목적은 에이전트 조작 에러의 사전 차단과 경로 단일화다.

- 게시·로그인·폼 입력뿐 아니라 **공고 조회·마감·삭제·중복 정리**까지 모든 브라우저 조작은 `manage.py autoposting` 명령어로만 수행한다.

```bash
python manage.py autoposting --site <site> --action run   --mode <dry|test|publish>
python manage.py autoposting --site <site> --action list  --title "<공고 제목>"
python manage.py autoposting --site <site> --action close --ref "<공고 식별자>"
```

- 일회성 정리라도 임시 스크립트를 만들지 않는다. 기능이 없으면 사이트 클래스에 `list_postings`/`close_posting`을 추가해 명령어로 노출한다.
- **직접 조작 예외**: 아직 명령어가 없는 구조 탐색(리서치)에 한해, 목적·범위를 주인님께 밝히고 **승인을 받은 뒤에만** 직접 조작한다. 얻은 로직은 최종 경로 함수에 병합하고 임시 파일을 삭제해야 완료다.
- 사이트 UI가 바뀌어 탐색이 필요하면 `$web-automation` 절차(관찰 → 구조 파악 → 컨트롤 매핑 → 1액션 → 검증)로 조사만 하고, 결과는 반드시 `sites/<site>.py`와 `site_maps/<site>/`에 병합한 뒤 명령어로 재검증한다.
- 탐색 중 만든 임시 코드·스크린샷 스크립트는 병합·검증 후 삭제한다. 탐색 경로가 실행 경로로 남으면 SSP 위반이다.
- 자격증명은 `auto_posting/.env`(또는 `AUTO_POSTING_ENV_PATH`)에서 변수명으로만 참조한다. 비밀번호·OTP·쿠키·토큰을 출력·저장·커밋하지 않는다.

## Runtime Boundary (스킬 개입 금지)

오토포스팅 런타임은 엑스다임 웹앱 안에서 완결된다: JD 승인 → 프로젝트 생성 → `enqueue_posting_workflow` → 워커 `process_auto_posting_run` → payload 생성 → 엔진 실행 → 알림. **이 스킬은 런타임의 일부가 아니며 실행 흐름에 개입하지 않는다.** 스킬은 에이전트가 이 앱을 개발·수정·검증할 때 따르는 규칙이다.

## Payload

- payload는 워커가 생성한다: `projects/services/auto_posting_workflow.py::build_auto_posting_payload` (jobkorea는 LLM projection 포함). 이 코드가 payload 스키마의 SSOT다. 에이전트가 별도 스크립트로 payload를 만들지 않는다.
- jobkorea 선택형 필드의 옵션 SSOT: `site_maps/jobkorea/job-function-options.json` 등 실측 옵션 파일. LLM은 여기 있는 라벨만 verbatim 사용한다.
- 수동 dry 검증용 샘플: `auto_posting/payloads/samples/sample-<site>-payload.json` (워커 스키마와 동일한 flat 구조).
- 구 `exdigm.site_posting_payload.v1` 스키마와 build/validate 스크립트는 2026-07-09 폐기됨. 재생성 금지.

## Browser Lifecycle (열고 닫는 규칙 — 반드시 지킴)

브라우저는 비싼 자원이고, 매 실행마다 새 로그인을 하면 사이트가 과다 로그인으로 계정을 차단한다(실사용 영향). 규칙:

1. **열기 전에 먼저 확인한다.** `common.page_session()`은 등록된 공유 브라우저(`AUTO_POSTING_CDP_URL`, 기본 `http://127.0.0.1:9222`)에 먼저 접속을 시도하고, 살아 있으면 **재사용**한다. 없을 때만 새로 연다. 사이트 클래스가 직접 `chromium.launch()`를 호출하지 않는다.
2. **로그인도 먼저 확인한다.** 각 사이트 `_login()`은 기존 세션이 로그인 상태인지 확인하고, 로그인되어 있으면 **재로그인하지 않고 즉시 반환**한다.
3. **닫는 시점은 테스트 세션 전체가 끝났을 때뿐이다.** 개별 실행은 자기가 연 탭만 닫는다. 공유 브라우저는 `manage.py autoposting_browser stop` 명령으로 사람이 닫는다. 스크립트 끝에 습관적으로 `browser.close()`를 넣지 않는다.
4. **좀비 금지.** 공유 브라우저는 `autoposting_browser start/status/stop`으로만 관리한다. 임시 브라우저를 띄워놓고 방치하지 않는다(과거 6/27·6/28 좀비 Chrome이 삭제한 폴더를 되살린 사고).

개발/테스트 절차:

```bash
python manage.py autoposting_browser status   # 있으면 재사용
python manage.py autoposting_browser start    # 없을 때만
python manage.py autoposting --site <site> --mode dry   # 몇 번을 돌려도 같은 브라우저·같은 로그인 세션
python manage.py autoposting_browser stop     # 테스트 전부 끝났을 때만
```

로그인 실패 시 즉시 재시도 금지. 반복 로그인 누적은 사이트 차단을 부른다.

## Browser & Login Entry (고정 계약)

- `headless=False` 고정: 채용 사이트 로그인은 headless에서 깨진다(2026-07-09 확정). `common.chromium_launch_options()`에 하드코딩되어 있고 파라미터로 열지 않는다. headless 옵션을 되살리는 변경 금지.
- 로그인 진입 주소의 단일 소스는 `.env`의 `<SITE>_LOGIN_URL`이다 (`require_env`, 없으면 raise). 코드 상수·폴백 체인·추측 URL 금지. 로그인 주소가 바뀌면 `.env` 값을 갱신한다(코드 수정 아님).
- "로그인 확인/테스트" 요청도 별도 브라우저 탐색으로 하지 않는다. `manage.py autoposting --site <site> --mode dry` 실행의 login 단계 결과(evidence)로 판정한다.

## Modes & Safety

- `dry`: 기본. 게시 없이 경로 검증.
- `test`: 실제 게시 후 해당 run이 만든 공고만(`run_id`/`jobNo`로 확인) 즉시 마감·삭제.
- `publish`: `AUTO_POSTING_PUBLISH_ENABLED=True` 피처 플래그 없이는 실행 불가. 사용자의 명시 지시 없이 publish 하지 않는다.
- 즉시 중단·보고 조건: CAPTCHA, 계정 잠금, 보안 챌린지, 결제, 지원자 개인정보 노출, 예상 못한 불가역 액션.
- 2FA는 사람인에만 존재하며 사이트 클래스에 구현된 절차를 따른다. 잡코리아에는 2FA가 없다(레거시 문서의 잡코리아 2FA 절차는 오정보). 예상 밖의 2FA·인증 화면이 나타나면 중단·보고한다.

## Execution Environment

- 코드 수정·dry 검증 루트: 원격 `/home/chaconne/exdigm-debug`.
- 운영 게시 실행 루트: 배포가 끝난 원격 `/home/chaconne/exdigm`.
- 파이썬: 각 원격 루트의 `.venv/bin/python` 또는 `uv run python`. 시스템 `python3` 금지.
- 디버깅 worktree에는 운영 채용사이트 자격증명을 연결하지 않는다. 실제 로그인·게시 검증은 주인님의 명시적 승인 후 운영 실행 경로에서만 수행한다.
- `ModuleNotFoundError: No module named 'django'`가 즉시 나오면 실행 환경 실패로 취급하고 프로젝트 파이썬으로 재실행한다.

## Anti-Drift Gate

모드 선언(분석/테스트/수정), 병합 단계·대체 요소 지목, 순증가 금지, 고아 패치 차단 절차는 전역 지침(`AGENTS.md`/`CLAUDE.md`)의 SSP 하드 게이트를 그대로 따른다. 여기에 이 스킬의 추가 조항:

- 검증 방법 선언은 반드시 `manage.py autoposting` 최종 경로 실행이어야 한다.
- 변경 후 이전에 통과하던 사이트가 같은 경로로 여전히 통과하는지 확인한다.

## One-Site Loop

한 번에 한 사이트만 진화시킨다.

1. 대상 사이트 하나를 선택한다.
2. `--mode dry`로 최종 경로를 실행한다.
3. 실패하면 Failure Loop를 돌리고, 통과하면 필요 시 `--mode test`로 실게시·정리까지 검증한다.
4. 통과 후 코드를 증류(distill)하고 다음 사이트로 넘어간다.
5. 여러 사이트를 동시에 배치 수정하지 않는다. 단, 하나의 공통 결함(예: common.py 버그)이 원인으로 검증된 경우는 공통 수정 후 전 사이트 회귀 실행한다.

## Failure Loop

원인 분석 절차는 전역 지침(`AGENTS.md`/`CLAUDE.md`)의 문제 해결 원칙(수정 전 게이트, 3/5 Whys, 줌아웃/줌인 리셋)을 그대로 따른다. 여기에 이 스킬의 도메인 적용:

- 증거원: 로그, 스크린샷, DOM 덤프, `site_maps/`, run 결과(run_id, 성공 마커, 최종 URL).
- 수정 위치는 사이트 클래스 / common / payload / site_map / 명령어 게이트 중 하나로 결정하고 가장 작은 일반 수정만 적용한다.
- 판정은 같은 `manage.py autoposting` 명령어 재실행으로만 한다. 재시도 반복으로 얻은 확률적 성공은 통과가 아니다.

기존 소스 우선 순서: 현재 `auto_posting` 코드 → `site_maps/<site>/field-map.json` → `payloads/samples/` → 이 스킬의 `references/site-domain-knowledge.md` → GBrain 페이지. 문서와 현재 코드가 다르면 코드가 이긴다. (구 `job-sites` 오케스트레이터 스킬과 사이트별 레거시 스킬 6개는 필수 내용을 이 스킬의 references로 이관한 뒤 삭제됨. 재생성하지 않는다.)

## Rule Admission

일반 규칙만 코드·site_map에 넣는다.

- 특정 공고 제목, 특정 회사명, 특정 payload 값, 1회성 좌표 하드코딩 금지.
- 셀렉터 채택 기준(보이는 컨트롤·프레임 소유·사후 검증)은 `$web-automation`의 컨트롤 매핑 규칙을 따른다.
- 의미 판단(문구 생성·분류)은 LLM/상위 워크플로우 책임으로 두고, 사이트 클래스는 기계적 입력·검증만 담당한다.

## Distillation

통과 후 반드시 정리한다:

- 임시 러너, 진단 출력, 방어적 분기, 죽은 셀렉터, 사용 안 하는 site_map 항목 제거.
- 두 사이트 이상에서 반복된 로직은 `common.py`로 승격하고 사이트 클래스에서 삭제.
- 최종 경로가 위에서 아래로 읽히는지 확인.

## Reporting

사이트 단위로 보고한다: 대상 사이트와 mode, pass/fail 판정과 증거(최종 URL, 성공 마커, run_id, 정리 결과), 실패 시 검증된 근본 원인, 적용한 일반 수정, 남은 리스크/블로커.

마지막에 SSP 마감 점검을 보고한다:

- 최종 경로가 진화했는가?
- 고아 패치나 별도 경로가 생겼는가? (기대 답: 아니오. 생겼으면 제거하거나 블로커로 보고)
- `autoposting.py` + `common.py` + `sites/<site>.py` 구조가 그대로 컴팩트하게 유지됐는가?

작업 종료 후 재사용 가능한 결정·검증 결과·교훈을 GBrain(`project/exdigm-auto-posting-process-policy` 등 관련 페이지)에 기록한다.

## References

- `references/site-domain-knowledge.md`: 코드에 없는 사이트별 필수 지식 — env 변수, 관리(읽기) URL, 2FA 사실(사람인만 존재), 사이트별 함정, 폐기된 접근 (코드 우선).
