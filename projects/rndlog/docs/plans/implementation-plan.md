# rndlog — 전체 구현 계획

> 기반: ../../CONTEXT.md
> 작성일: 2026-04-12

---

## Phase 구조 개요

| Phase | 이름 | 핵심 목표 | 의존성 |
|:-----:|------|----------|--------|
| 0 | 기반 인프라 | Django 프로젝트, DB, 인증, 기업/연구소 CRUD | 없음 (완료) |
| 1 | 과제 + 연구노트 핵심 | Project, MonthlyNote CRUD + AI 연구노트 생성 | Phase 0 |
| 2 | 연구주제 발굴 + 로드맵 | TopicDiscovery, MonthlyMilestone + AI 리서치 | Phase 1 |
| 3 | PDF 생성 + 증빙 체인 | WeasyPrint PDF, 타임스탬프 체인, 서명 | Phase 1 |
| 4 | 보고서 + 비용 관리 | 계획서, 완료보고서, 연구과제총괄표, 비용 | Phase 1, 3 |
| 5 | 대시보드 | 컨설턴트/CEO/연구원 역할별 대시보드 | Phase 1, 4 |
| 6 | Voice Layer | STT, 음성 보고, 미팅 녹음 분석 | Phase 1 |
| 7 | 컴플라이언스 캘린더 + 알림 | 기한 관리, 텔레그램 알림, 변경신고 감지 | Phase 5 |
| 8 | 텔레그램 보이스 채널 | 텔레그램 봇 통합, 음성 명령 | Phase 6, 7 |
| 9 | 세액공제 증빙 패키지 + 내보내기 | ZIP 일괄 내보내기, KOITA 가이드 | Phase 4 |

---

## Phase 0: 기반 인프라 (완료)

### 상태: 완료

이미 구현된 것:
- Django 프로젝트 스켈레톤 (main, common, accounts, companies)
- User 모델 (AbstractUser + UUID PK)
- Company, Membership, ResearchInstitute, Researcher 모델
- 이메일 로그인
- BaseModel (UUID PK + timestamps)
- LLM 클라이언트 (common/llm.py)
- Tailwind CSS + HTMX 기반 프론트엔드
- base.html (로딩/토스트/HTMX 패턴)
- docker-compose.yml, Dockerfile, dev.sh

---

## Phase 1: 과제 + 연구노트 핵심

### 목표

"기업의 월간 연구 활동 원자료를 바탕으로 AI가 연구노트를 작성한다" — 제품의 핵심 가치 검증.

### 1.1 Django 앱 생성

**research 앱** 신규 생성.

### 1.2 모델

```
Project
  title, description, period_start, period_end, status
  budget_personnel, budget_material, budget_outsource
  institute → ResearchInstitute (FK)

MonthlyNote
  researcher → Researcher (FK)
  project → Project (FK)
  month: DateField
  activities, challenges, results (입력 필드)
  ai_draft_text, final_text (AI 생성 필드)
  status: draft/researcher_signed/manager_approved/pdf_generated
  created_at, updated_at

NoteAttachment
  note → MonthlyNote (FK)
  file, filename, description
```

Phase 1에서는 타임스탬프 증빙 체인(notified_at, viewed_at 등)과 서명을 포함하지 않는다. draft → researcher_signed → manager_approved 3단계 상태만 구현.

### 1.3 뷰/URL

```
/projects/                          → 과제 목록
/projects/new/                      → 과제 생성 폼
/projects/<id>/                     → 과제 상세
/projects/<id>/edit/                → 과제 수정
/projects/<id>/notes/               → 연구노트 목록
/projects/<id>/notes/new/           → 연구노트 작성 폼
/projects/<id>/notes/<id>/          → 연구노트 상세
/projects/<id>/notes/<id>/generate/ → AI 초안 생성 (POST)
/projects/<id>/notes/<id>/approve/  → 연구소장 승인 (POST)
```

### 1.4 템플릿

