# 마케팅 파이프라인 (Lead → 이메일 → TM → 방문 → Next Action) 설계

- 작성일: 2026-06-09
- 상태: 합의 완료, 구현 대기
- 새 앱 이름: `marketing`

## 1. 목적과 범위

기존 R&D 컴플라이언스 OS(rndnote)에 **B2B 영업 파이프라인 미니 CRM**을 추가한다. 외부에서 수집한 잠재고객(구글 시트 등)에게 이메일을 발송하고, 후속 TM·방문·Next Action을 한 화면에서 추적·관리한다.

### 마케팅 프로세스 정의 (사용자 요구)
1. TM·광고로 관심 표명 고객 이메일을 구글 시트에 수집
2. 시트를 시스템에 임포트 → Lead DB에 적재
3. 선택한 이메일 템플릿으로 일괄 발송 (KOITA 실사 자가진단 안내 등)
4. 발송한 고객 대상 TM → 이메일 확인·관심도 확인 → 가능 시 방문 일정 확보
5. 방문 일정 관리 + 방문 결과별 Next Action 관리

### 구현 범위 (Big Bang)
1회 구현으로 위 1–5 전체와 운영 UI(HTMX), 트래킹 픽셀, 자동 상태 전이, 시드 템플릿까지 완성한다.

## 2. 합의된 결정 사항

| 항목 | 결정 |
|---|---|
| 구현 범위 | Big Bang (전체 한 번에) |
| 시트 연동 | Google Sheets API + 수동 import 버튼 (`gspread`) |
| 기존 `ConsultationRequest` | 통합 — 데이터 마이그레이션 후 모델 제거, 랜딩 폼은 Lead 직접 생성 |
| 관리 UI | HTMX 커스텀 페이지 (Pretendard + Tailwind, 기존 패턴 준수) |
| 발송 규모 | 회차당 100명 이하 → Gmail SMTP + 백그라운드 스레드로 처리, 외부 발송 서비스 불필요 |
| 열람 추적 | 자동(1px 픽셀) + TM 시 수동 확인 둘 다 |
| 활동 로깅 | 단일 `Activity` 모델로 TM/방문/메모/이메일을 한 타임라인에 통합 |

## 3. 아키텍처

### 3.1 앱 구조
- 단일 `marketing` 앱.
- 기존 앱과의 관계
  - `accounts.User` — Lead.assigned_to, Campaign.sender, Activity.performed_by의 FK 타겟
  - `companies.Company` — Lead.company는 plain string(임포트 시점엔 미등록이 일반적). 추후 won 상태에서 Company로 승격 가능(별도 트랜잭션, 본 스펙 범위 밖)
- `accounts.ConsultationRequest` 모델은 데이터 마이그레이션 후 제거. 랜딩 폼은 Lead를 직접 생성.

### 3.2 데이터 모델

모든 모델은 `common.mixins.BaseModel` (UUID PK + Timestamp) 상속.

#### Lead — 잠재고객 1명
- `email` (EmailField, unique, lowercase로 normalize)
- `name`, `phone` (CharField, blank)
- `company_name` (CharField, blank — plain string)
- `source` (Choices: `google_sheet`, `landing_page`, `tm`, `ad`, `manual`)
- `source_detail` (CharField, blank — 시트 URL, 광고 캠페인명 등)
- `status` (Choices: `new`, `contacted`, `interested`, `scheduled`, `visited`, `won`, `lost`)
- `interest_level` (Choices: `unknown`, `low`, `medium`, `high`)
- `assigned_to` (FK User, null, on_delete=SET_NULL)
- `tags` (ArrayField of CharField, blank=list — PostgreSQL 전제)
- `notes` (TextField, blank)
- `is_unsubscribed` (Boolean, default False)
- `last_contacted_at` (DateTime, null)
- DB index: `(status, assigned_to)`, `email`, `source`

#### LeadImport — 시트 임포트 이력
- `sheet_url`, `sheet_title` (CharField)
- `column_mapping` (JSONField — {`email`: 헤더명, `name`: 헤더명, …})
- `filter_rule` (JSONField, null — {`column`: 헤더명, `equals`: 값})
- `imported_count`, `skipped_count`, `failed_count` (Integer)
- `imported_by` (FK User)
- `error_log` (TextField, blank)

