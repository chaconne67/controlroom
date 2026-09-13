# RNDLOG 관리자 고객·연구소 관리 기획

- 작성 기준일: 2026-09-05
- 상태: 화면 시안과 1차 구현 범위를 결정하는 기획 정본
- 대상: RNDLOG 내부 관리자
- 원칙: 확인된 고객 자료만 사용하며, 확인되지 않은 값은 `미확인` 또는 `미지정`으로 남긴다.

## 1. 결론

RNDLOG의 관리 대상은 보고서 파일이 아니다. 고객 요청을 받고 자료를 모아 연구과제를 운영하고,
단계별 문서를 생성·검토·전달하며 연구소 유지와 세무 일정을 계속 관리하는 **고객사별 관리 건**이다.

관리 화면은 다음 질문에 바로 답해야 한다.

1. 이 회사를 누가 맡고 있는가?
2. 지금 어느 단계이며 무엇 때문에 멈췄는가?
3. 누구에게 어떤 자료를 받아야 하는가?
4. 다음 업무와 기한은 무엇인가?
5. 어떤 문서가 어느 근거로 생성되었고 지금 어느 버전인가?
6. 누구에게 어떤 버전을 전달했는가?
7. 연구소·연구원·과제·세무 상태가 언제 어떻게 바뀌었는가?

## 2. 조사 근거와 적용 우선순위

### 2.1 정본 우선순위

1. 현재 고객사 작업공간 `companies/<정식 회사명>/`
2. 각 회사 `README.md`와 실제 파일 존재 여부
3. 현재 `rndlog` 보고서 작성 스킬과 RNDLOG 운영 지침
4. `resources/references/`, `resources/samples/`의 업무 조사자료와 문서 종류
5. 2026년 기업부설연구소 공식 업무편람과 국세청 안내
6. 과거 설계 문서는 현재 자료와 충돌하지 않는 업무 개념만 참고

샘플 회사와 과거 POC 수치는 화면 데이터로 사용하지 않는다. 과거 HTML·PDF 중심 설계보다 현재의
중앙 작업공간·DOCX 경로를 우선한다.

### 2.2 실제 고객사 기준선

| 고객사 | 연구조직 | 실제 자료 상태 | 실제 산출 상태 | 지금 필요한 다음 행동 | 내부 관리자 |
|---|---|---|---|---|---|
| 주식회사 나즈 | 기업부설연구소 | 회사·인정·특허·연구자료 있음 | 문서 파일 7종 존재, 모두 초안·검토 미확정 | 연구원 자격·실제 급여·투입률·실측값 확인 | 미지정 |
| 주식회사 헬로우버디 | 연구개발전담부서 | 회사·인정·연구개요 자료 있음 | 작업본 12종, 최종본 없음 | 시나리오 수치를 실측값으로 교체하고 검토 | 미지정 |
| 주식회사 세움텍 | 기업부설연구소 | 원본 6건과 연구주제 조사 있음 | 산출물 없음 | 연구원·활동·급여 자료 요청 | 미지정 |
| 주식회사 지렙스 | 자료 안에 연구소 관련 기록 있음 | 회수·검증한 입력 ZIP 1건 | 확인된 최종 산출물 없음 | 입력자료 분석 여부 결정 | 미지정 |
| 주식회사 아성 | 과거 기록만 있음 | 현재 파일 없음 | 현재 검증 가능한 산출물 없음 | 원본과 과거 전달본 재확보 | 미지정 |
| 주식회사 힛더락 | 미확인 | 사업자등록증과 수신메모만 있음 | 산출물 없음 | 인정서·연구원·과제·활동자료 요청 | 미지정 |

폴더에 파일이 있다는 사실과 문서가 검토·승인·전달되었다는 사실은 구분한다.

## 3. 업무 범위

### 3.1 고객 등록과 담당 배정