- `research/project_list.html` — 과제 목록 (카드)
- `research/project_detail.html` — 과제 상세
- `research/project_form.html` — 과제 생성/수정 폼
- `research/note_list.html` — 연구노트 목록
- `research/note_form.html` — 연구노트 작성 폼 (activities, challenges, results 입력)
- `research/note_detail.html` — 연구노트 상세 (AI 초안 + 최종본)

### 1.5 AI 연구노트 생성 서비스

```python
# research/services/note_generator.py

def generate_note_draft(note: MonthlyNote) -> str:
    """연구노트 AI 초안 생성."""
    # 입력: note.activities, challenges, results + project 정보 + company 업종
    # System prompt: 업종별 템플릿 + KOITA 요건
    # 출력: 구조화된 연구노트 텍스트
```

**System Prompt 핵심:**
- 업종별 분기 (company.industry)
- 제3자 재현 가능성 강조
- 기술적 불확실성/차별성 강조
- 사용자 입력 데이터만 사용 (hallucination 방지)

### 1.6 권한

- 연구원: 자기 노트 CRUD + AI 생성 요청
- 연구소장: 소속 연구소 노트 승인
- 컨설턴트: 관리 기업 전체 열람
- CEO: 자사 열람

### 1.7 검증 기준

- [ ] 과제 CRUD 동작
- [ ] 연구노트 폼 입력 → AI 초안 생성
- [ ] AI 초안 품질: SW/IT 업종 샘플 1건 작성하여 양식 충족 확인
- [ ] 승인 플로우 (draft → researcher_signed → manager_approved) 동작

---

## Phase 2: 연구주제 발굴 + 로드맵

### 목표

"기업 프로필을 입력하면 AI가 연구주제를 제안하고 12개월 로드맵을 생성한다."

### 2.1 모델

```
CompanyProfile (companies 앱 확장)
  company → Company (OneToOne)
  main_products, core_technologies, expansion_direction, market_context
  onboarding_completed

TopicDiscovery (research 앱)
  company → Company (FK)
  company_context: TextField
  ai_research_results: JSONField
  status: draft/completed

TopicCandidate (research 앱)
  discovery → TopicDiscovery (FK)
  title, description, uncertainty_points, differentiation
  benchmarks: JSONField
  estimated_duration_months
  required_capabilities, government_project_linkage
  status: proposed/selected/rejected

MonthlyMilestone (research 앱)
  project → Project (FK)
  month_number (1~12), target_month
  objective, tasks (JSONField), references (JSONField)
  expected_outputs, note_guide
  status: upcoming/in_progress/completed/delayed
  actual_result
```

### 2.2 뷰/URL

```
/companies/<id>/profile/edit/        → 온보딩 프로필 편집
/topics/                             → 주제 발굴 목록
/topics/new/?company=<id>            → 주제 발굴 시작 (POST → AI 리서치)
/topics/<id>/                        → 발굴 결과 (후보 3~5개)
/topics/<id>/select/<candidate_id>/  → 주제 선정 → Project 생성

/projects/<id>/milestones/           → 월별 로드맵
/projects/<id>/milestones/generate/  → AI 로드맵 생성 (POST)
/projects/<id>/milestones/<id>/      → 마일스톤 상세
```

### 2.3 AI 서비스

```python
# research/services/topic_discovery.py
def discover_topics(company: Company, profile: CompanyProfile) -> list[dict]:
    """웹 검색 기반 연구주제 후보 3~5개 생성."""

# research/services/roadmap_generator.py
def generate_roadmap(project: Project, candidate: TopicCandidate) -> list[dict]:
    """12개월 MonthlyMilestone 생성."""
```

### 2.4 MonthlyNote와 MonthlyMilestone 연계

Phase 1의 MonthlyNote에 `milestone` FK 추가.
연구노트 작성 시 해당 월의 milestone.objective, tasks, note_guide를 폼에 표시.
AI 초안 생성 시 milestone 정보를 컨텍스트로 전달.

### 2.5 검증 기준

- [ ] 기업 프로필 입력 (구조화 폼)
- [ ] AI 연구주제 발굴 → 3~5개 후보 생성
- [ ] 후보 중 하나 선정 → Project 자동 생성
- [ ] AI 12개월 로드맵 생성 → MonthlyMilestone 12개 생성
- [ ] MonthlyNote 작성 시 milestone 가이드 연동

