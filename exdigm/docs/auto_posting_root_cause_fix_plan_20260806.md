# 운영 자동게시 근본 원인 수정 통합 계획

## 1. 목표

- 2026-08-06 운영 publish 4건에서 확인된 자동게시 결함을 사이트별 단일 성공 경로 안에서 해결한다.
- 특정 프로젝트명, `천안`, `서초구`, 특정 날짜 같은 사례값을 코드 조건으로 추가하지 않는다.
- 이미 성공한 엑스다임 공고 4건은 변경하지 않는다.
- 실패 사이트는 게시 전에 정확한 사이트 입력값을 만들고, 만들 수 없으면 외부 사이트 진입 전에 이해 가능한 오류로 중단한다.
- 국내 근무지를 계정 기본 주소로 게시하는 Incruit·Saramin의 숨은 오게시 경로도 함께 제거한다.
- 모든 외부 게시 제목은 `<클라이언트 설명>-<JD 포지션>` 한 규칙으로 생성한다.

## 2. 작업 경계

### 변경 대상

- `projects/services/auto_posting_workflow.py`
  - 공통 게시 제목, 사이트별 의미 매핑, 문서 마감일, 담당자 snapshot
- `auto_posting/sites/jobkorea.py`
  - 현재 로그인 상태와 공고등록 진입 컨트롤
- `auto_posting/sites/businesspeople.py`
  - 지역 하위값, 저장 경고, 입력 사후 검증
- `auto_posting/sites/incruit.py`
  - 국내·해외 근무지 선택과 사후 검증
- `auto_posting/sites/peoplenjob.py`
  - 옵션 자료 기반 근무지 입력 검증
- `auto_posting/sites/saramin.py`
  - 정확한 회원 ID와 실제 근무지 입력 검증
- 기존 `auto_posting/site_maps/<site>/field-map.json`
  - 운영 화면에서 확인한 선택 옵션과 계층만 보완
- 기존 사람인 회원 ID 모델·폼·템플릿·migration 변경
- 자동게시·프로필 관련 집중 테스트와 번역

### 보존 대상

- 엑스다임 외부 공고 4건
- 프로젝트 JD, 공고문, 담당자 선택, 자격증명
- 자동게시 사이트 목록과 명령 진입점
- 현재 작업트리의 알림 UI 관련 사용자 변경
- 별도 러너·임시 스크립트·우회 URL·폴백 경로를 만들지 않는다.

## 3. 수정 전 하드 게이트

### 최소 구현 게이트

`2단계에서 멈춤 — 기존 workflow payload 생성, 5개 사이트 클래스, site_maps, User 프로필 폼이 모두 존재하므로 그 경로를 교체·축소한다.`

확인 근거:

- `projects/services/auto_posting_workflow.py`: `_businesspeople_location`, `_peoplenjob_location_tags`, `_incruit_workplace`, `_saramin_workplace`, `_businesspeople_date`, `_posting_contact_snapshot`
- `auto_posting/sites/jobkorea.py`: `_login`, `_click_register_menu`, `_open_register`
- `auto_posting/sites/businesspeople.py`: `_fill`, `_publish_current_form`
- `auto_posting/sites/incruit.py`: `_select_region`
- `auto_posting/sites/saramin.py`: `_fill_workplace`, `_select_internal_manager`
- `auto_posting/site_maps/*/field-map.json`: 사이트별 실측 옵션 자료

### SSP 잠금

현재 최종 경로:

```text
프로젝트 저장
→ enqueue_posting_workflow
→ process_auto_posting_run
→ build_auto_posting_payload
→ AutoPosting.main
→ sites/<site>.py::run
```

병합 위치:

- 게시 제목: `build_auto_posting_payload`가 모든 사이트 payload를 만들기 직전의 공통 제목 생성 단계
- 의미 해석: `build_auto_posting_payload`가 호출하는 기존 사이트별 projection 단계
- 기계적 입력: 각 `sites/<site>.py`의 기존 입력·검증 단계
- 화면 옵션: 각 사이트의 기존 `field-map.json`
- 담당자 신원: 기존 사용자 프로필 → run snapshot → Saramin 담당자 선택 단계