- 정식 법인명과 고객사 작업공간을 연결한다.
- 관리 시작일·관리연도·서비스 상태를 기록한다.
- 주담당 관리자를 반드시 한 명 지정한다.
- 필요하면 내부 검토자를 별도로 지정한다.
- 담당자 변경 시 기존 담당 기간과 처리 이력을 보존한다.

### 3.2 회사와 관계자 관리

- 대표자와 연락 담당자를 구분한다.
- 회계·세무, 인사·노무, 자료 전달 담당자를 별도 역할로 둔다.
- 한 사람이 여러 역할을 맡을 수 있다.
- 역할에는 시작일·종료일·확인 근거를 남긴다.

### 3.3 연구조직과 연구인력 관리

- 기업부설연구소와 연구개발전담부서를 구분한다.
- 인정번호·인정일·조직명·소재지·연구분야를 관리한다.
- 연구소장·연구전담요원·연구보조원·연구관리직원을 구분한다.
- 학위·전공·재직·자격 증빙의 확인 상태를 관리한다.
- 연구원 변경, 주소·공간·기자재 변경을 업무와 일정으로 연결한다.

### 3.4 연구과제와 정기 연구업무 관리

- 연구주제 후보와 선정 근거를 남긴다.
- 과제별 기간·목표·참여 연구원·투입률을 관리한다.
- 과제 단계에 맞춰 필요한 자료와 산출물 종류를 결정한다.
- 월간·주간 연구노트 등 반복 업무는 회사별로 주기를 설정한다.
- 실제 연구활동 원자료가 없으면 문서 생성을 막고 이유를 표시한다.

### 3.5 문서 요청·생성·검토·전달

- 필요한 서류와 제공자를 연결한다.
- 요청일·요청자·기한·수신일·보완 여부를 기록한다.
- 문서 생성에는 사용한 원천자료와 스킬 실행 이력을 연결한다.
- 초안, 검토 중, 승인, 전달, 폐기·대체 상태를 구분한다.
- 전달할 때 수신자·채널·전달 시각·정확한 파일 버전을 기록한다.

### 3.6 세무·신고·일반 업무

- 세무 업무는 연구과제·연구원·연구비 자료와 연결한다.
- 활동조사와 변경신고는 법정·공식 기한을 가진 업무로 관리한다.
- 일반 업무도 같은 업무·문서 구조를 쓰되 업무 분류만 다르게 한다.

## 4. 관계자와 책임

| 구분 | 역할 | 주된 책임 | 시스템 권한 |
|---|---|---|---|
| 내부 주담당 관리자 | `primary_manager` | 고객사 전체 진행, 자료 요청, 일정, 다음 행동 결정 | 고객 관리 건 편집 |
| 내부 검토자 | `reviewer` | 생성 문서의 근거·내용·완성 상태 확인 | 검토·승인 |
| 대표자 | `representative` | 회사 정보 확인, 주요 의사결정, 최종 확인 | 추후 고객 화면 범위 |
| 연구소장·전담부서장 | `research_director` | 연구조직·과제·연구원·활동 확인 | 추후 고객 화면 범위 |
| 연구원 | `researcher` | 실제 연구활동과 원자료 제공 | 추후 본인 자료 범위 |
| 고객 실무 담당자 | `general_contact` | 연락과 자료 전달 | 추후 요청 응답 범위 |
| 회계·세무 담당자 | `accounting_contact` | 급여·비용·세무자료 제공 | 추후 세무자료 범위 |
| 인사·노무 담당자 | `hr_contact` | 재직·학위·보험·인사자료 제공 | 추후 인사자료 범위 |
| 외부 세무사 등 | `external_advisor` | 신고 검토·제출 지원 | 추후 위임 범위 |

한 사람에게 역할을 직접 고정하지 않고 `person`과 역할 연결을 분리한다. 대표자가 연구소장과 연구원을
겸하는 실제 사례를 그대로 표현하기 위해서다.

## 5. 문서 체계

### 5.1 회사·일반 관리 자료