---

## Phase 3: PDF 생성 + 증빙 체인

### 목표

"승인 완료된 연구노트가 법적 요건을 충족하는 PDF로 자동 생성된다."

### 3.1 PDF 파이프라인

```python
# research/services/pdf_generator.py
def generate_note_pdf(note: MonthlyNote) -> str:
    """MonthlyNote → HTML → WeasyPrint → PDF → 파일 저장 → 해시 계산."""
```

1. MonthlyNote.final_text → Django Template으로 HTML 렌더링
2. WeasyPrint로 PDF 변환 (A4, 머리글, 페이지번호, 서명란)
3. PDF 메타데이터에 타임스탬프 임베딩
4. SHA-256 해시 계산 → `note.pdf_hash`에 저장
5. 파일 저장: `media/notes/{company_id}/{project_id}/{year_month}.pdf`

### 3.2 타임스탬프 증빙 체인

MonthlyNote 모델에 필드 추가:
```
notified_at, viewed_at, draft_created_at,
researcher_signed_at, manager_approved_at, pdf_generated_at
```

각 상태 전환 시 해당 타임스탬프 자동 기록.

### 3.3 전자서명

```
SignatureRegistry (accounts 앱 또는 별도)
  user → User (FK)
  signature_image: FileField
  signature_type: image/certified_digital
  registered_at
```

MonthlyNote에 서명 FK 추가:
```
researcher_signature → SignatureRegistry (FK, null)
manager_signature → SignatureRegistry (FK, null)
```

### 3.4 PDF 템플릿 (HTML)

업종별 4종 × 문서유형별 분기:
- `research/pdf/note_base.html` — 공통 레이아웃
- `research/pdf/note_sw_it.html` — SW/IT 특화 (Git 커밋 섹션)
- `research/pdf/note_manufacturing.html` — 제조업 특화 (실험조건 테이블)
- `research/pdf/note_bio.html` — 바이오 특화 (IRB, 시약 정보)
- `research/pdf/note_service.html` — 서비스업 특화

### 3.5 뷰/URL 추가

```
/accounts/signature/                 → 전자서명 등록/관리
/accounts/signature/upload/          → 서명 이미지 업로드
/projects/<id>/notes/<id>/sign/      → 연구원 서명 (POST)
/projects/<id>/notes/<id>/approve/   → 연구소장 승인+서명 (POST) → PDF 자동 생성
/projects/<id>/notes/<id>/pdf/       → PDF 다운로드
```

### 3.6 검증 기준

- [ ] WeasyPrint로 PDF 생성 동작
- [ ] PDF에 타임스탬프 메타데이터 포함
- [ ] SHA-256 해시 저장 및 검증
- [ ] 서명 이미지가 PDF에 삽입
- [ ] 업종별 PDF 템플릿 4종 렌더링

---

## Phase 4: 보고서 + 비용 관리

### 목표

"과제 완료 시 AI가 완료보고서를 생성하고, 연말에 연구과제총괄표를 자동 생성한다."

### 4.1 모델

```
ResearchPlan (이미 정의)
  project → Project (OneToOne)
  ai_draft, final_version, approved_by, approved_at

CompletionReport (이미 정의)
  project → Project (OneToOne)
  ai_draft, final_version, approved_by, approved_at

CostEntry (research 앱 — 신규)
  project → Project (FK)
  researcher → Researcher (FK, null)  # 인건비일 때
  type: personnel/material/outsource
  amount: DecimalField
  month: DateField
  description: CharField
  evidence_file: FileField(null)  # 세금계산서 등
```

### 4.2 AI 서비스

```python
# research/services/plan_generator.py
def generate_research_plan(project: Project) -> str:
    """연구개발계획서 AI 초안. 입력: project + milestones + company 프로필"""

# research/services/report_generator.py
def generate_completion_report(project: Project) -> str:
    """완료보고서 AI 초안. 입력: project + 전체 MonthlyNote + milestone 달성도"""

# research/services/summary_generator.py
def generate_project_summary_table(company: Company, year: int) -> dict:
    """연구과제총괄표 데이터. 과세연도의 모든 project + 비용 집계"""
```