대체·정리 대상:

- JobKorea 이전 DOM 전용 상태 판정과 CSS selector
- PeopleNJob의 일부 지역 직접 분기
- Incruit·Saramin의 시·도 문자열 기반 국내/해외 판정과 국내 기본 주소 유지
- BusinessPeople의 불완전한 하위 지역 매핑
- BusinessPeople의 프로젝트 마감일 사용
- BusinessPeople의 학력 선호 문구 직접 전달
- Saramin의 이메일·이름 추정 담당자 연결
- 사이트마다 `project.title`을 직접 게시 제목으로 전달하는 중복

엔트로피 판정:

- 새 실행 경로는 만들지 않는다.
- 여러 지역 사례 분기를 사이트 옵션을 소비하는 projection 한 경로로 교체한다.
- Incruit의 분리된 의미 매핑 호출은 한 form projection으로 합쳐 LLM 호출 수를 줄인다.
- 직접 URL 또는 selector fallback을 추가하지 않고 현재 컨트롤 하나로 교체한다.

### 공통 게시 제목 계약

- 형식: `<client.description>-<project.title>`
- 예시: `국내 대표 OLED/반도체 유기재료 기업-CP개발그룹 개발`
- 고객사 설명은 `Client.description`의 앞뒤 공백만 제거해 그대로 사용한다.
- 포지션은 프로젝트에 저장된 JD 포지션명 `Project.title`의 앞뒤 공백만 제거해 사용한다.
- 운영 데이터에서 내부 분석값 `requirements.position`에 `(Conductive Particle)` 같은 부연 설명이 붙는 사례가 확인됐으므로 게시 제목 원천으로 사용하지 않는다.
- `(신입 ~ 대리급)` 같은 직급 문구를 별도 문자열 규칙으로 잘라내지 않는다. 프로젝트 제목이 곧 게시용 JD 포지션명의 정본이다.
- 고객사 설명이나 프로젝트 제목이 비어 있으면 임의 대체값을 만들지 않고 브라우저 진입 전에 실패한다.
- 공통 제목은 BusinessPeople `title`, PeopleNJob·JobKorea·Incruit·Saramin `posting_title`, Exdigm의 공개 제목 필드에 동일하게 전달한다.
- 사이트의 별도 포지션·부서 필드는 구조화된 포지션만 유지한다.

## 4. LLM과 스크립트 책임

### LLM 책임

- 원문 근무지와 고객사 주소를 함께 읽고 대상 사이트의 정확한 지역 옵션을 선택한다.
- 학력 등급과 전공 우대를 구분하고 대상 사이트의 정확한 학력 옵션을 선택한다.
- 증거가 부족하면 옵션을 추정하지 않고 `needs_human_review`로 반환한다.

### 스크립트 책임

- 사이트 옵션 자료와 LLM 입출력을 전달한다.
- 반환 label이 실제 옵션에 존재하는지, 필수 상·하위 값이 모두 있는지 검사한다.
- 외부 사이트의 보이는 컨트롤에 값을 입력하고 같은 값이 반영됐는지 확인한다.
- 문서 마감일만 외부 공고 마감일로 사용한다.
- 필수 결과가 없으면 게시 전에 명시적으로 실패한다.

### 필수 출력 계약

- Location: 사이트가 요구하는 상·하위 label 또는 국내 주소가 모두 존재한다.
- Education: 사이트의 정확한 학력 enum 하나와 전공 우대의 분리 근거가 존재한다.
- Manager: 내부 사용자와 외부 사이트 회원 ID가 정확히 일치한다.
- Navigation: 현재 로그인 상태와 공고등록 화면 도달을 URL·제목·보이는 marker로 확인한다.

## 5. 사이트별 구현 순서

### 5.1 JobKorea