- 사업자등록증
- 법인등기·회사 기본자료
- 회사소개서
- 조직도
- 특허·인증·확인서
- 계약·동의·연락 창구 자료
- 결산·재무자료
- 자료 요청·수신 메모와 대화 근거

### 5.2 연구소 유지 자료

- 연구소·전담부서 인정서
- 연구개발활동 개요서
- 연구개발인력 현황
- 연구기자재 현황
- 연구공간 도면·내부사진·현판사진
- 학위·경력·재직·4대보험·인사발령 자료
- 변경신고 근거와 처리 결과

### 5.3 연구과제 자료와 산출물

- 연구주제 조사와 선정 기록
- 연구과제총괄표
- 연구개발계획서
- 연구노트·연구일지
- 연구원별 업무일지
- 회의록 또는 근거가 있는 자가점검 기록
- 실험·설계·계측·분석 원자료
- 완료보고서와 연구개발보고서

### 5.4 세무 자료와 산출물

- 급여대장·원천징수 관련 자료
- 연구원별 R&D 투입률 산정 근거
- 인건비배분표
- 연구개발비명세서
- 연구개발계획서·보고서·연구노트 등 공제 증빙
- 세액공제 사전심사·신고 관련 자료

### 5.5 정기 신고 자료

- 연구개발활동조사표
- 연구소 인정요건 점검 자료
- 대표·주소·연구분야·연구소장·연구원·기자재·공간 변경 자료

## 6. 단계별 문서 요구 규칙

| 단계 | 선행 조건 | 필수 업무·문서 | 완료 판단 |
|---|---|---|---|
| 접수 | 정식 회사명 확인 | 회사 등록, 담당 배정, 원본 적재, 수신메모 | 작업공간과 담당자 존재 |
| 연구소 확인 | 인정자료 수신 | 연구조직·연구인력·공간·기자재 확인 | 핵심 항목 검증 또는 부족 사유 기록 |
| 과제 준비 | 연구분야·인력 확인 | 연구주제 조사, 과제 선정, 계획·일정 | 고객 확인된 과제와 계획 존재 |
| 연구 진행 | 실제 활동 원자료 수신 | 정기 연구노트·업무일지·회의기록 | 해당 기간 활동 근거와 검토본 존재 |
| 기간 마감 | 급여·투입·비용 자료 수신 | 인건비배분·비용명세·증빙 묶음 | 실제 수치 검증과 승인 |
| 과제 종료 | 종료 결과 수신 | 완료보고서·총괄 정리 | 승인된 최종 버전 존재 |
| 정기 신고 | 신고 대상·기한 확인 | 활동조사·세무·변경신고 | 제출 기록과 결과 존재 |

필수 선행 조건이 없으면 다음 단계로 넘어가지 않고 `자료 대기` 상태와 부족한 항목을 보여준다.

## 7. 데이터 모델

모든 업무 테이블은 공식 DB `ceo_loan`의 `rndlog` 스키마에 둔다. 기존 TM·영업 테이블과 섞지 않는다.

### 7.1 고객·조직 정본

#### `rndlog.client_company`

- `id`
- `legal_name`
- `business_number_digits`
- `workspace_key`
- `directory_company_id` — 공통 회사 정본과 연결될 때만 사용, nullable
- `status` — active, paused, closed
- `verified_at`, `verified_by`
- `created_at`, `updated_at`

#### `rndlog.person`

- `id`
- `name`
- `phone`, `email`
- `verification_status`
- `created_at`, `updated_at`

#### `rndlog.company_role`

- `company_id`, `person_id`
- `role_type`
- `is_primary_contact`
- `started_on`, `ended_on`
- `evidence_asset_id`

#### `rndlog.research_unit`

- `company_id`
- `unit_type` — institute, dedicated_department
- `name`, `recognition_number`
- `recognized_on`
- `research_field`, `address`
- `status`, `status_checked_on`
- `evidence_asset_id`

#### `rndlog.research_membership`