#### EmailTemplate — 이메일 본문 템플릿
- `name` (CharField — 운영자 식별용)
- `subject` (CharField)
- `html_body` (TextField — base64 임베드 이미지 포함 가능)
- `text_body` (TextField, blank — plain text fallback. 비어 있으면 HTML에서 자동 추출)
- `is_active` (Boolean, default True)
- `created_by` (FK User)

#### EmailAttachment — 템플릿 첨부
- `template` (FK EmailTemplate, related_name='attachments')
- `file` (FileField, upload_to='email_attachments/%Y/%m/')
- `display_name` (CharField — 수신자에게 보일 파일명)
- 업로드 시 최대 20MB 검증(Gmail 25MB 한도 고려, 본문 여유분).

#### EmailCampaign — 발송 1회 단위
- `name` (CharField — 운영자 식별용)
- `template` (FK EmailTemplate, on_delete=PROTECT)
- `status` (Choices: `draft`, `sending`, `sent`, `partial_failed`, `failed`)
- `scheduled_at` (DateTime, null — MVP는 즉시 발송만, 필드는 미래 확장 대비)
- `sent_at` (DateTime, null)
- `sender` (FK User)
- `total_recipients`, `success_count`, `failure_count`, `open_count` (Integer)
- `selection_snapshot` (JSONField — 발송 시점의 필터 조건/리드 ID 목록 스냅샷, 감사 추적용)

#### EmailSendLog — 수신자별 발송 1건
- `campaign` (FK EmailCampaign, related_name='sends')
- `lead` (FK Lead, on_delete=PROTECT)
- `to_email` (EmailField — 발송 시점 스냅샷)
- `status` (Choices: `queued`, `sent`, `failed`)
- `sent_at` (DateTime, null)
- `error_message` (TextField, blank)
- `tracking_id` (UUIDField, unique, default=uuid4)
- `opened_at` (DateTime, null — 첫 열람)
- `open_count` (Integer, default 0)
- `last_opened_at` (DateTime, null)
- Unique together: `(campaign, lead)` — 동일 캠페인 중복 발송 방지

#### Activity — 통합 타임라인 1행
- `lead` (FK Lead, related_name='activities')
- `type` (Choices: `email`, `call`, `visit`, `note`)
- `subject` (CharField — 한 줄 요약)
- `body` (TextField, blank — 상세 메모)
- `outcome` (Choices: `positive`, `neutral`, `negative`, `no_response`, `na`, default `na`)
- `scheduled_at` (DateTime, null — 방문 예약 시 사용)
- `happened_at` (DateTime, null — 실제 일어난 일시. 발생 시 채워짐)
- `performed_by` (FK User, null, SET_NULL)
- `email_log` (FK EmailSendLog, null — type=email일 때 연결)
- `next_action` (CharField, blank — 다음 액션 한 줄)
- `next_action_due` (DateTime, null)
- `next_action_done_at` (DateTime, null — Next Action 완료 시각)
- DB index: `(lead, -happened_at)`, `(next_action_due, next_action_done_at)`

### 3.3 상태 흐름 (자동 전이)

```
new
 → contacted          (캠페인 발송 성공 시 자동)
 → interested         (TM Activity outcome=positive 시 자동)
 → scheduled          (type=visit + scheduled_at 채워진 Activity 생성 시 자동)
 → visited            (type=visit + happened_at 채워질 때 자동)
 → won | lost         (수동만)
```
- 자동 전이는 한 단계씩 앞으로만(역행 X). 운영자 수동 변경은 모든 상태 자유.
- TM outcome=negative 시: `interest_level=low`만 자동 조정, status 변경 없음.

## 4. URL 구조