1. 운영 공유 브라우저에 읽기 전용으로 연결한다.
2. 현재 로그인 상태 marker와 보이는 `공고등록` 컨트롤의 tag·accessible name·href·postcondition을 확인한다.
3. 이전 session marker와 등록 selector를 현재 컨트롤 하나로 교체한다.
4. 직접 등록 URL, 구 selector fallback, 재로그인 반복은 추가하지 않는다.
5. 공식 dry에서 로그인 재사용 → 등록 화면 도달 → 필드 검증을 확인한다.

### 5.2 BusinessPeople

1. 기존 industry/job LLM projection에 location과 education을 합쳐 한 번에 선택한다.
2. 국내 시·도 선택 후 나타나는 필수 시·군·구 옵션을 운영 화면에서 읽기 전용으로 확인해 field-map에 반영한다.
3. 외부 공고 마감일은 `document_deadline`만 사용하고, 없으면 `채용 시 마감`을 사용한다.
4. 저장 뒤 보이는 모든 경고 dialog 문구를 실제 실패 이유로 보존한다.
5. 지역 상·하위값과 학력값을 사후 검증한다.

### 5.3 PeopleNJob

1. 기존 field-map의 전체 근무지 옵션을 LLM에 제공한다.
2. 일부 서울·중국 직접 분기를 exact option label 검증으로 교체한다.
3. 존재하지 않는 label이나 모호한 결과는 브라우저 진입 전에 실패시킨다.

### 5.4 Incruit

1. 분리된 industry·education 의미 매핑과 workplace 판정을 한 form projection으로 합친다.
2. 국내·해외 지역 레이어의 현재 상·하위 옵션과 적용 후 표시 영역을 읽기 전용으로 확인한다.
3. 국내도 계정 기본 주소를 유지하지 않고 source-backed 지역을 직접 선택한다.
4. 선택 결과가 화면 표시와 일치하지 않으면 게시 전에 중단한다.

### 5.5 Saramin

1. 현재 작업본의 `saramin_member_id` 모델·폼·snapshot·정확 일치 변경을 보존해 완성한다.
2. 기존 job selection LLM projection에 workplace mode와 site option을 합친다.
3. 국내 주소 변경 UI와 해외 국가 UI를 읽기 전용으로 확인한다.
4. 국내도 계정 기본 주소를 유지하지 않고 source-backed 주소를 입력·검증한다.
5. 회원 ID가 없거나 외부 멤버 목록과 일치하지 않으면 run 생성 전 또는 게시 전에 중단한다.

## 6. 프로필 화면 IAC

- 사용자 의도: 설정의 기본 프로필에서 사람인 멤버 권한 화면에 표시되는 회원 ID를 저장한다.
- Given: 로그인한 활성 사용자, 기존 프로필 form
- 입력 SSOT: `User.saramin_member_id`
- When: 기존 프로필 저장 버튼 → 기존 settings POST → `ProfileForm` → User 저장
- Then: 같은 프로필 영역에 저장값이 유지되고, 누락 시 사람인 사이트 선택 단계에서 다음 행동이 보이는 오류를 표시한다.
- 변경 경계: 기존 프로필 form 내부 필드 한 개와 기존 저장 흐름만 사용한다.
- 불변조건: 다른 프로필 입력, URL, 탭, 스크롤, 자동게시 담당자 선택은 유지한다.
- 실패: 입력 오류를 해당 필드 아래에 표시하고 사용자가 입력을 고칠 수 있게 한다.
- UX: 기존 `.form-control`, label, 도움말, focus 규칙을 재사용하며 새 CSS를 만들지 않는다.

## 7. 테스트와 검증

### 자동 테스트

1. 모든 사이트 제목이 `<클라이언트 설명>-<JD 포지션>`으로 같아지는 red test를 먼저 만든다.
2. 고객사 설명이나 프로젝트 제목 누락 시 게시 전 실패하는 테스트를 추가한다.
3. 일반화된 실패 입력으로 사이트별 red test를 먼저 만든다.
4. 사이트별 projection 계약 테스트를 통과시킨다.
5. 담당자 snapshot·migration·profile form 테스트를 통과시킨다.
6. 공유 pytest 잠금 명령으로 자동게시·프로필 집중 테스트를 실행한다.
7. 변경 영향 범위의 기존 회귀 테스트를 실행한다.