- `research_unit_id`, `person_id`
- `role_type` — director, dedicated_researcher, assistant, manager
- `started_on`, `ended_on`
- `qualification_status`
- `evidence_asset_id`

### 7.2 관리·담당·일정

#### `rndlog.management_case`

- `company_id`
- `management_year`
- `started_on`, `ended_on`
- `service_status` — intake, active, waiting, closing, closed
- `next_action_summary` — 표시용 캐시, 실제 값은 열린 업무에서 계산

#### `rndlog.admin_assignment`

- `management_case_id`
- `user_id` — 기존 `accounts.User`
- `assignment_role` — primary_manager, reviewer
- `started_at`, `ended_at`
- `assigned_by`

규칙: 한 관리 건에는 활성 상태의 `primary_manager`가 정확히 한 명이어야 한다.

#### `rndlog.schedule_rule`

- `management_case_id`, `project_id`
- `work_category`
- `cadence` — weekly, monthly, quarterly, yearly, one_time
- `rule_value`
- `due_basis` — legal, contract, customer, internal
- `next_due_on`
- `assigned_user_id`
- `is_active`

#### `rndlog.work_item`

- `management_case_id`, `project_id`
- `parent_work_item_id`
- `schedule_rule_id`
- `category` — intake, research, document, tax, compliance, general, delivery
- `title`
- `status` — todo, waiting_customer, ready, in_progress, review, done, canceled
- `priority`, `due_on`, `due_basis`
- `assigned_user_id`
- `blocked_reason`
- `completed_at`

### 7.3 연구과제

#### `rndlog.research_project`

- `management_case_id`, `research_unit_id`
- `project_code`, `title`, `research_field`
- `started_on`, `ended_on`
- `status` — proposed, planned, active, paused, completed
- `selection_basis_asset_id`

#### `rndlog.project_participation`

- `project_id`, `person_id`
- `project_role`
- `started_on`, `ended_on`
- `allocation_rate`
- `allocation_basis_asset_id`

### 7.4 자료·문서·산출물

#### `rndlog.document_type`

- `code`, `name`
- `business_category`
- `direction` — incoming, generated, submitted
- `applicable_stage`
- `default_provider_role`
- `requires_review`

#### `rndlog.document_requirement`

- `management_case_id`, `project_id`, `work_item_id`
- `document_type_id`
- `provider_role`, `provider_person_id`
- `status` — missing, requested, received, needs_revision, accepted, not_applicable
- `requested_at`, `due_on`, `received_at`
- `satisfied_by_asset_id`
- `note`

#### `rndlog.file_asset`

- `company_id`
- `storage_area` — source_original, source_intake, research, draft, final
- `relative_path`
- `original_name`, `mime_type`, `byte_size`, `sha256`
- `origin` — customer, internal_research, generated, recovered
- `received_at`, `created_by`
- `verification_status`
- `is_immutable`

#### `rndlog.document`

- `management_case_id`, `project_id`
- `document_type_id`
- `period_start`, `period_end`
- `status` — draft, reviewing, approved, delivered, superseded, void
- `current_version_id`

#### `rndlog.document_version`

- `document_id`, `file_asset_id`
- `version_number`
- `source_manifest` — 생성에 사용한 원천자료 식별자
- `generated_at`, `generated_by`
- `reviewed_at`, `reviewed_by`
- `review_result`
- `created_at`

#### `rndlog.delivery`

- `document_version_id`
- `recipient_person_id`, `recipient_text`
- `channel` — download, email, kakao, sms_link, external_submission
- `status` — prepared, sent, failed, acknowledged
- `sent_at`, `sent_by`
- `evidence_asset_id`

### 7.5 관리 이력

#### `rndlog.activity_event`

- `management_case_id`
- `actor_user_id`
- `event_type`
- `entity_type`, `entity_id`
- `summary`
- `occurred_at`

현재 상태를 활동 로그만 재생해서 만들지 않는다. 핵심 테이블에 현재 상태를 보관하고,
`activity_event`는 누가 언제 무엇을 바꿨는지 확인하는 감사 기록으로 사용한다.