| URL | 화면 |
|---|---|
| `GET /marketing/` | 대시보드 |
| `GET /marketing/leads/` | Lead 목록 + 필터 |
| `GET /marketing/leads/<uuid>/` | Lead 상세 + 타임라인 |
| `PATCH /marketing/leads/<uuid>/` | 인라인 필드 편집 (HTMX) |
| `GET /marketing/leads/import/` | 시트 임포트 마법사 |
| `POST /marketing/leads/import/preview/` | 시트 fetch + 매핑 미리보기 |
| `POST /marketing/leads/import/execute/` | 임포트 실행 |
| `GET /marketing/templates/` | 템플릿 목록 |
| `GET/POST /marketing/templates/new/` | 템플릿 생성 |
| `GET/POST /marketing/templates/<uuid>/edit/` | 템플릿 편집 |
| `POST /marketing/templates/<uuid>/preview/` | 미리보기 fragment |
| `GET /marketing/campaigns/` | 캠페인 목록 |
| `GET /marketing/campaigns/new/` | 캠페인 마법사 |
| `POST /marketing/campaigns/<uuid>/test/` | 본인에게 테스트 발송 |
| `POST /marketing/campaigns/<uuid>/send/` | 발송 실행 |
| `GET /marketing/campaigns/<uuid>/progress/` | 발송 진행률 fragment (HTMX 폴링) |
| `GET /marketing/campaigns/<uuid>/` | 캠페인 결과 |
| `POST /marketing/leads/<uuid>/activities/` | 활동 기록 |
| `POST /marketing/activities/<uuid>/complete-next/` | Next Action 완료 |
| `GET /marketing/visits/` | 방문 일정 캘린더 |
| `GET /marketing/next-actions/` | Next Action 큐 |
| `GET /marketing/track/o/<uuid>.png` | 트래킹 픽셀 |
| `GET /marketing/unsubscribe/<token>/` | 수신거부 처리 |

## 5. 시트 임포트 동작

### 5.1 인증
- `.env`에 `GOOGLE_SERVICE_ACCOUNT_JSON` (JSON 문자열 그대로) 추가.
- 라이브러리: `gspread` + `google-auth`.
- 운영자는 Google Cloud Console에서 Service Account 생성 + Sheets API 활성화 + JSON 키 발급 → `.env` 추가 → Service Account 이메일을 시트에 "뷰어" 권한 공유.
- 임포트 UI 첫 화면에 "이 이메일을 시트에 공유하세요: `<service-account-email>`" 안내 표시.

### 5.2 3단계 흐름
1. **URL 입력**: 운영자가 시트 URL 붙여넣기. 서버는 `gspread`로 첫 워크시트 헤더 + 최대 100행 fetch.
2. **컬럼 매핑 + 필터 미리보기**: 시트 헤더 드롭다운으로 `email`(필수), `name`, `phone`, `company_name`, `interest_note`에 매핑. 선택적 필터(`<column> == <value>`). 미리보기 5행을 우리 필드로 변환해서 표시.
3. **실행**: 백엔드에서
   - 이메일 normalize (lowercase + trim)
   - 빈 이메일/잘못된 형식 → `failed_count++`
   - 기존 Lead와 이메일 매치 → `skipped_count++` (병합 옵션 OFF — 단순화)
   - 신규 → Lead 생성(source='google_sheet', source_detail=시트 URL)
   - 각 신규 Lead에 `Activity(type='note', subject='구글 시트 임포트', body=원본 행 데이터 JSON)` 자동 기록
   - `LeadImport` 1행 저장
   - 결과 화면: 생성 N건 / 스킵 N건 / 실패 N건 + 에러 로그

## 6. 이메일 발송 동작

### 6.1 캠페인 생성 마법사 4단계
1. **템플릿 선택** (활성 템플릿 중). 이 단계 제출 시 서버는 `EmailCampaign(status='draft')` 행을 생성하고 이후 단계 URL에서 그 UUID를 사용.
2. **수신자 선택** — Lead 목록과 동일한 필터 UI. "이 조건 N명에게 보내기" 카운트 실시간. `is_unsubscribed=True` 제외. 빠른 선택: 특정 이전 캠페인의 "미열람자"만. 제출 시 `selection_snapshot`에 필터 조건과 Lead ID 목록 저장.
3. **미리보기 + 테스트 발송** — 렌더된 HTML, 첨부 파일명 리스트. "내게 테스트 발송" 버튼이 현재 운영자 이메일로 1통 전송(SendLog는 남기지 않음).
4. **발송 실행** — 확인 모달 → 백그라운드 스레드 트리거 후 진행률 화면으로 이동. 한 캠페인은 한 번만 발송 가능(status='draft'에서만 send 허용).