### 4.3 뷰/URL

```
/projects/<id>/plan/                 → 연구개발계획서
/projects/<id>/plan/generate/        → AI 계획서 생성
/projects/<id>/plan/approve/         → 계획서 승인
/projects/<id>/report/               → 완료보고서
/projects/<id>/report/generate/      → AI 보고서 생성
/projects/<id>/report/approve/       → 보고서 승인
/projects/<id>/costs/                → 비용 관리
/projects/<id>/costs/new/            → 비용 항목 추가
```

### 4.4 검증 기준

- [ ] AI 연구개발계획서 초안 생성 (별지 제3호의2 항목 충족)
- [ ] AI 완료보고서 초안 생성
- [ ] 비용 항목 CRUD
- [ ] 연구과제총괄표 자동 집계

---

## Phase 5: 대시보드

### 목표

"역할별로 다른 대시보드를 보여준다."

### 5.1 컨설턴트 대시보드

쿼리:
- 관리 기업 목록: `Membership.objects.filter(user=request.user, role='consultant').select_related('company')`
- 기업별 미작성 연구노트: 이번 달 MonthlyNote가 없는 Researcher
- 기한 임박: ComplianceDeadline 중 D-7 이내
- 세액공제 예상액: 각 기업 Project의 budget 합계 × 25%

### 5.2 CEO 대시보드

- 자사 연구소 상태
- 세액공제 예상액
- 승인 대기 문서 (ResearchPlan, CompletionReport 중 approved_at is null)
- 과제 진행 현황

### 5.3 연구원 대시보드

- 이번 달 MonthlyMilestone (할 일)
- 연구노트 작성 상태
- 과거 연구노트 목록

### 5.4 대시보드 분기 로직

```python
def dashboard(request):
    memberships = request.user.memberships.all()
    if memberships.filter(role='consultant').exists():
        return consultant_dashboard(request, memberships)
    elif memberships.filter(role='ceo').exists():
        return ceo_dashboard(request, memberships)
    elif memberships.filter(role='manager').exists():
        return manager_dashboard(request, memberships)
    else:
        return researcher_dashboard(request, memberships)
```

### 5.5 검증 기준

- [ ] 역할별 대시보드 분기
- [ ] 컨설턴트: 전체 고객사 현황 표시
- [ ] CEO: 자사 상태 + 승인 대기 표시
- [ ] 연구원: 이번 달 할 일 표시

---

## Phase 6: Voice Layer

### 목표

"음성으로 입력하면 AI가 문서로 변환한다."

### 6.1 Django 앱

**voice 앱** 신규 생성.

### 6.2 모델

```
VoiceRecording
  uploaded_by → User
  company → Company
  recorded_at, audio_file, duration_seconds
  type: onboarding_meeting/daily_report/ad_hoc
  transcript_text, speaker_segments (JSONField)
  extracted_data (JSONField)
  linked_discovery, linked_note, linked_project (FK, null)

DailyVoiceLog
  researcher → Researcher
  project → Project
  recorded_at, audio_file (null), transcript
  structured_content (JSONField)
```

### 6.3 STT 서비스

```python
# voice/services/stt.py
def transcribe(audio_file: File) -> dict:
    """Whisper API 호출 → {text, segments[{start, end, text}]}"""

def transcribe_with_diarization(audio_file: File) -> dict:
    """화자 분리 포함 전사 → {speakers[{speaker, segments}]}"""
```

### 6.4 AI 추출 서비스

```python
# voice/services/extractor.py
def extract_onboarding_data(transcript: str) -> dict:
    """미팅 전사에서 기업 프로필 데이터 추출."""
    # 출력: {main_products, core_technologies, expansion_direction, ...}

def extract_daily_report(transcript: str, project: Project) -> dict:
    """일일 보고 전사에서 연구 활동 데이터 추출."""
    # 출력: {activities, challenges, results}
```

### 6.5 뷰/URL