## 8. 핵심 상태 규칙

### 8.1 관리 건

- `intake`: 고객 등록과 최초 자료 수집
- `active`: 진행할 수 있는 업무가 있음
- `waiting`: 고객 또는 외부 자료를 기다림
- `closing`: 검토·승인·전달 단계
- `closed`: 해당 관리기간 종료

### 8.2 자료 요구

`missing → requested → received → accepted`

- 자료가 불충분하면 `needs_revision`으로 되돌린다.
- 적용 대상이 아니면 `not_applicable`로 남기고 이유를 기록한다.

### 8.3 문서

`draft → reviewing → approved → delivered`

- 수정본이 나오면 새 버전을 만든다.
- 이전 버전은 `superseded`로 보존한다.
- 파일 위치만으로 상태를 추정하지 않는다.

## 9. 저장 구조

### 9.1 파일 정본

고객 파일은 중앙 작업공간에만 둔다.

```text
companies/<정식 회사명>/
├── sources/
│   ├── original/     고객에게 받은 원본
│   └── intake/       수신메모·링크·대화 근거
├── research/         회사별 조사자료
└── deliverables/
    ├── drafts/       작업본
    └── final/        검토 완료 산출물
```

연구·세무·일반 업무 구분은 폴더가 아니라 DB의 `business_category`와 `document_type`으로 관리한다.

### 9.2 DB 저장 내용

- 파일 자체가 아닌 상대경로·해시·크기·형식·버전·상태 저장
- 관계자·담당 관리자·업무·일정·자료 요구·검토·전달·이력 저장
- 고객 개인정보는 화면에서 필요한 범위만 노출

### 9.3 운영 웹서비스 연결

운영 서버에 고객 파일을 복제하지 않는다. 업로드·다운로드 단계에서는 중앙 작업공간만 접근하는
통제된 저장소 연결 계층이 필요하다.

- 회사 작업공간 밖의 경로 접근 차단
- 업로드 후 해시와 파일 크기 기록
- 원본 파일 덮어쓰기 금지
- 다운로드·생성·전달 기록 남김
- 운영 DB에는 파일 바이트를 넣지 않음

첫 화면 시안은 이 연결이 이미 구현된 것처럼 가장하지 않는다. 실제 연결 전에는 파일 작업 버튼을
`연결 전` 상태로 설명한다.

## 10. 권한

| 기능 | 관리자 | TM | 영업 | 고객 관계자 |
|---|---:|---:|---:|---:|
| 연구소 관리 메뉴 보기 | 허용 | 차단 | 차단 | 차단 |
| 고객사 목록·상세 보기 | 허용 | 차단 | 차단 | 차단 |
| 담당 관리자 지정 | 허용 | 차단 | 차단 | 차단 |
| 상태·일정·자료 요구 편집 | 허용 | 차단 | 차단 | 차단 |
| 문서 검토·승인 | 관리자 중 권한 보유자 | 차단 | 차단 | 추후 별도 설계 |
| 파일 다운로드·전달 | 관리자 중 권한 보유자 | 차단 | 차단 | 추후 별도 설계 |

사이드바에서 링크를 감추는 것과 별개로 직접 URL 접근도 관리자 역할로 차단한다.

## 11. 화면 구조

### 11.1 기존 로그인과 메뉴

- 관리자 로그인 후 첫 화면은 현재의 `문자 발송`을 유지한다.
- `문자 발송` 바로 아래에 관리자 전용 `연구소 관리`를 배치한다.
- TM·영업·승인대기 계정에는 메뉴를 표시하지 않는다.

### 11.2 첫 화면: 관리 업무함

첫 화면의 목표는 관리자가 10초 안에 **어느 회사를 왜 먼저 처리해야 하는지** 판단하는 것이다.

#### 상단 집계

- 담당자 미지정
- 자료 대기
- 검토 필요
- 기한 확인 필요

