# RNDlog CEO Loan Clone Design

## 1. 목표

RNDlog의 공개 랜딩페이지와 KOITA 자가진단, CRETOP 전체 경로를 유지하면서 로그인 이후 시스템을 현재 운영 중인 CEO Loan 코드 기준으로 교체한다.

- 복제 기준: `chaconne@49.247.205.170:~/ceoloan/repo`
- 기준 커밋: `0e6c3a50443488a68c006dc9e045bd97a67430d8`
- 공개 브랜드: RNDlog
- 로그인 이후 브랜드: RNDlog 로고와 명칭
- 운영 도메인: `rndnote.co.kr`

## 2. 유지 범위

### 2.1 공개 기능

- `/`: 기존 RNDlog 랜딩페이지
- `/koita-checkup/`: 기존 KOITA 자가진단
- 랜딩페이지 상담 신청
- 자가진단 결과 상담 신청

### 2.2 CRETOP 최종 경로

CRETOP 관련 코드는 삭제하거나 우회하지 않는다.

- `cretop/`: 계약·참조자료
- `scripts/cretop_agent.py`: CRETOP 화면 자동화
- `scripts/cretop_detail_collection.py`: 상세 수집 실행 경로
- `scripts/cretop_report_pipeline.py`: 구조화·재무·보고서 적재
- `scripts/test_cretop_*.py`: 수집 경로 테스트
- `docs/cretop/`: 절차·스키마·품질 계약
- `ceo_loan.cretop`: 원천 34개 테이블
- `ceo_loan.public.leads`: 대표이사 승격 원천
- `funding.services.cretop_data`: 기업 사실 조회
- `funding_sync_ceos`: 대표이사·회사 동기화
- 자격 판정, 대출 산식, 경영진단 엑셀, LLM 검토의견
- DB 터널과 예약 실행 경로

CRETOP 원천은 Django 마이그레이션의 생성·변경·삭제 대상이 아니다.

## 3. 제거 범위

- 마케팅 대시보드와 운영 URL
- 이메일 캠페인·템플릿·발송·추적 화면
- Google Sheet 리드 가져오기 화면
- 기존 이메일·비밀번호 서비스 로그인 화면
- 사용하지 않는 회사 업무 화면
- `FundingRouter` 기반의 계정 DB·기업자금 DB 분리 구조
- 기존 일반 사용자 3명
- 기존 배분·통화·녹음·전달·문자·캠페인 데이터

마케팅 데이터 테이블은 운영 연결에서 제거한다. 기존 데이터는 전환 대상이 아니며 새 시스템으로 가져오지 않는다.

## 4. 애플리케이션 구조

### 4.1 유지 앱

- `accounts`: Google 인증, 승인, 역할, 슈퍼관리자 비상 접근, 공개 상담 신청
- `checkup`: KOITA 자가진단과 상담 신청
- `funding`: CEO Loan의 관리자·TM·영업·문자·경영진단
- `common`: 권한, 공용 모델, 이름 정리 등 공통 계약

### 4.2 제거 앱

- `marketing`: 공개 상담 저장에 필요한 최소 모델을 `accounts`로 옮긴 뒤 제거
- `companies`: 랜딩·자가진단·기업자금 최종 경로에서 사용하지 않으므로 제거

### 4.3 URL

- `/`: `landing.html`
- `/light/`: 기존 보조 랜딩
- `/koita-checkup/`: 자가진단
- `/accounts/login/`: RNDlog Google 로그인
- `/accounts/after-login/`: 역할별 착지
- `/accounts/pending/`: 승인대기
- `/accounts/approvals/`: 슈퍼관리자 승인
- `/admin/`: 슈퍼관리자 비상 로그인
- `/funding/`: TM 상담
- `/funding/admin/`: 관리자 기업 목록·발송함
- `/funding/handoffs/`: 영업 전달함

CEO Loan의 루트 로그인 URL은 적용하지 않는다. RNDlog에서는 루트를 공개 랜딩이 소유하고 로그인은 `/accounts/login/`이 소유한다.

## 5. 인증과 사용자

- `django-allauth` Google 공급자만 일반 서비스 로그인에 사용한다.
- 원격 CEO Loan의 Google OAuth 클라이언트 ID와 비밀키를 재사용한다.
- Google Cloud OAuth 클라이언트에 `https://rndnote.co.kr/accounts/google/login/callback/`을 등록한다.
- 신규 계정은 `pending`으로 생성한다.
- 슈퍼관리자만 사용자 역할을 승인·변경·거절한다.
- 역할은 `pending`, `admin`, `tm`, `sales` 네 가지다.
- 로그인 착지는 `accounts.views.after_login` 한 곳이 결정한다.
- 기존 슈퍼관리자 2명은 사용자명과 비밀번호 해시를 보존해 `/admin/` 비상 계정으로 이전한다.
- 기존 일반 사용자 3명은 이전하지 않는다.
- 일반 사용자는 전환 후 Google 로그인으로 다시 가입한다.