```
/voice/upload/                       → 음성 파일 업로드 폼
/voice/<id>/                         → 녹음 상세 (전사 + 추출 결과)
/voice/<id>/apply/                   → 추출 결과 적용 (프로필/노트에 반영)
/voice/daily/                        → 일일 음성 보고 (녹음 UI)
/voice/daily/<id>/                   → 일일 보고 상세
```

### 6.6 웹 녹음 UI

- 브라우저 MediaRecorder API로 녹음
- 녹음 완료 → 서버 업로드 → STT → 구조화
- 결과 확인 → "적용" 버튼으로 연구노트/프로필에 반영

### 6.7 검증 기준

- [ ] 오디오 파일 업로드 → Whisper STT 전사
- [ ] 미팅 녹음 → 기업 프로필 데이터 자동 추출
- [ ] 일일 음성 보고 → 구조화된 활동 데이터 변환
- [ ] 축적된 일일 보고 → 월간 연구노트 초안 연계

---

## Phase 7: 컴플라이언스 캘린더 + 알림

### 목표

"기한을 놓치지 않도록 시스템이 자동으로 알려준다."

### 7.1 Django 앱

**compliance 앱** 신규 생성.

### 7.2 모델

```
ComplianceDeadline
  company → Company
  type: koita_annual/change_report/tax_filing/monthly_note/personnel_change
  title, due_date, status: pending/completed/overdue
  reminder_sent_at, completed_at, notes
```

### 7.3 자동 기한 생성

기업 등록 시 연간 기한 자동 생성:
- KOITA 연차보고: 매년 4월 30일
- 법인세 신고: 매년 3월 31일
- 월간 연구노트: 매월 말일

변경신고 트리거:
- Researcher 모델 save signal → 변경신고 기한 자동 생성 (변경일 + 14일)

### 7.4 리마인더 서비스

```python
# compliance/services/reminder.py
def check_and_send_reminders():
    """매일 실행 (management command 또는 cron)."""
    # D-7, D-3, D-1, D-day에 알림 발송
    # 채널: 웹 알림 + 텔레그램
```

### 7.5 텔레그램 알림

```python
# compliance/services/telegram.py
def send_deadline_reminder(deadline: ComplianceDeadline):
    """텔레그램 봇으로 기한 알림 발송."""
```

### 7.6 뷰/URL

```
/compliance/                         → 컴플라이언스 캘린더 (월간 뷰)
/compliance/deadlines/               → 기한 목록 (필터: 기업, 상태)
/compliance/<id>/complete/           → 기한 완료 처리
```

### 7.7 검증 기준

- [ ] 기업 등록 시 연간 기한 자동 생성
- [ ] 연구원 변경 시 변경신고 기한 자동 생성
- [ ] 기한 D-7에 텔레그램 알림 발송
- [ ] 캘린더 뷰 렌더링

---

## Phase 8: 텔레그램 보이스 채널

### 목표

"텔레그램으로 음성 명령을 보내면 시스템이 응답한다."

### 8.1 텔레그램 봇 명령어

| 명령 | 설명 | 역할 |
|------|------|------|
| /status | 관리 기업 현황 요약 | 컨설턴트 |
| /note {기업명} | 이번 달 연구노트 상태 | 컨설턴트/연구소장 |
| /generate {기업명} | 연구노트 생성 요청 | 컨설턴트 |
| /approve {노트ID} | 연구노트 승인 | 연구소장 |
| /deadline | 임박 기한 목록 | 전체 |
| 음성 메시지 | STT → 일일 보고 기록 | 연구원 |

### 8.2 봇 아키텍처

```
텔레그램 Webhook → Django view
  ↓
명령 파서 → 해당 서비스 호출
  ↓
응답 생성 → 텔레그램 API로 전송
```

- synco의 python-telegram-bot 패턴 재사용
- 음성 메시지 → Whisper STT → DailyVoiceLog 생성

### 8.3 사용자 바인딩

기존 synco 패턴 참고:
- 웹에서 텔레그램 연결 코드 생성
- 텔레그램에서 코드 입력 → User와 chat_id 바인딩
- 이후 chat_id로 사용자 식별