### 6.2 발송 메커니즘
- 캠페인 status: `draft → sending → sent | partial_failed`
- `EmailCampaign.send()` 호출 시
  1. 선택된 Lead 목록을 `selection_snapshot`에 저장
  2. 각 수신자에 대해 `EmailSendLog(status='queued')` row 생성
  3. `threading.Thread(daemon=True)`로 워커 시작 — Django의 `connection.close_if_unusable_or_obsolete()` + 각 발송 후 sleep 300ms
  4. 각 SendLog에 대해
     - 본문 변수 치환: Python `str.format_map(SafeDict)` — `{lead.name}` 등을 안전하게 (없으면 빈 문자열). 현재 KOITA 템플릿엔 변수 없어 그대로 통과.
     - `</body>` 직전에 트래킹 픽셀 `<img>` 자동 삽입
     - `EmailMultiAlternatives` 생성, HTML attach, 첨부 파일 attach
     - From: `DEFAULT_FROM_EMAIL`, Reply-To: `campaign.sender.email`
     - 발송 → 성공 시 `status='sent'`, `sent_at` 기록. 실패 시 `status='failed'`, `error_message`.
  5. 모든 발송 완료 후 캠페인 status/카운터 업데이트. 성공한 Lead의 status가 `new`면 `contacted`로 자동 전이. `last_contacted_at` 갱신.
- 진행률 화면은 HTMX 2초 폴링으로 `success_count + failure_count` / `total_recipients` 표시.
- 백그라운드 스레드는 **Django runserver와 gunicorn(--workers ≥1) 양쪽에서 동작**. gunicorn worker가 죽으면 발송이 중간에 끊길 수 있는 위험은 인지하되, 100명 이하 + 발송 30~60초 이내 완료 가정에서 수용. 끊긴 캠페인은 "실패 N건 재시도" 버튼으로 복구.

### 6.3 트래킹 픽셀
- `GET /marketing/track/o/<uuid:tracking_id>.png`
  - SendLog 조회 → `open_count++`, `opened_at`(NULL일 때만 set), `last_opened_at=now()`
  - `EmailCampaign.open_count`도 (첫 열람일 때만) `++`
  - 1×1 투명 GIF 반환(Content-Type: image/gif), `Cache-Control: no-store`
  - 잘못된 UUID는 조용히 픽셀만 반환

### 6.4 수신거부
- 메일 본문 푸터 자동 추가: "수신을 원치 않으시면 [여기]를 누르거나 본 메일에 회신해 주세요."
- 링크: `GET /marketing/unsubscribe/<token>/` — `token`은 HMAC(SECRET_KEY, lead.id)
- 응답: "수신거부 처리되었습니다" 정적 페이지 + `Lead.is_unsubscribed=True`
- 캠페인 수신자 선택 시 `is_unsubscribed=True`는 자동 제외, 카운트에서도 차감 표시.

## 7. 화면 인터랙션 핵심

### 7.1 Lead 상세 (가장 중요한 작업 화면)
- 좌측: 기본정보 + 인라인 편집되는 상태/관심도/담당자/태그
- 우측 상단: 활동 입력 폼 (라디오: TM 통화 / 방문 예약 / 방문 결과 / 메모)
  - 공통 필드: subject(한 줄 요약), outcome, body, next_action, next_action_due
  - `TM 통화`: `happened_at=now()` 자동 채움. outcome=positive → status=interested 자동 전이.
  - `방문 예약`: `scheduled_at` 필수 입력, `happened_at`은 비움 → 자동 status=scheduled
  - `방문 결과`: `happened_at` 필수 입력(과거 일시 허용), `scheduled_at`은 기존 예약 활동에서 가져오거나 비워둠 → 자동 status=visited
  - `메모`: `happened_at=now()`만 자동. status 변경 없음.
  - 폼 제출 후 HTMX로 타임라인 fragment + 폼 리셋 + 상태 칩 갱신 반환
- 우측 하단: 시간역순 타임라인 (이모지 아이콘으로 type 구분)

### 7.2 대시보드
- 오늘 마감 Next Action 수, 이번 주 방문 일정 수
- 최근 캠페인 3건 카드 (발송 N · 열람 N · 열람률 %)
- 상태별 Lead 도넛, 출처별 유입 바 차트(서버 렌더 SVG 또는 단순 표)
- 담당자별 본인 큐 (로그인 사용자에게 할당된 활성 Lead 수)

### 7.3 Next Action 큐
- 마감일 임박 정렬, "지나간 항목"은 적색
- 행 클릭 → Lead 상세로
- 행에 "완료" 버튼 → Activity.next_action_done_at = now()

### 7.4 방문 캘린더
- 월/주 토글
- 셀에 `scheduled_at` 기준 Activity 표시 (Lead 이름)
- 클릭 → Lead 상세

## 8. 권한