Google OAuth 장애가 발생해도 `/admin/` 비상 로그인은 유지한다. 일반 서비스에 비밀번호 로그인 폼은 제공하지 않는다.

## 6. 공개 상담 저장

`marketing` 앱을 제거하기 전에 공개 상담 신청이 의존하는 `Lead`와 `Activity`를 끊는다.

- `accounts.ConsultationRequest`가 랜딩과 자가진단 상담 신청을 함께 저장한다.
- 공통 필드: 회사명, 담당자명, 전화번호, 이메일, 접수 경로, 접수 내용, 생성 시각
- 랜딩 추가 필드: 고민, 희망 연락 시간
- 자가진단 추가 필드: 점수, 등급, 업종, 상담 담당자
- 이메일 알림은 현재 공개 화면의 성공·실패 계약을 유지한다.
- 기존 상담 데이터는 이전하지 않는다.

## 7. 데이터베이스 전환

### 7.1 최종 DB

로그인 이후 시스템과 공개 상담 저장은 로컬 PostgreSQL의 `ceo_loan` DB 하나를 사용한다.

- Django `default` 연결은 `ceo_loan`을 가리킨다.
- `FundingRouter`를 제거한다.
- 교차 DB 문자열 연결을 최신 CEO Loan의 실제 FK로 교체한다.
- `cretop` 스키마와 `public.leads`는 같은 DB에 그대로 둔다.

### 7.2 초기화 대상

- `funding_agent`
- `funding_assignment`
- `funding_callaudio`
- `funding_callrecord`
- `funding_ceo`
- `funding_ceocompany`
- `funding_handoff`
- 새 문자·캠페인 테이블이 이미 존재한다면 해당 데이터
- 슈퍼관리자를 제외한 인증 사용자와 관련 세션

### 7.3 보존 대상

- `cretop` 스키마 전체
- `public.leads`
- 기존 슈퍼관리자 2명의 인증에 필요한 값

### 7.4 마이그레이션 상태 복구

현재 `ceo_loan`에는 인증 마이그레이션 기록이 있지만 실제 인증 테이블이 없다. 다음 순서로 복구한다.

1. 실제 테이블과 `django_migrations`의 불일치를 검증한다.
2. `funding`을 제외한 잘못 기록된 인증·관리자·세션 마이그레이션 행만 제거한다.
3. CEO Loan의 인증 초기 마이그레이션으로 실제 테이블을 만든다.
4. 슈퍼관리자 2명을 복사한다.
5. 기존 기업자금 업무 테이블을 비운다.
6. CEO Loan `funding` 마이그레이션 `0009`부터 `0017`까지 적용한다.
7. `funding_sync_ceos`로 대표이사·회사·재무 스냅샷을 재생성한다.

마이그레이션 `0009~0017`은 문자 이력, 예약 캠페인, 도달 결과, 수신거부, 담당자·진행 상태 등 최신 기능의 스키마다. 기존 업무 데이터를 보존하기 위한 단계가 아니다.

## 8. 기업자금 기능

운영 CEO Loan의 `accounts`, `funding`, `common`, 공통 템플릿과 정적 자산을 기준으로 가져온다.

- 관리자 기업 목록과 재무 필터
- 관리자 발송함과 진행 현황
- TM 상담 목록·회사 카드·통화 기록
- 녹음 업로드·전사·요약
- 관리자 및 TM의 영업 전달
- 영업 전달함과 상태 관리
- 경영진단 엑셀과 LLM 문구
- 다른 사용자로 보기
- 사용자 승인과 역할 관리

RNDlog의 CRETOP 조회와 보고서 계약이 운영 CEO Loan보다 새롭거나 상세하면 RNDlog 구현을 유지한다. 코드가 다를 때는 CRETOP 정확성과 단일 실행 경로를 우선한다.

## 9. 문자와 MMS

### 9.1 설정

- `SOLAPI_API_KEY`: `.env`
- `SOLAPI_API_SECRET`: `.env`
- `SOLAPI_SENDER`: `.env`, 발신번호와 RNDlog 회사 연락처의 단일 정본
- `SMS_OPT_OUT_NUMBER`: `.env`, SOLAPI 공용번호 `080-500-4233`

별도 회사 전화번호 설정은 만들지 않는다. 문자 본문, MMS 카드, 회신번호는 모두 `SOLAPI_SENDER`를 읽는다.