### 8.4 검증 기준

- [ ] 텔레그램 봇 웹훅 동작
- [ ] /status 명령 → 기업 현황 응답
- [ ] 음성 메시지 → STT → DailyVoiceLog 저장
- [ ] 사용자 바인딩 플로우

---

## Phase 9: 세액공제 증빙 패키지 + 내보내기

### 목표

"법인세 신고 시 필요한 모든 증빙을 ZIP으로 일괄 내보낸다."

### 9.1 증빙 패키지 구성

```
{company_name}_증빙패키지_{year}/
├── 01_연구소인정서/
│   └── 인정서_사본.pdf
├── 02_연구개발계획서/
│   └── {과제명}_계획서.pdf
├── 03_연구노트/
│   ├── {과제명}/
│   │   ├── 01월_연구노트.pdf
│   │   ├── 02월_연구노트.pdf
│   │   └── ...
├── 04_완료보고서/
│   └── {과제명}_완료보고서.pdf
├── 05_연구과제총괄표/
│   └── 총괄표_{year}.pdf
├── 06_인건비증빙/
│   └── 인건비_배분표.pdf
└── 07_체크리스트/
    └── 증빙_체크리스트.pdf
```

### 9.2 KOITA 연차보고 가이드

rnd.or.kr 온라인 입력용 데이터를 정리한 가이드 문서:
- R&D 투자액 (항목별)
- 인력 현황
- 과제 수행 실적
- 성과 (특허/논문/신제품)

### 9.3 뷰/URL

```
/compliance/export/?company=<id>&year=<year>  → ZIP 생성 + 다운로드
/compliance/koita-guide/?company=<id>         → KOITA 제출 가이드
/compliance/checklist/?company=<id>           → 증빙 체크리스트
```

### 9.4 검증 기준

- [ ] ZIP 파일 생성 (올바른 디렉터리 구조)
- [ ] 모든 PDF가 ZIP에 포함
- [ ] KOITA 가이드 문서 생성
- [ ] 증빙 체크리스트 생성 (미비 항목 표시)

---

## Phase 간 의존성 그래프

```
Phase 0 (완료)
  │
  ├──→ Phase 1 (과제 + 연구노트)
  │      │
  │      ├──→ Phase 2 (주제 발굴 + 로드맵)
  │      │
  │      ├──→ Phase 3 (PDF + 증빙 체인)
  │      │      │
  │      │      └──→ Phase 4 (보고서 + 비용)
  │      │             │
  │      │             └──→ Phase 9 (증빙 패키지)
  │      │
  │      ├──→ Phase 5 (대시보드)
  │      │      │
  │      │      └──→ Phase 7 (캘린더 + 알림)
  │      │             │
  │      │             └──→ Phase 8 (텔레그램 보이스)
  │      │
  │      └──→ Phase 6 (Voice Layer)
  │             │
  │             └──→ Phase 8 (텔레그램 보이스)
```

---

## 공통 사항

### 테스트 전략

- 각 Phase마다 pytest 테스트 작성
- 모델 테스트: 생성, 관계, 상태 전환
- 뷰 테스트: 권한 확인, HTMX 응답
- AI 서비스 테스트: mock LLM 응답으로 파이프라인 검증

### AI 프롬프트 관리

- 프롬프트는 `research/prompts/` 디렉터리에 텍스트 파일로 관리
- 업종별 프롬프트: `note_sw_it.txt`, `note_manufacturing.txt`, `note_bio.txt`, `note_service.txt`
- 프롬프트 버전 관리 (git)

### 네비게이션 업데이트

Phase마다 `nav_sidebar.html` 업데이트:
- Phase 1: 과제, 연구노트
- Phase 2: 연구주제
- Phase 5: 대시보드 역할 분기
- Phase 7: 컴플라이언스

### 마이그레이션 규칙

- Phase별로 migration 생성
- 파괴적 변경 시 2단계 분리 (새 컬럼 추가 → 이전 컬럼 제거)
- Phase 간 모델 수정 시 backward-compatible하게