### 실제 최종 경로

사이트별로 한 번에 하나씩 실행한다.

```text
manage.py autoposting_browser status
manage.py autoposting --site <site> --mode dry --payload <worker-generated-or-package-sample>
```

필수 증거:

- JobKorea: 로그인 재사용 marker, 공고등록 화면 URL·제목
- BusinessPeople: 정확한 상·하위 지역·학력·문서 마감일
- PeopleNJob: field-map에 존재하는 지역 label
- Incruit: 실제 선택된 국내·해외 지역 표시
- Saramin: 정확한 회원 ID와 실제 근무지 표시
- 모든 dry: `submitted=false`, `published=false`
- 모든 사이트: 동일한 공통 게시 제목과 구조화된 별도 포지션 값

### UI 검증

- 공용 개발 URL의 설정 프로필 화면에서 필드 표시·입력·저장·오류를 확인한다.
- 클릭 전·저장 후 화면, console·network 오류, 입력 보존을 확인한다.

### 완료 게이트

- `uv run --locked python -m tools.code_knowledge catalog_update`
- 관련 문서와 GBrain 사건 기록 갱신
- 같은 범위의 `code-review-loop`에서 승인 finding 0건
- 관련 파일만 커밋하고 알림 UI 변경은 커밋하지 않는다.

## 8. 운영 반영과 게시물 정정

현재 작업트리에는 이 계획과 무관한 알림 UI 변경이 함께 있다. 공식 운영 배포 명령은 작업트리 전체를 자동 커밋하므로 이번 승인만으로 운영 배포하지 않는다.

관련 변경을 별도 커밋한 뒤 다음 조건이 충족되면 운영 단계로 넘어간다.

1. 무관한 변경이 별도 작업으로 정리돼 운영 배포에 포함해도 되는 상태다.
2. 공식 운영 배포 명령이 성공한다.
3. 운영에서 5개 사이트 dry가 통과한다.
4. 기존 성공 공고는 `list`로 실제 근무지를 확인한다.
5. 잘못된 Incruit 공고는 기존 기록을 이용해 정상 workflow가 닫고 교체한다.
6. 실패했던 사이트만 프로젝트별로 다시 게시한다.
7. 외부 ID·공개 URL·제목·근무지와 중복 부재를 확인한다.

운영 게시·마감·교체는 외부 상태를 바꾸므로 별도의 명시적 운영 실행 지시가 있을 때만 수행한다.

## 9. 실패 복구

- 조사 중 CAPTCHA·예상 밖 2FA·계정 잠금·결제 화면이 나오면 즉시 중단한다.
- 사이트별 공식 dry가 실패하면 그 사이트의 이번 미검증 변경만 되돌리고 분석 단계로 돌아간다.
- 임시 DOM 조사 코드와 임시 파일은 남기지 않는다.
- 한 사이트 실패 때문에 다른 사이트의 우회 경로를 추가하지 않는다.

## 10. 실행 결과

- 관련 자동 테스트: 87건 통과
- 정적 검사: 변경 Python 파일 Ruff 통과, JSON 3개 파싱 통과, diff whitespace 오류 없음
- JobKorea dry `20260806184902`: 성공, 제출·게시 없음
- BusinessPeople dry `20260806185333`: 성공, 제출·게시 없음
- Incruit dry `20260806185404`: 성공, 제출·게시 없음
- Saramin dry `20260806185811`: 성공, 제출·게시 없음
- Exdigm dry `20260806185910`: 성공, 제출·게시 없음
- PeopleNJob dry `20260806190425`: 유료 헤드헌팅 이용권이 없어 폼 진입 전 중단
- PeopleNJob 실패는 로그인·selector·payload 문제가 아니라 외부 계정 이용권 조건으로 분리했다.
- 코드 리뷰 루프 마지막 결과: 승인 finding 없음