### 9.2 발송 경로

- 관리자와 TM이 화면에서 대상을 선택한다.
- 즉시 발송 또는 고정 대상 예약 캠페인을 만든다.
- 수신거부 명단 확인 실패 시 전체 발송을 막는다.
- 일반 사용자의 야간 발송을 막는다.
- 슈퍼관리자의 명시적 즉시 발송은 CEO Loan과 같은 예외를 적용한다.
- 접수 결과와 번호별 실패를 `SmsSend`에 기록한다.
- 도달 동기화가 수신 완료·실패 사유를 갱신한다.
- 실제 문자 검증은 주인님이 지정한 테스트 번호에만 수행한다.

## 10. 예약 실행

현재 RNDlog 호스트의 cron을 다음 단일 경로로 정리한다.

- 매시 5분: `funding_sync_ceos`
- 매시 0분·30분: `funding_send_sms_campaigns`
- 매시 25분·55분: `funding_sync_sms_delivery`

각 명령은 RNDlog 저장소와 최종 설정을 사용한다. 이전 DB나 원격 CEO Loan 저장소를 호출하지 않는다.

## 11. 배포 구조

RNDlog의 Docker Swarm과 `deploy.sh`를 유지한다. CEO Loan의 Docker Compose 운영 방식으로 바꾸지 않는다.

- 앱 이미지에 `django-allauth`, Playwright, Pillow를 포함한다.
- Chromium과 한글 글꼴을 앱 이미지에 설치한다.
- MMS HTML 카드를 JPG로 렌더한다.
- 정적 파일은 기존 RNDlog nginx 이미지 경로로 전달한다.
- 배포 백업·마이그레이션은 최종 `ceo_loan` DB 한 곳을 기준으로 수정한다.
- 앱과 nginx 서비스가 새 이미지 태그로 각각 `1/1`이 된 뒤 성공으로 인정한다.

## 12. 오류 처리

- Google 설정 부족: 로그인 화면에서 구성 오류를 노출하고 계정을 임의 생성하지 않는다.
- 승인대기: 업무 URL 접근 대신 승인대기 화면으로 이동한다.
- 역할 불일치: `PermissionDenied`로 차단한다.
- SOLAPI 설정 부족: 화면과 서버 발송을 같은 관문으로 차단한다.
- 수신거부 조회 실패: 한 건도 보내지 않는다.
- MMS 렌더 실패: 해당 발송을 실패로 기록하고 글자 문자로 우회하지 않는다.
- CRETOP 사실 부족: 값을 만들지 않고 빈 값 또는 판정 불가로 표시한다.
- 경영진단 계약 위반: 파일을 만들지 않고 기존 `NarrativeContractError` 경로를 유지한다.
- 데이터 전환 검증 실패: 배포하지 않고 운영 서비스를 현재 이미지로 유지한다.

## 13. 검증 기준

### 13.1 자동 검증

- 마이그레이션 드리프트 없음
- RNDlog 전체 테스트 통과
- CEO Loan에서 가져온 인증·기업자금·문자 테스트 통과
- CRETOP 수집·동기화·보고서 테스트 회귀 없음
- Ruff 검사 통과
- Django deploy check 통과

### 13.2 DB 검증

- `cretop` 34개 테이블 유지
- `public.leads` 건수 유지
- 슈퍼관리자 2명 존재
- 일반 사용자 0명
- 최신 `funding` 마이그레이션 `0017` 적용
- `funding_sync_ceos` 실행 후 대표이사·회사 재생성
- 기존 통화·전달·문자·캠페인 데이터 0건

### 13.3 화면 검증

- 랜딩과 자가진단 공개 접근
- RNDlog Google 로그인 버튼
- 신규 계정 승인대기
- 슈퍼관리자 승인과 역할별 착지
- 관리자·TM·영업 주요 화면
- CRETOP 회사 상세와 경영진단 생성
- MMS 카드의 RNDlog 로고와 `SOLAPI_SENDER`
- 운영 HTTPS `200`

## 14. 완료 조건

- 공개 랜딩·자가진단·CRETOP 전체 기능이 기존과 같거나 더 정확하게 동작한다.
- 로그인 이후 화면과 기능이 기준 CEO Loan 커밋과 일치한다.
- RNDlog 로고와 연락처가 모든 고객 접점에 적용된다.
- Google 가입·승인·역할별 접근이 동작한다.
- 문자 즉시·예약·도달 확인이 같은 최종 경로로 동작한다.
- 운영 서비스가 새 이미지로 정상 배포되고 기존 분리 경로가 남지 않는다.