#### 고객사 목록

- 고객사
- 연구조직
- 주담당 관리자
- 현재 단계
- 부족한 자료 또는 위험
- 다음 업무
- 기준일·기한
- 최근 산출 상태

#### 고객사 상세 패널

- 기본 정보와 연구조직
- 고객 관계자와 내부 담당자
- 현재 연구과제
- 부족한 자료
- 다음 업무 3건
- 최근 문서와 버전 상태
- 최근 관리 이력

### 11.3 후속 화면

1. 관계자·연구원 관리
2. 과제·일정 관리
3. 자료 요청·수신 관리
4. 문서 생성·검토·버전 관리
5. 전달·제출 이력
6. 세무·활동조사·변경신고 일정

### 11.4 화면 재현 기준

- Seed key: `rndlog-admin-workbench-v1-20260905`
- Seed 근거: 기존 RNDLOG 로그인 화면의 190px 사이드바, 종이색 바탕, 남색 본문, 초록 브랜드 강조,
  파란 업무 버튼을 유지하고 다회사 운영에 필요한 master-detail 구조만 추가한다.
- 첫 화면 기억점: 상태 큐에서 실제 고객사를 고르면 막힌 이유·다음 업무·주담당자를 같은 화면에서 본다.
- 모바일 기억점: 메뉴에서 `문자 발송 → 연구소 관리` 순서를 확인하고 고객사 목록과 상세를 왕복한다.

## 12. 최소 구현 순서

### 1차: 실제 고객사 관리대장

- 관리자 전용 메뉴와 URL
- 실제 고객사 6곳 등록
- 주담당 관리자 지정·변경 이력
- 실제 자료·산출물 현황 표시
- 부족한 자료, 막힌 이유, 다음 업무 표시
- 회사 상세 패널

### 2차: 자료·문서 메타데이터

- 중앙 파일 목록 동기화
- 문서 종류·버전·상태 관리
- 자료 요청과 수신 상태
- 문서 검토·승인 상태

### 3차: 중앙 저장소 연결

- 권한이 있는 업로드·다운로드
- 원본 불변성·해시 검증
- 새 버전 생성과 이력

### 4차: 보고서 생성 업무 연결

- `rndlog` 스킬에 전달할 작업 요청 생성
- 사용한 원천자료와 생성 결과 연결
- 초안 생성 후 사람 검토·승인
- 자료 부족 시 생성 차단

### 5차: 지속 관리

- 회사별 반복 일정
- 세무·활동조사·변경신고 일정
- 전달·제출 이력
- 기한·자료 대기 알림

## 13. 1차 화면 시안 합격 조건

- 실제 고객사 6곳만 사용한다.
- 실제 존재하지 않는 회사·담당자·발송 기록·일정을 만들지 않는다.
- 현재 관리자 계정은 선택 후보로만 표시하고 기본 배정은 `미지정`이다.
- 각 회사의 막힌 이유와 다음 행동이 실제 README와 일치한다.
- 나즈와 헬로우버디 문서는 승인 완료로 오인되지 않게 표시한다.
- 지렙스 입력자료를 RNDLOG 산출물로 표시하지 않는다.
- 아성의 과거 기록을 현재 완료 상태로 표시하지 않는다.
- 관리자 메뉴가 문자 발송 바로 아래에 있고 다른 역할에는 보이지 않음을 설명한다.
- 운영 업로드·다운로드·발송이 아직 연결되지 않았음을 명확히 표시한다.
- 390px 모바일과 데스크톱에서 핵심 업무를 확인할 수 있다.

## 14. 공식 참고

- 기업부설연구소등의 연구개발 지원에 관한 법률·시행규칙, 2026-02-01 시행
- 2026 기업부설연구소 및 연구개발전담부서 신고 업무편람
- 기업부설연구소/전담부서 신고관리시스템 연구개발활동조사 안내
- 국세청 연구·인력개발비 세액공제 안내