- 모든 `/marketing/*`는 `@login_required` + `request.user.is_staff` 필수.
- 역할 분리 없음 — staff 전체가 모든 기능 사용.
- Lead.assigned_to는 표시·필터·대시보드 큐 용도. 권한 게이팅엔 사용하지 않음.

## 9. 데이터 마이그레이션

1. `marketing` 앱 초기 마이그레이션으로 모델 생성.
2. 데이터 마이그레이션:
   - `accounts.ConsultationRequest` 전체 row 순회 → `Lead` 생성 (source='landing_page', notes에 concern/preferred_time 합쳐 저장)
   - 각각에 `Activity(type='note', subject='랜딩페이지 상담신청', body=원본 필드)` 자동 기록
3. `accounts.views`와 폼: 상담신청 처리 흐름을 `Lead.objects.create(...)` + Activity 자동기록으로 교체. 기존 `send_consultation_request_email` 함수는 새 모듈로 이전.
4. `ConsultationRequest` 모델 제거 마이그레이션.

## 10. 시드 데이터 (마이그레이션 또는 management command)

- `EmailTemplate(name='KOITA 자가진단 안내 v1', subject='RNDlog | 2026 KOITA 실사 대비 안내', html_body=<typeA_crisis_hero_v4_two_directors.html 본문>, is_active=True)`
  - 본문은 `docs/자료/checkup-nextjs/email-html/typeA_crisis_hero_v4_two_directors.html`에서 복사
- `EmailAttachment(template=위, file=rndlog_service_guide.pdf, display_name='RNDlog 서비스 안내서.pdf')`
  - 파일은 `docs/자료/checkup-nextjs/rndlog_service_guide.pdf`를 `media/email_attachments/`로 복사
- 시드는 `python manage.py seed_marketing` 커맨드로 idempotent 실행.

## 11. 새 의존성

`pyproject.toml`에 추가:
- `gspread` (Google Sheets)
- `google-auth` (Service Account 인증)

## 12. 환경변수 추가

`.env.example`에 추가:
```
GOOGLE_SERVICE_ACCOUNT_JSON=
SITE_URL=http://localhost:8000
```
`SITE_URL`은 이미 있으나 트래킹 픽셀·수신거부 링크의 절대 URL 베이스로 사용.

## 13. 테스트 전략

- **시트 임포트**: gspread를 모킹해 헤더/행 fixture를 주고 매핑·필터·중복 처리 검증.
- **발송**: Django `mail.outbox` 사용. 동기 경로(쓰레드 대신 inline 호출)로 호출하는 테스트 헬퍼.
- **트래킹 픽셀**: 픽셀 URL GET → open_count 증가, 캐시 헤더 검증.
- **자동 상태 전이**: Activity 생성 → Lead status 검증.
- **수신거부**: 토큰 검증, 발송 제외.
- **마이그레이션**: ConsultationRequest → Lead 데이터 마이그레이션 단위 테스트(Django `MigrationExecutor`).

## 14. 배포 영향

- 새 의존성 → `Dockerfile`은 영향 없음(`uv sync`로 처리). `uv.lock` 갱신.
- 새 환경변수 → 운영 `.env`에 `GOOGLE_SERVICE_ACCOUNT_JSON` 채워야 함.
- `media/` 디렉토리 영속화(첨부 파일) — 현재 docker-compose에 볼륨 없으면 추가 필요. 본 스펙 범위에서 docker-compose 볼륨 마운트 추가.
- nginx: `media/`를 Django가 처리하도록 두거나(현 정적 자산 처리 패턴 확인 후 결정), nginx alias 추가. 정적 파일 처리 패턴이 이미 정해진 경우 그것에 맞춤.
- 백그라운드 스레드 운영: gunicorn `--workers ≥1 --threads ≥4` 권장. `docker-compose.yml`의 web 서비스 command 확인 후 필요 시 조정.

## 15. 비범위 (이번에 만들지 않는 것)

- 회신 자동 분류·이메일 답장 inbound 파싱 (이미 IMAP 정보가 .env에 있으나 본 스펙 범위 외)
- 캠페인 예약 발송(필드는 두되 즉시 발송만 구현)
- A/B 테스트, 세그먼트 자동 생성, 머신러닝 스코어링
- 다국어 템플릿
- Lead → Company 자동 승격(별도 작업)
- Celery/RQ 등 외부 작업 큐
- 외부 발송 서비스(SES/SendGrid)
- 사용자별 권한 분리(staff 통합)
