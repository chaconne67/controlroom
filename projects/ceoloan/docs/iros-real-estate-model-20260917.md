# IROS 부동산 등기 표본과 DB 저장 모델

작성일: 2026-09-17. 상태: **기존10건 + 추가20개 물건·첨부14개 조사 완료 / 최종 논리 모델 v2.1 / 운영 적용 전 설계 제안**.

추가 검토: 10건은 일반 건물에 집중된 모델 탐색 표본이다. 추가 표본의 필요성·권고 범위·종료 기준은10절, 주인님의 진행 승인과 실제 실행 기록은11절에 기록한다. **4절은 추가 원문·보류 표본을 반영한 최종 모델 v2.1이며,12·13절은 변경 근거와 검증 한계다. 운영 DB 적재·DDL·권한·웹 다운로드는 별도 구현 단계다.**

주인님 요청에 따라 CRETOP 상세정보가 저장된 모기지 대상 회사에서 무작위 후보를 뽑아 실제 IROS 등기를 열람했다. 원본과 분석용 구조화 자료는 별도 마운트 디스크에 보관했다. 운영 DB에는 이번 자료를 적재하지 않았으며, 새 스키마·권한·웹 다운로드 기능은 아직 만들지 않았다.

## 1. 결과와 자료 위치

다음 수치는 최초10개 조사 기록이다. 승인된 추가 조사까지 포함하면 고유 물건30개, PDF34개/232쪽이다. 추가20개 판독 자료와 최종 수량·비용·한계는11~13절에 있다. 추가 조사 자료의 보관 정본은 `/mnt/ceoloan/registry/studies/20260917_expand20_model/`이며 실제 검증 기록은 private validation_report/archive_verification에 보존한다.

- 열람 PDF 10개, 고유번호 10개, 총 41쪽, 선불 열람료 7,000원. 말소사항 포함, 주민등록번호 미공개 조건이다.
- 소유권 취득 관련 기록 28건: 매매 17행, 보존 6행, 증여 3행, 신탁 이전·귀속 2행. 동일 매매목록의 지분 이전 여러 행을 하나의 거래로 연결해야 한다.
- 근저당 설정 기록 43개와 부기·변경·말소 관계를 구조화했다. 열람 시점에 말소되지 않은 근저당 10개, 모두 말소됐거나 을구에 기록이 없는 건물 4개다. **43개는 43개의 실제 대출을 뜻하지 않는다.**
- 전세권·압류·가압류·가처분 등 그 밖의 권리 설정 기록 18개를 별도로 정리했다.
- 이번 본문에서 매매가격, 실제 대출 잔액, 대출 만기를 확보하지 못했다. 이 값들은 NULL과 사유로 남겼다.
- PDF 전체 41쪽을 화면으로 확인하고 PDF 고유번호·페이지 수·주요 소유권 지분·권리 변경·말소선을 대조했다. 공식 텍스트 파서의 표제부 분리 오류 1건을 발견해 표본 판단에서 보완했다.
- 원본 PDF 10개 828,650바이트를 업로드한 후 SHA-256을 원본과 대조했다. 수집기의 입력 데스크톱은 전후 Default였고, 수집용 Chrome의 전경 전환은 관측되지 않았으며 모든 실행 후 소유 프로필 Chrome이 종료됐다. 사용자가 다른 앱으로 옮긴 전경 이벤트는 별도로 기록했다.

| 자료 | 실제 위치 |
|---|---|
| 설계 정본 | 조정실 `~/controlroom/projects/ceoloan/docs/iros-real-estate-model-20260917.md` |
| 표본 구조화 JSON 작업본 | `C:\\iros-agent\\studies\\20260917_sample10_model\\structured_samples.json` |
| 후보·제외·실행·파일 manifest 작업본 | 같은 폴더의 `selection.json`, `manifest.json`, `*_monitor.json`, `*_archive.json` |
| PDF 글자·표 위치·벡터선 자료 | 같은 폴더의 `*_layout.json` |
| 보관 서버·마운트 | `chaconne@49.247.45.243`, `/mnt` = `/dev/vdb1` ext4 별도 약 98GiB 디스크 |
| 원본 PDF 정본 | `/mnt/ceoloan/registry/original/2026/09/<IROS 고유번호>/<SHA-256>.pdf` |
| 구조화·근거 자료 보관 정본 | `/mnt/ceoloan/registry/studies/20260917_sample10_model/` |

원본 및 개인 이름·사업자번호·주소를 포함한 표본 JSON은 Git에 넣지 않는다. 이 설계 문서에는 표본 코드를 사용한다. `/mnt/data`는 기존 MySQL 자료 경로이므로 사용하지 않았다. 디스크에 저장했다는 사실과 웹에서 다운로드할 수 있다는 사실은 별개다. 현재는 서버 파일과 manifest가 보관 결과이며, 웹 링크를 제공할 인증 다운로드 경로는 아래 설계의 구현 대상이다.

### 표본의 구성과 한계

읽기 전용 운영 DB 조회에서 모기지 대상 20,519개 중 CRETOP 상세 저장 기록과 주소값이 있는 회사 3,900개를 확인했다. 회사 주소의 값 존재는 주소의 정확성을 보장하지 않는다.

무작위 seed `087d33ad8e6a4506e24378cf968ea103`로 대상 ID를 해시 정렬해 후보 30개 순서를 고정했다. 앞에서부터 15개를 검토해 10개를 열람했다. C05·C09는 도로명 검색 무결과, C08은 같은 주소에 고유번호 2개, C10은 주소 필드에 '표준산업분류(10차)', C13은 검색 결과에서 정확히 일치하는 건물을 찾지 못해 제외했다. 이 후보들은 결제하지 않았다.

성공 표본은 모두 **건물 등기**다. 전체 회사의 자산 보유나 부채 분포를 추정하는 통계 표본으로 사용하지 않는다. 숙박업 모기지 대상과 주소로 특정 가능한 건물에 치우친 자료다. 토지·집합건물·대지권·매매목록·공동담보목록·신탁원부의 실제 판독 계약은 추가 표본 검증이 필요하다.

| 표본 | PDF 쪽수 | 표제부/갑구/을구 항목 | 취득 관련 행 | 근저당 설정 기록 | 말소되지 않은 근저당 |
|---|---:|---:|---:|---:|---:|
| C01 | 3 | 3/4/5 | 2 | 2 | 1 |
| C02 | 4 | 2/8/8 | 2 | 4 | 2 |
| C03 | 5 | 3/10/10 | 3 | 4 | 2 |
| C04 | 6 | 2/25/8 | 5 | 4 | 1 |
| C06 | 8 | 3/18/25 | 8 | 10 | 1 |
| C07 | 2 | 2/2/3 | 2 | 1 | 0 |
| C11 | 3 | 2/2/4 | 2 | 2 | 0 |
| C12 | 2 | 3/2/0 | 1 | 0 | 0 |
| C14 | 6 | 2/12/20 | 2 | 15 | 3 |
| C15 | 2 | 2/1/2 | 1 | 1 | 0 |

C04의 기존 파서는 표제부를 7개로 나눴으나 실제 표는 2개다. 이 표의 항목 수는 원문 대조 후 값이다. '말소되지 않음'은 해당 열람 문서의 등기 상태를 뜻하며, 실제 금융부채 잔액이나 법적 우선순위의 판정은 아니다. 역사 범위는 보존된 등기기록까지이며, 전산이기 이전 모든 거래가 들어 있다고 가정하지 않는다.

## 2. 이 표본이 요구하는 모델의 핵심

| 관측 사례 | 저장해야 하는 차이 |
|---|---|
| C01: 1996년 매매 → 2021년 증여, 2014년 근저당의 채무자만 2021년 변경 | 취득 원인과 권리 최초 설정일을 보존. 채무자 변경을 새 대출·새 근저당으로 만들지 않음 |
| C01·C02: 옛 채무자 이름·주소에만 말소선 | 권리 전체 말소와 필드의 옛 값 말소를 구분 |
| C03: 전세금·가압류 청구금액·근저당 최고액, 소유자의 이름·국적 변경 | 금액 종류와 당사자 역할을 분리. 이름 변경은 소유권이전이 아님 |
| C04: 같은 매매목록을 참조하는 지분 취득 3행, 지분 '10분의2.4' | 거래 1개와 지분 배분 여러 개. 지분을 정확한 분수로 저장 |
| C04: 공동담보목록 번호만 존재 | 목록의 미수령 상태를 저장. 건물별 최고액을 회사 전체 대출로 중복 합산하지 않음 |
| C06: 신탁 이전 → 신탁재산 귀속 → 매매 | 수탁자·등기명의자·매수인을 구분. 신탁원부 없는 수익자는 미확인 |
| C06: 아파트 한 건만 공동담보에서 소멸 | 담보 구성원 일부 해제와 본건 근저당 전체 말소를 분리 |
| C11: 소유자와 채무자가 다른 회사, 근저당권자가 국가 | 소유자·담보 제공자·채무자·채권자를 별도 역할로 연결. 채권자를 은행으로 제한하지 않음 |
| C12: 본건·창고·사랑채·보일러실·정자가 같은 '1층'에 반복 | 면적을 부속건물/구성요소/층별 여러 행으로 저장. 층 번호 하나로 덮어쓰지 않음 |
| C14: 같은 사람이 1/2을 취득한 뒤 남은 1/2 추가 취득 | 최신 소유권 행만 사용하지 않고 남은 지분을 누적해 현재 1/1 계산 |
| C14: 같은 은행·같은 날짜·같은 최고액의 설정 2건, 서로 다른 접수번호 | 금액·은행·날짜만으로 권리를 합치지 않음 |
| C14: 말소 1행이 근저당 6개를 지목 | 등기 사건과 대상 권리는 일대다 관계 |
| C07·C11·C15: 모든 근저당 말소, C12: 을구 '기록사항 없음' | 확인된 현재 0건과 추출 실패/상태 미확인을 구분 |

근저당의 채권최고액을 실제 잔액으로 사용할 수 없다. 법원 사례도 채권최고액 등기만으로 실제 피담보채권의 존재나 액수를 추정하지 않는다. [서울북부지방법원 공개 사례](https://slbukbu.scourt.go.kr/dcboard/new/DcNewsViewAction.work?cbub_code=000213&gubun=44&pageIndex=1&scode_kname=&searchWord=&seqnum=9463)

거래가액 등기 규정은 모든 취득 원인·모든 시대의 가격을 제공하지 않는다. 여러 부동산이나 당사자 구성이 포함되면 본문 대신 매매목록을 참조할 수 있다. 거래가격은 **목록/계약 전체 가격인지, 개별 부동산·지분 가격인지** 범위를 같이 보존해야 한다. [거래가액 등기에 관한 업무처리지침, 2025-01-31 시행](https://www.law.go.kr/LSW/admRulInfoP.do?admRulSeq=2200000106191)

## 3. 도메인 용어와 데이터 소유

용어의 정본은 [부동산 등기 모델 설계 용어](iros-model/CONTEXT.md)다. 아래 표는 이 설계에서의 주요 연결을 설명한다. 이 용어 문서는 현재 제품의 운영 CONTEXT에 새 저장 스키마를 적용한 문서가 아니다.

| 용어 | 모델에서의 뜻 |
|---|---|
| 부동산 | IROS 고유번호로 구별되는 등기 대상. 회사나 주소 문자열과 다른 개체 |
| 사업장-부동산 연결 | 회사 주소 검색으로 찾았다는 근거. 해당 회사의 소유 자산이라는 뜻이 아님 |
| 등기 문서 | 특정 열람시점의 기록을 담은 PDF. 재열람하면 다른 문서가 추가될 수 있음 |
| 판독 실행 | 같은 PDF를 특정 추출기·모델·계약 버전으로 구조화한 불변 결과 |
| 등기 항목 | 표의 실제 표시/순위번호와 각 칸을 보존한 원문 행. 부기번호·옛 번호 포함 |
| 취득 | 매매·증여·상속·경매·신탁·보존 등 구분된 원인으로 지분을 받은 기록 |
| 거래 | 여러 항목·부동산·당사자를 묶는 계약/매매목록 단위. 가격의 저장 단위 |
| 근저당 | 일정 최고액까지 담보하는 등기상 권리. 실제 대출 계약·잔액과 별개 |
| 공동담보 그룹 | 동일 담보권의 부동산 집합. 목록·관계가 확인되어야 합칠 수 있음 |
| 현재 | 선택한 판독 문서의 열람시점 기준. 조사 시점과 등기원인일·접수일은 다름 |
| 원문 근거 | 문서·쪽·표 영역·순위번호·필드·말소선과 연결되는 위치 정보 |

원격 정본 `CONTEXT.md`는 회사 정본은 `company`, CEO Loan 업무는 `ceoloan`으로 분리하고 CEO Loan 웹 역할이 `company`를 읽고 `ceoloan`만 쓰도록 정한다.

**권고 결정:** 등기 사실은 공유 자산 사실이므로 중앙 DB `company_main.real_estate`라는 전용 스키마에서 관리한다. 회사명·사업자번호는 기존 `company.companies`를 참조하며 복사하지 않는다. 모기지 대상·상담·담당자·통화 상태는 기존 `ceoloan`에 남긴다. CEO Loan 마이그레이션으로 `company`나 새 공유 스키마를 만들지 않는다.

추후 적용 시 중앙 데이터 담당 마이그레이션과 수집 전용 역할이 `real_estate`를 쓰고, CEO Loan 웹은 승인된 조회 뷰와 인증된 파일 조회 권한만 받는다. **현재 ceoloan DB 역할의 쓰기 권한을 확대하지 않았다.** 이 스키마와 역할은 이번 설계의 제안이며 운영 합의·적용은 다음 구현 단계다.

대안은 `company`에 모든 등기 테이블을 넣거나 `ceoloan`에 자료를 복제하는 것이다. 전자는 회사 식별 정보와 자산·권리 이력을 함께 관리하는 부담이 커지고, 후자는 다른 서비스가 같은 자산을 또 수집하고 고치게 된다. 전용 공유 스키마와 회사 참조를 선택하면 중앙 사실과 영업 업무의 경계를 유지할 수 있다.

## 4. 관계 구조

다음은 구현 전 논리 모델이다. 분석에 필요한 값은 열로 저장한다. JSONB는 원문 칸·말소선·계약별 비정형 조건·검증 결과를 보존하는 데 사용하며, 이름·지분·기준 날짜·금액·권리 상태를 JSON에만 숨기지 않는다.

```mermaid
erDiagram
    company_companies ||--o{ company_property_links : references
    properties ||--o{ company_property_links : located_at_or_verified_owner
    properties ||--o{ registry_documents : observed_at
    file_objects ||--o{ registry_documents : original
    registry_documents ||--o{ extraction_runs : interpreted_as
    extraction_runs ||--o{ registry_entries : contains
    registry_entries ||--o{ source_spans : supports
    registry_entries ||--o{ ownership_interests : acquires
    transactions ||--o{ transaction_observations : observed_as
    transaction_observations ||--o{ transaction_members : covers
    properties ||--o{ transaction_members : transferred
    registry_entries ||--o{ rights : establishes
    rights ||--o{ right_changes : changes_or_cancels
    rights ||--o{ right_party_roles : debtor_or_creditor
    party_mentions ||--o{ right_party_roles : printed_party
    collateral_groups ||--o{ collateral_members : includes
    properties ||--o{ collateral_members : secures
```

### 공통 타입과 참조 규칙

모든 테이블의 기본 키는 UUID, 생성시각은 timestamptz다. 아래 표에서 생략한 `id`·`created_at`와 참조 필드 인덱스를 공통으로 갖는다. 주요 날짜는 `date`, 원본의 열람·실행시각은 시간대가 있는 `timestamptz`다. 원문이 날짜만 제공하면 시각을 만들어 넣지 않는다.

금액은 `numeric(20,2)`와 ISO 통화코드 `char(3)`로 저장하며 KRW 원문은 정수 원 단위로 보존한다. 지분은 분자·분모 `numeric(38,0)`, 분모 > 0, 원문 지분 문자열을 함께 보관한다. '10분의2.4'는 정확하게 6/25로 환산하고 변환 근거를 남긴다. 통화·지분·면적에 float를 사용하지 않는다. 정확히 환산한 분수의 분자/분모가 허용 크기를 넘으면 원문을 유지하고 수치 확정을 보류한다. 면적은 `numeric(18,6)`·원문 단위·정규화 m²·변환 방법을 보관한다.

모든 판독 사실은 `extraction_run_id`를 갖거나 동일 실행의 원문 항목 FK로 그 실행에 연결된다. 서로 다른 판독 실행의 항목·당사자 표기·권리를 섞는 참조는 저장 단계에서 거부한다. 부동산·확인된 당사자·거래 식별 그룹·공동담보 식별 그룹은 여러 문서가 함께 참조할 수 있는 개체다. 이 식별 개체와 각 문서의 관측 사실을 구분한다.

### A. 파일·열람·판독

| 테이블 | 주요 필드와 저장 규칙 |
|---|---|
| `file_objects` | `storage_backend text`, `storage_key text`, `sha256 char(64)`, `byte_size bigint`, `mime_type text`, `original_filename text`, `access_scope text`, `download_path text nullable`, `link_status text`, `hash_verified_at timestamptz`. PDF·추출 JSON·위치 자료를 각각 파일 객체로 관리. UNIQUE(backend,key), SHA-256 인덱스. DB에 PDF 바이트를 넣지 않음 |
| `registry_reads` | `request_id UUID`, `run_id text`, `requested_company_id UUID FK company`, `source_address_id UUID FK`, `address_input text`, `selected_property_id UUID FK nullable`, `expected_unique_number text`, `selection_evidence_file_id UUID`, `requested_at/paid_at/finished_at timestamptz`, `status text`, `fee_amount numeric`, `currency char(3)`, `payment_transaction_no text nullable`, `approval_no text nullable`, `document_id UUID nullable`, `failure_stage/error_code text nullable`, `listed_request_at timestamptz nullable`, `listed_timestamp_kind text`, `request_link_method text`, `resumed_from_request_id UUID nullable`. 결제 성공·PDF 미수령도 따로 기록. 결제정보 비밀값은 저장하지 않음 |
| `registry_documents` | `property_id UUID`, `original_file_id UUID`, `read_id UUID nullable`, `document_kind text`, `includes_cancellations bool`, `id_disclosure_mode text`, `registry_state text`, `registry_office_code/name text`, `viewed_at timestamptz`, `viewed_at_raw text`, `page_count int`, `source_uid_raw text`, `issued_or_viewed_mode text`, `source_title text`, `history_coverage text`(present_register/transcribed_subset/unknown), `history_cutoff_date date nullable`, `history_cutoff_reason_raw text nullable`. 원본 해시와 고유번호로 중복 문서 판별, 열람용/발급용 구별 |
| `extraction_runs` | `document_id UUID`, `schema_version/extractor_version/prompt_version/model_id text NOT NULL`, `started_at/finished_at timestamptz`, `status text`, `structured_file_id/layout_file_id UUID`, `validation_report jsonb`, `reviewer/reviewed_at`, `title_complete/ownership_complete/encumbrances_complete bool`, `unresolved_annex_count int`, `failure_detail jsonb nullable`. 사용하지 않는 프롬프트·모델 버전은 사전 정의된 not-used 값, 사용했다면 실제 버전 필수. 자동 추출과 검증된 결과를 구분. 확정 결과는 불변으로 보존 |

`registry_reads.status`는 `requested → candidate_verified → payment_ready → payment_confirmed → document_received → source_verified`와 `selection_failed/payment_uncertain/paid_document_pending/failed`를 구분한다. 거래번호는 수단+provider 범위에서 고유하게 관리하되 한 결제에 여러 문서가 들어가는 미래 배치는 결제와 읽기 연결표를 추가하기 전 지원하지 않는다. 이번 공식 경로처럼 1건씩 운영하면 이 모델로 결제 상태와 복구를 추적할 수 있다.

### B. 부동산과 회사 연결·표제부

| 테이블 | 주요 필드와 저장 규칙 |
|---|---|
| `properties` | `registry_unique_number text UNIQUE`, `property_kind text`(land/building/unit), `registry_office_code text nullable`, `registered_scope text`(whole_property/registered_floor_or_portion/exclusive_unit), `published_extraction_id UUID nullable`. 주소·회사명은 PK가 아님. 토지와 건물은 같은 주소라도 다른 고유번호로 관리. 집합건물의 전유부와 건물 부모 관계는 근거 확보 후 연결 |
| `company_property_links` | `company_id UUID FK company.companies`, `property_id UUID`, `source_address_id/source_snapshot_id UUID nullable`, `read_id/document_id UUID nullable`, `link_role text`(business_address_search_result/registered_owner_verified/other_verified), `property_scope text`(whole_building/unit/floor_or_portion), `source_address_raw text`, `match_method text`, `evidence_span_id UUID nullable`, `verified_by/verified_at`, `observed_from/to timestamptz nullable`. 이번30개 물건의 회사 연결은 주소 검색 결과이며 회사 소유 확인값이 아님 |
| `property_descriptions` | `extraction_run_id UUID`, `entry_id UUID`, `property_id UUID`, `component_id UUID`, `subject_scope text`, `purpose_land_number_raw text nullable`, `description_event_kind text`, `description_status text`, `land_address_raw/road_address_raw/building_name/block/unit/structure/use_raw text nullable`, `display_registration_date date nullable`, `description_cause text nullable`, `land_category_raw text nullable`, `land_area_m2 numeric nullable`, `exclusive_area_m2 numeric nullable`, `construction_completion_date date nullable`. 모든 표제 이력 보존, 새주소로 옛주소를 덮어쓰지 않음. 준공일이 원문에 없으면 NULL |
| `area_segments` | `description_id UUID`, `segment_order int`, `component_label/component_kind/floor_label/use_raw text`, `floor_number int nullable`, `is_basement bool nullable`, `area_value numeric`, `area_unit text`, `area_m2 numeric nullable`, `area_scope text`(total/component/exclusive/share), `parent_segment_id UUID nullable`, `conversion_method text nullable`, `evidence_span_id UUID`, `is_additive bool`, `same_area_reference_to_segment_id UUID nullable`. 총면적과 세부 구성면적을 모두 합산하지 않도록 parent와 scope 사용 |

`company_property_links`의 소유 확인은 실제 등기 당사자와 회사의 확인된 법인 식별정보 또는 별도 근거로 한다. 개인사업자의 이름이나 대표자 이름이 같다는 이유로 회사 소유로 확정하지 않는다. 사업장 층이 있는 회사 주소로 통건물 등기를 읽었다면 그 범위 차이를 저장한다.

### C. 원문 항목·필드 근거·사건 관계

| 테이블 | 주요 필드와 저장 규칙 |
|---|---|
| `registry_entries` | `extraction_run_id UUID`, `component_id UUID`, `section_instance_no int`, `subrecord_kind text`, `inherited_rank_raw text nullable`, `section text`(title/A/B), `subsection text`(건물표시/전유부/대지권 등), `rank_raw text`, `main_rank int nullable`, `subrank text nullable`, `former_rank_raw text nullable`, `source_order int`, `purpose_raw text`, `receipt_date date nullable`, `receipt_no_raw text nullable`, `cause_date date nullable`, `cause_raw text nullable`, `annotation_date date nullable`, `raw_columns jsonb`, `raw_text text`, `visual_cancellation_scope text`(none/field/whole/mixed/uncertain), `page_start/end int`. 식별은 실행+component+section_instance+source_order, 순위번호만 고유키로 쓰지 않음 |
| `source_spans` | `extraction_run_id UUID`, `entry_id UUID nullable`, `component_id UUID nullable`, `geometry_precision text`(field/row/table/page), `evidence_media text`(native_text/raster/mixed), `transcription_method text`, `section/subsection text nullable`, `target_table/field_path text`, `target_row_id UUID`, `page_no int`, `bbox numeric[]`(4좌표), `coordinate_system text`, `quoted_text text nullable`, `strike_lines jsonb`, `field_state text`(current/historical/canceled/uncertain), `value_status text`, `interpretation_method text`, `confidence numeric nullable`, `review_status text`. 한 사실에 여러 span 허용. 빈 section의 명시 문구는 항목 FK 없이 판독에 연결. 좌표는 PDF point 단위 top-left 기준 [x0,top,x1,bottom]와 페이지 폭·높이를 보존. 대상 행 존재와 실행 일치는 저장 validator로 확인 |
| `entry_relations` | `from_entry_id UUID`, `to_entry_id UUID nullable`, `relation_kind text`(changes/cancels/corrects/transfers_share/releases_member/provisional_becomes_final/assigns_provisional_right/adds_land_right_to_security/splits_parcel/terminates_trust/encumbers_secured_claim/transcribed_from_prior_register/continues_registered_right), `target_scope text`(whole_right/party_field/share/collateral_member/secured_claim), `target_party_mention_id UUID nullable`, `share_num/den numeric nullable`, `target_reference_raw text`, `evidence_span_id UUID`, `resolution_status text`. 말소 한 행 → 여러 권리, 변경 행 → 기존 설정 권리 관계 보존 |

원문 말소선은 일부 필드에만 있을 수 있다. 말소선 존재만으로 행 전체나 권리 전체를 삭제하지 않는다. 기록의 최신 값을 만드는 책임은 원문 행 분리·시각 정보와 사건 관계를 해석하는 공식 추출 경로에 둔다. 금액을 읽은 뒤 소비자에서 경고하는 것으로 잘못된 자동 적재를 정당화하지 않는다.

### D. 당사자·소유권·거래

| 테이블 | 주요 필드와 저장 규칙 |
|---|---|
| `party_entities` | `party_kind text`(person/corporation/public_authority/unknown), `canonical_name text nullable`, `verified_corporate_registration_no text nullable`, `company_id UUID nullable`, `resolution_method/evidence/verification_status`. 확인된 법인 식별정보만 해당 namespace에서 고유화. 개인 이름이나 마스킹 식별번호는 전역 UNIQUE로 사용하지 않음 |
| `party_mentions` | `entry_id UUID nullable`, `component_id UUID nullable`, `entity_id UUID nullable`, `mention_order int`, `role_raw text`, `name_raw text`, `id_type text nullable`, `id_masked_raw text nullable`, `address_raw text nullable`, `branch_name_raw text nullable`, `nationality_raw text nullable`, `field_state text`, `source_span_id UUID`. 문서에 나온 이름·주소를 그대로 남김. 같은 문서의 이름·표시 변경 관계는 연결하되 다른 문서의 개인을 자동 합치지 않음 |
| `ownership_interests` | `extraction_run_id UUID`, `property_id UUID`, `acquisition_entry_id UUID`, `recipient_mention_id UUID`, `transaction_observation_id UUID nullable`, `acquisition_kind text`, `acquired_share_num/den numeric`, `remaining_share_num/den numeric nullable`, `acquired_cause_date/receipt_date date nullable`, `as_of_viewed_at timestamptz`, `observed_status text`, `share_resolution_status text`, `acquired_share_basis text`, `share_derivation_formula text nullable`. 취득 시 지분과 해당 문서 시점의 남은 지분을 구분. 일부 이전 관계는 entry_relations에 정확한 분수로 저장 |
| `transactions` | `identity_status text`(unresolved/verified), `verified_sale_list_identity text nullable`, `grouping_basis/evidence text`, `published_observation_id UUID nullable`. 여러 문서에서 같은 계약으로 확인된 거래를 묶는 영구 식별 개체. 목록 번호만으로 전국/시대가 다른 거래를 병합하지 않음 |
| `transaction_observations` | `extraction_run_id UUID`, `transaction_id UUID`, `transaction_kind text`, `contract_cause_date date nullable`, `sale_list_ref_id UUID nullable`, `price_amount numeric nullable`, `price_currency char(3) nullable`, `price_scope text`(single_property/partial_share/multiple_assets/unknown), `price_status text`, `price_source_span_id UUID nullable`, `member_scope_complete bool`. 문서별로 확인된 가격·원인·목록 범위의 불변 사실. 전역 거래의 가격 집계는 선택한 관측 1개만 사용 |
| `transaction_members` | `transaction_observation_id UUID`, `property_id UUID nullable`, `property_reference_raw text nullable`, `entry_id UUID nullable`, `seller_mention_id/buyer_mention_id UUID nullable`, `transferred_share_num/den numeric nullable`, `allocated_price numeric nullable`, `allocation_method text nullable`, `party_role_basis text`(explicit/inferred_reviewed/unknown), `evidence_span_id UUID`. 전체 거래의 부동산·배분·매도인·매수인 연결. 매도인 명시가 없으면 이전 소유자라는 추론을 사실 칸에 자동 입력하지 않음 |

현재 소유권은 남은 지분들을 당사자별로 합산한 조회 결과다. 최근 순위번호 하나로 정하지 않는다. 신탁에서 등기명의자와 수탁자, 원부의 수익자·우선수익자는 다른 역할이며 원부가 없으면 후자는 미확인이다. 주민등록번호 미공개를 유지하고 마스킹 문자열에서 생년·성별·미공개 번호를 새로 추정하지 않는다. 개인정보가 담긴 원문 필드는 접근을 제한하고 검색·로그에서는 최소 표시만 사용한다.

같은 매매목록을 서로 다른 부동산 문서에서 수집해도 검증된 거래 식별 개체 하나에 여러 관측을 연결하고 가격 관측 1개만 선택한다. 목록 원문·관할·당사자·구성 부동산으로 동일 계약이 확인되기 전에는 미해결 거래 그룹으로 남기며 정확한 포트폴리오 거래가격 합계를 제공하지 않는다.

가격이 다자·다물건 거래 전체 값이면 선택한 거래 관측에 1회 저장한다. 개별 부동산 배분은 계약/목록에 명시된 값만 `allocated_price`로 기록한다. 면적비·지분비로 나눈 분석 추정치는 별도 분석 결과에 방법·가정을 기록하며 원문 거래가액을 덮어쓰지 않는다.

### E. 근저당·다른 권리·변경·공동담보

| 테이블 | 주요 필드와 저장 규칙 |
|---|---|
| `rights` | `extraction_run_id UUID`, `property_id UUID`, `root_entry_id UUID`, `right_kind text`(maximum_amount_mortgage/fixed_mortgage/jeonse/lease/seizure/provisional_attachment/provisional_disposition/superficies/provisional_registration/registration_restriction/compulsory_auction/voluntary_auction/other), `setup_mode text`(initial/additional_collateral/unknown), `setup_cause_date/setup_receipt_date date nullable`, `initial_max_amount/latest_registered_max_amount numeric nullable`, `registered_fixed_claim_amount numeric nullable`, `deposit_amount numeric nullable`, `attachment_claim_amount numeric nullable`, `amount_currency char(3) nullable`, `observed_status text`, `cancellation_entry_id UUID nullable`, `scope_raw text`, `registered_object_scope text`(whole_property/ownership_share/building_only/land_right_only/unit_and_land_right/secured_claim/unknown), `court_name_raw text nullable`, `court_case_ref_raw text nullable`, `term_start/end/return_due_date date nullable`, `registry_stated_interest_rate numeric nullable`, `interest_terms_raw text nullable`, `collateral_group_id UUID nullable`. 종류별 허용 금액 열을 CHECK. 말소됐어도 마지막 등기금액 보존 |
| `right_changes` | `right_id UUID`, `entry_id UUID`, `change_kind text`(debtor_assumption/creditor_transfer/merger/amount_change/cancellation/partial_cancellation/member_release/correction/scope_clarification), `target_scope text`, `cause_date/receipt_date/annotation_date date nullable`, `max_amount_before/after numeric nullable`, `currency char(3) nullable`, `scope_reference_raw text nullable`, `changed_fields jsonb`, `evidence_span_id UUID`. 기존 설정과 관계를 유지, 채무자 변경이나 합병을 새 권리로 세지 않음 |
| `right_party_roles` | `right_id UUID`, `party_mention_id UUID`, `role text`(debtor/creditor/jeonse_holder/collateral_provider/other), `from_entry_id/to_entry_id UUID nullable`, `from_receipt_date/to_receipt_date date nullable`, `role_status_as_of_document text`, `scope_raw text nullable`, `evidence_span_id UUID`. 다수 채무자·채권자와 변경 이력, 현재 역할 모두 조회 가능 |
| `annex_references` | `document_id UUID`, `source_entry_id UUID`, `annex_kind text`(sale_list/joint_collateral_list/trust_ledger/other), `office_namespace_raw text nullable`, `number_raw text`, `year int nullable`, `received_file_id UUID nullable`, `received_document_id UUID nullable`, `collection_status text`(referenced_only/received/verified/not_available), `scope_resolved bool`. 목록 번호의 관할·시대·문서 맥락을 보존. 전국의 같은 숫자라고 바로 병합하지 않음 |
| `collateral_groups` | `verified_annex_ref_id UUID nullable`, `identity_status text`(unresolved/verified), `verification_basis text`, `evidence_span_id UUID nullable`. 목록 원문이나 명시적 연결이 확인된 동일 담보권 집합만 그룹화 |
| `collateral_members` | `collateral_group_id UUID`, `source_extraction_id UUID nullable`, `source_annex_ref_id UUID nullable`, `property_id UUID nullable`, `property_reference_raw text`, `member_right_id UUID nullable`, `member_status_as_of_document text`, `member_ordinal_raw text`, `predecessor_member_observation_id UUID nullable`, `change_kind_raw text nullable`, `member_scope_kind text`, `member_scope_raw text`, `addition_entry_id/release_entry_id UUID nullable`, `receipt_date/annotation_date date nullable`, `evidence_span_id UUID`. 문서/목록 관측별 구성 이력을 보존하고 부동산당 선택한 판독으로 현재 구성 판단. 다른 부동산 UID를 모르면 원문 참조와 미해결 상태 유지. 본건 밖 아파트 말소를 본건 전체 말소로 처리하지 않음 |

같은 채권자·금액·날짜만으로 공동담보 그룹을 만들지 않는다. 미확인 공동담보가 있으면 회사/소유자 포트폴리오의 정확한 합계는 NULL 또는 '중복 가능·해결 미완료' 상태로 제공한다. 건물별로 기록된 최고액 합계를 표시할 때도 범위를 분명히 적는다.

등기 순위번호·접수일·접수번호는 원문 사실로 저장하지만 실제 배당 우선순위나 대출 가능액을 자동 확정하지 않는다. 채무자와 소유자가 다르면 '등기상 다른 당사자'라는 관측을 남기고, 보증·실제 담보 제공 계약의 법률관계를 추정해 채우지 않는다.

**실제 대출은 별도 자료 영역:** 잔액증명·금융기관 자료를 얻는 후속 단계가 승인되면 `loan_observations`를 도입해 실제 원금·잔액 기준일·약정 대출일·만기·금리·기관·원문을 보관하고 확인된 대출-담보 연결을 만든다. IROS만으로는 이 테이블의 값을 생성하지 않는다. 채권최고액을 120%/130%로 나누거나 설정연도를 대출 시작연도로 바꿔 실제 대출값을 만들지 않는다.


### F. 문서 구성·물건 관계·대지권·신탁

다음9개 테이블도 동일한 UUID·판독 실행·원문 근거 규칙을 적용한다. 생략한 FK는 UUID, *_raw와 상태/종류는 text, 날짜는 date, 기간은 int, 수익권 금액은 numeric(20,2), 지분은 numeric(38,0), 진위는 bool, 구조화 부수 조건은 jsonb다. 아래는 SQL 마이그레이션이 아니라 논리 필드 계약이다.

| 테이블 | 주요 필드와 저장 규칙 |
|---|---|
| `document_components` | `extraction_run_id`, `document_id`, `parent_component_id nullable`, `component_kind`(registry_body/title_subject/sale_list_copy/joint_list_copy/trust_change_table/trust_contract_copy/separator), `logical_annex_ref_id nullable`, `physical_copy_ordinal`, `subject_kind`, `subject_property_id nullable`, `subject_reference_raw`, `page_regions jsonb`(쪽·PDF point bbox·정밀도), `content_mode`(native_text/raster/mixed), `review_status`. 같은 쪽에 본문과 목록이 섞이거나 한 목록이 여러 번 인쇄되어도 물리 사본을 보존한다. 사본 수를 거래·권리 수로 계산하지 않음 |
| `property_relations` | `source_extraction_id`, `from_property_id`, `to_property_id nullable`, `to_subject_component_id nullable`, `target_reference_raw`, `relation_kind`(land_building_reference/purpose_land/part_of_described_collective_building/split_from/split_to/register_continuation), `reference_role`(prior_register/current_register), `record_transcription_date date nullable`, `record_transcription_reason_raw text nullable`, `event_entry_id nullable`, `cause_date/annotation_date nullable`, `identity_resolution_status`, `evidence_span_id`. 다대다 연결. 확인되지 않은 토지/부모 건물 UID는 NULL이고 원문 지번·동 설명만 보존 |
| `land_right_observations` | `extraction_run_id`, `unit_property_id`, `entry_id`, `title_component_id`, `purpose_land_number_raw`, `purpose_land_property_id nullable`, `purpose_land_component_id`, `right_kind_raw`, `share_num/share_den numeric(38,0) nullable`, `share_raw`, `cause_date/registration_annotation_date nullable`, `observed_status`, `evidence_span_id`. 목적 토지별 종류와 정확한 비율·변경 이력을 보존. 비율 분자에 소수가 있으면 원문을 유지하고 정확한 정수 분수로 정규화. 전유부분의 소유 지분과 별개 |
| `trust_agreements` | `office_namespace`, `ledger_number_raw`, `permanent_document_uid nullable`, `identity_status`, `verified_identity_basis`, `published_observation_id nullable`. 관할+연도 포함 원부번호와 실제 연결로 식별. 내용이 비슷하다는 이유로 다른 물건의 원부를 병합하지 않음 |
| `trust_observations` | `extraction_run_id`, `agreement_id`, `annex_ref_id`, `contract_component_id`, `registration_entry_id nullable`, `contract_signed_date nullable`, `registration_cause_date/receipt_date nullable`, `receipt_no_raw`, `base_term_start_event`, `base_duration_months nullable`, `stated_start_date date nullable`, `scheduled_end_date nullable`, `scheduled_end_is_conditional bool`, `extension_condition_raw`, `termination_entry_id nullable`, `observed_termination_date nullable`, `observed_status`, `selected_fields_complete bool`, `full_clause_transcription_complete bool`. 원부의 역사적 계약과 본문의 관측시점 종료를 연결 |
| `trust_roles` | `trust_observation_id`, `party_mention_id`, `role`(grantor/trustee/priority_beneficiary/residual_principal_beneficiary/income_beneficiary/debtor/agent), `priority_rank nullable`, `priority_group_key nullable`, `branch_name_raw`, `role_scope_raw`, `from_component_id`, `evidence_span_id`. 같은 사람/법인이 여러 역할을 가져도 각각 보존. 채무자는 위탁자와 같다고 자동 복사하지 않음 |
| `trust_assets` | `trust_observation_id`, `member_order`, `property_id nullable`, `property_kind`, `property_reference_raw`, `description_component_id nullable`, `share_num/share_den nullable`, `area_m2 nullable`, `member_resolution_status`, `evidence_span_id`. 별지의 신탁재산 범위와 본문 UID의 실제 대응. 토지 계약과 건물 계약의 각 재산 범위를 보존 |
| `trust_benefit_limits` | `trust_observation_id`, `beneficiary_role_id`, `priority_rank`, `priority_group_key nullable`, `secured_credit_agreement_date date nullable`, `certificate_no_raw nullable`, `limit_amount numeric(20,2)`, `currency`, `limit_kind`, `loan_ratio_num/den nullable`, `loan_ratio_raw`, `claim_scope_raw`, `scope_resolution_status`, `evidence_span_id`. 실제 잔액·근저당 최고액과 별개. 명시된120%에서 계산한 계약상 기준금액은 분석 파생값에 계산식·원문 한도/비율·비실행 확인 상태를 함께 저장 |
| `trust_terms` | `trust_observation_id`, `component_id`, `clause_reference_raw`, `term_kind`, `value_type`, `date_value/duration_months/amount_value/rate_value/currency nullable`, `raw_text`, `value_json nullable`, `selected_option bool nullable`, `overrides_term_id nullable`, `excluded_clause_reference_raw nullable`, `effective_scope`, `evidence_span_id`. 기간 연장·변제 범위·처분 조건·특약 우선·적용 제외·선택된 비용과 미선택 대안을 구분. 핵심 날짜·금액·역할은 위 정규화 열에 저장하고 장문의 표준 조항/계약별 부수 조건은 원문과 JSONB 보존 |

추가 참조 조건:

- party_mentions는 같은 판독 실행의 entry 또는 component 중 하나 이상에 연결한다. 원부의 당사자에게 본문 항목을 지어내지 않는다.
- entry_relations의 to_entry_id가 NULL이면 실제 target_reference_raw와 unresolved_prior_register 상태가 필수다. 다른 등기기록의 항목 UUID를 추정하지 않는다.
- 대지권의 종류·목적 토지별 비율·이력은 land_right_observations에서 보존한다. 1동 전체·목적 토지·전유부분 면적을 섞지 않는다.
- 같은 1순위 우선수익자가3곳이면 trust_roles와 trust_benefit_limits를 각각3행으로 저장하고 priority_group_key로 공동1순위를 연결한다. 수탁자인 은행과 세 우선수익 법인은 별개다.
- 우선수익권 한도는 실제 대출잔액이나 근저당 최고액이 아니다. 계약에 명시된 비율로 계산한 값도 분석 파생값으로만 보존하며 대출 사실로 승격하지 않는다.
- 신탁의 고정 시작/예정 종료 날짜와 기간·연장 조건, 실제 본문 종료일을 따로 저장한다. 계약상 신탁 종료 예정일을 대출 만기로 사용하지 않는다.
- 전산분할 이기의 기록일은 원래 권리의 설정일과 다르다. 기존 설정 사건과 split_transcription 항목, 그 연결을 보존한다.
- 등기기록 이기로 현재 문서의 이전 순위와 새 순위가 연결되면 register_continuation과 continues_registered_right, 공동담보 member predecessor를 남긴다. 이를 새 담보나 말소로 세지 않는다.
- source_spans의 페이지 전체 근거는 geometry_precision=page다. 조사 자료의 페이지 bbox를 필드 단위 좌표가 확인된 것처럼 표시하지 않는다.

## 5. 날짜·누락·현재 상태·중복 계약

### 날짜를 섞지 않는다

| 필드 | 사용 목적 |
|---|---|
| `cause_date` | 등기원인으로 적힌 계약·증여·해지 등 날짜. 거래 연도 분석 |
| `receipt_date + receipt_no_raw` | 등기 접수 순서와 사건 식별. 같은 날짜의 설정·말소 구별 |
| `annotation_date` | 접수일이 없는 부기·공동담보 변경 등에 적힌 날짜. 접수일로 복사하지 않음 |
| `viewed_at` | 이 등기 상태를 관측한 실제 열람시점 |
| `extraction_started_at/reviewed_at` | 판독·검토 처리시점 |
| `term_start/end` | 명시된 전세권 등 존속기간. 근저당 설정시점으로 대출 만기 생성 금지 |

등기 사건의 접수 순서에 따른 상태와 원인일별 거래 분석을 분리한다. 과거 시점 상태 조회는 그 시점까지의 접수·변경 관계로 재구성하며, 다른 시점에 받은 문서들의 현재 상태를 단순 합산하지 않는다. 금전 회수일·계약의 법률상 효력 발생일은 원문이나 별도 검증 없이는 생성하지 않는다.

### NULL은 사유를 갖는다

숫자·날짜 열의 NULL에는 해당 `source_spans.value_status` 또는 사실별 상태 열로 `not_stated / not_applicable / annex_not_collected / unreadable / extraction_failed / identity_unresolved / scope_unresolved`를 남긴다. 값이 있는 경우는 `observed`; 실제 금융 잔액은 별도 데이터 출처가 없으면 `not_provided_by_registry`다.

가격이 없음과 가격 0원은 다르다. 을구의 '기록사항 없음', 또는 모든 설정·말소 관계를 확인한 경우에만 **현재 등기된 근저당 건수/최고액 합계**를 0으로 계산한다. 해당 경우에도 실제 대출 잔액은 NULL이다. 판독 실패·권리 관계 미해결 때 합계를 0으로 반환하지 않는다.

### 재수집·재판독은 불변 이력으로 보존한다

1. PDF 바이트 해시가 같으면 기존 파일 객체를 재사용한다. 새로운 열람 문서는 열람시점·PDF 해시와 함께 별도로 보존한다.
2. 동일 PDF의 판독 버전은 `UNIQUE(document_id, schema_version, extractor_version, prompt_version, model_id)`로 중복 방지한다. 이 키의 버전 열은 NOT NULL이며 사용하지 않는 프롬프트·모델에는 사전 정의된 not-used 값을 사용한다. 사용한 버전을 모르면 검증된 결과로 확정하지 않는다. 확정 전 실패 재시도는 같은 실행의 시도 이력으로 관리하고 성공 결과를 따로 중복 생성하지 않는다.
3. 사실은 문서/판독 실행 안에서 불변이다. 더 나은 파서가 이전 결과를 덮어쓰지 않는다.
4. `properties.published_extraction_id`는 승인된 검증 상태의 판독으로만 바꾼다. 늦게 끝난 옛 문서가 새로운 열람 상태를 덮어쓰지 않도록 원본 viewed_at과 선택 버전을 비교한다.
5. 현재 조회는 부동산당 선택한 판독 1개에서 계산한다. 다른 판독의 동일 설정을 함께 더하지 않는다. 거래 전체 가격은 검증된 거래 그룹당 선택한 관측 1개만, 담보 포트폴리오 금액은 검증된 동일 담보권 그룹당 1개만 사용한다.
6. 여러 문서 사이 같은 사건을 연결할 때는 고유번호·section·옛/현 순위·접수일·접수번호·목적·원문 연결을 함께 대조한다. 순위번호 단독키 또는 이름·금액·날짜만으로 사건을 병합하지 않는다.
7. 목록이 없다는 이유로 본문에서 확인된 소유권·근저당 사실을 모두 버리지 않는다. 영역별 완전성과 미확인 범위를 보존하고, 정확한 전체 거래가격/포트폴리오 합계에는 제한을 적용한다.

## 6. 파일 저장과 링크 계약

### 저장 키와 실제 경로

```text
storage_backend = registry-mounted-v1
storage_key     = original/2026/09/<registry_unique_number>/<sha256>.pdf
실제 root        = DB 서버 /mnt/ceoloan/registry
실제 파일         = root + storage_key
```

파일 이름에 소유자나 주민번호를 사용하지 않는다. `original_file_id`를 문서에 연결하고 `file_objects`에 디스크 상대 키·해시·바이트 수·미디어 종류·검증시각·접근 링크를 저장한다. backend 이름의 실제 호스트·root는 서버 설정이 소유한다. 서버가 바뀌어도 부동산/거래 키를 바꾸거나 모든 DB 행에 호스트 IP를 다시 쓰지 않는다.

같은 폴더의 `.part`에 업로드 → 해시 일치 확인 → 최종 이름으로 이동 → 파일 객체 기록 → 구조화 DB transaction 순으로 확정한다. 파일 확정 후 DB 실패는 이미 보관된 파일 객체/요청을 재사용해 적재만 재개한다. DB에 원본 없는 링크를 먼저 확정하거나 결제를 다시 하지 않는다. 이후 배치의 실패 정리 정책은 요청·파일 이력을 보고 결정하며 자동 삭제하지 않는다.

이번 실제 저장 권한은 전용 디렉터리 0750, 파일 0640, 소유자 chaconne다. CEO Loan 웹에 디스크 읽기 권한이나 마운트를 추가하지 않았다. 현재 웹의 통화 녹음 `FileField`가 있어도 공개 MEDIA 저장을 등기 원본 경로로 재사용하지 않는다.

### DB에 넣을 접근 링크

권고 링크는 `download_path = /documents/registry/<document_uuid>/original/` 형태의 **영구 식별 URL 경로**다. 운영 도메인은 앱이 붙인다. 인증된 다운로드에서 DB의 문서 → file_objects → backend/key를 찾아 중앙 파일 저장소에서 전송한다. 실제 바이트 접근은 저장소 담당 서비스/표준 Storage 어댑터에 맡기며, 기존 중앙 자료 전송 기능을 확인해 재사용한다.

- 링크는 회사/문서 조회 권한을 검사한 후에만 PDF를 반환한다. 목록·자료 접근도 같은 기준을 사용한다.
- 사용자에게 서버 SSH 경로나 공개 정적 PDF 경로를 넘기지 않는다.
- 만료되는 signed URL은 요청 때 생성하고 장기 DB 링크로 저장하지 않는다.
- `download_path`가 아직 구현되지 않은 현재 표본 manifest는 `link_status=designed_not_implemented`, 접근 링크 NULL이다. 실제 저장 host/path/key/hash는 모두 보존돼 있다.
- 다운로드 구현의 성공조건은 해당 링크에서 **같은 SHA-256의 PDF 바이트를 받는 것**이다. HTTP 200이나 파일 존재만으로 완료하지 않는다.

마운트 디스크는 저장 위치이며 별도 백업은 아니다. 현재 약 22GiB 여유가 확인됐다. 이번 10개 원본은 약 0.79MiB다. 장기 수집 전 원본·JSON·위치 자료의 성장, 접근 권한, 기존 백업 경로 적용·복원 검증을 확정한다. 새 자동 백업/청소 작업은 이번에 만들지 않았다.

## 7. 추후 공식 수집·저장 경로와 검증 조건

현재 공식 경로는 `scripts/iros_dom.py`의 검색 → 정확히 1개 고유번호 → 열람 범위·미공개 → 총1통 700원 → 선불 결제 → 기존 뷰어 → PDF → `iros_ssp.parse_registry_text`로 고유번호/3개 section/원문 항목 JSON을 저장하는 데까지다. 이 파서는 소유자·금액·날짜·관계·개별 말소 상태의 완전한 구조화 기능이 없다.

권고 구현 연결은 다음과 같다.

```text
company 상세/주소 읽기
→ 요청 상태·정확한 부동산 선택 근거 저장
→ 기존 IROS 공식 열람/결제/PDF 경로
→ 마운트 원본 확정·해시·문서 메타데이터
→ PDF 표 칸·행·말소선·원문 위치 추출
→ 근거와 실제 선택지로 소유권·권리·사건 관계 해석
→ 영역별 계약 검증·필요한 검토
→ 한 DB transaction으로 판독 사실 저장
→ 검증된 published_extraction 선택
→ 회사/자산 조회와 인증 원본 링크
```

의미 판단은 기존 제품/승인된 LLM 경로에서 근거·선택지·출력 계약을 전달해 수행한다. 스크립트의 정규식이나 회사 업종 분류표로 매매·신탁·말소 범위·당사자를 임의 결정하지 않는다. 기계적 숫자/날짜 정규화·무결성 확인과 의미 해석의 책임을 분리한다. 같은 책임의 두 번째 브라우저/결제/적재 경로를 만들지 않는다.

C04는 현재 파서가 항목 시작을 연속 숫자로 추정해 표제부의 2층·3층 등을 표시번호로 오인한 사례다. 향후 자동 적재를 연결하기 전에 **실제 첫 번째 칸의 번호, 표의 셀 경계, 페이지 이어짐, 권리자 칸과 개별 말소선**을 원문 행의 생산 단계에서 보존하도록 고쳐야 한다. 이번 표본은 PDF 화면과 대조한 조사용 구조화이며, 기존 코드가 이 모델을 자동 생성한다고 주장하지 않는다.

### 저장 승인 전 필수 조건

| 검사 | 기대 결과 |
|---|---|
| 문서 식별 | 결제 선택·PDF 헤더·저장 property의 고유번호 일치, 페이지 연속·필수 section 존재 |
| 빈 영역 | '기록사항 없음'과 판독 실패의 빈 결과를 구분 |
| 셀/행 | C04 표제부 2개 복원, 층수로 가짜 항목 생성하지 않음, 이어진 페이지의 같은 행 연결 |
| 날짜/금액 | 원인일·접수일·부기일 원문 근거, 통화와 금액 종류 유지, 한글 금액 대조 |
| 소유권 | C04 지분3/10+5/10+2/10=1, C14 같은 사람의 남은1/2+추가1/2=1; 미완성/범위제한이면 이유 표시 |
| 권리/부분 변경 | C01·C02 옛 채무자 필드 말소와 권리 전체 구분; C06 공동담보 일부 소멸 구별 |
| 복수 대상 | C14 말소14 → 권리4·7·8·9·10·11 전부 연결 |
| 중복 | C14 설정12·13 유지, 재판독/재수집은 현재 합계에 두 번 반영하지 않음 |
| 목록 | 미수령 매매/공동담보/신탁 목록의 사유·참조 번호 유지. 미확인 전체 가격/부채를 계산하지 않음 |
| 파일 | 업로드 전후 해시 동일, 디스크 마운트 및 파일 권한 확인, 인증 링크로 같은 PDF 수령 |
| 실패 복구 | 결제 상태 불확실/결제완료 PDF미수령에서 재결제 차단, 기존 뷰어 재개, DB실패에서 원본 재업로드·재결제 없이 적재만 재개 |
| 권한/보존 | ceoloan 웹의 company 쓰기 금지 유지, 공유 수집 역할 분리, 기존 파일·데이터·브라우저·배치 보존 |

## 8. 분석용 조회 계약

조회 뷰는 물리적인 사실 저장과 별도로 정의한다. 모두 선택한 판독과 열람시점·완전성 상태를 반환한다.

| 조회 | 계산과 제한 |
|---|---|
| 현재 등기명의자/지분 | 남은 ownership_interests를 확인된 당사자 범위에서 합산. 취득 원인·최초/추가 취득일 포함 |
| 누가·언제 샀는가 | acquisition_kind=sale의 명시된 매수인, cause_date·receipt_date 각각 제공. 증여·보존·신탁은 별도 결과 |
| 얼마에 샀는가 | transactions에서 선택한 transaction_observations의 가격·통화·범위·가격 상태 제공. 목록 미수령이면 금액 NULL. 검증된 동일 거래 가격 1회 |
| 현재 담보 현황 | 말소되지 않은 권리·채권자·현재 채무자·최초 설정일·최고액. 판독이 불완전하면 건수/합계 미확인 |
| 은행별·설정연도별 변화 | 설정과 해지/이전/채무자 변경을 각각 사건 종류로 집계. 추가 담보 설정을 신규 대출로 집계하지 않음 |
| 등기된 담보 유지기간 | 설정 접수일→말소 접수일 또는 열람시점의 기간. 실제 대출 기간/만기로 표시하지 않음 |
| 공동담보 중복 제거 | 검증된 collateral_group별 동일 권리를 1회만 집계. 미해결 그룹은 합계의 미완성 범위 표시 |
| 위험 이력 | 가압류·압류·가처분·전세·신탁 이력과 현재 상태, 청구금/전세금 구별. 모든 과거 금액을 대출로 합산하지 않음 |

당사자 역할·거래 구성원·원문 span을 조인할 때 한 권리가 여러 행으로 늘어날 수 있다. 금액 합계는 권리/거래 ID 단위에서 먼저 집계하고 당사자 상세를 붙인다. DISTINCT(금액)으로 중복을 없애면 실제로 같은 금액인 별개 권리를 잃으므로 사용하지 않는다.

주요 인덱스는 property UID 고유키, 문서(property,viewed_at), 판독(document,version), 항목(extraction,section,rank), 사건(receipt_date,receipt_no), 소유권(property,acquisition_kind,cause_date), 권리(property,observed_status,setup_receipt_date), 역할(right,role,status), 회사 연결(company,role), 목록(kind,namespace,number)다. 개인 이름 전체검색이나 원문 로그 노출은 운영 접근 정책이 확정되기 전 만들지 않는다.

## 9. 기존 승인·보호 조건과 작업 종료/재개

### 작업 시작 기준선

- 코드 정본: `chaconne@49.247.205.170:/home/chaconne/ceoloan/repo`, main `e9c013929378815c7294f52c9e76c330ef285ce9`. 시작 때 GitHub main과 일치하고 작업트리가 깨끗했다.
- Windows `C:\\cretop-agent\\iros_dom.py`·`iros_ssp.py`는 정본 SHA-256과 일치했다.
- 기존 `20260913_pay_001` PDF를 현재 파서로 재판독하여 기존 JSON과 동일한 결과(9쪽, 표제부2/갑구4/을구35)를 확인했다.
- 운영 DB는 ceoloan 역할로 read-only session을 사용했다. 이번 작업에 DB INSERT/UPDATE/DDL·배포·문자·cron·터널·인증서 변경이 없다.
- 원본 디스크 전용 폴더와 이번 표본만 새로 저장했다. 기존 `/mnt/data`, 다른 자료·브라우저·기존 추출 파일·다른 프로젝트의 미커밋 변경을 보존했다.

### 최소 구현과 실제 경로

최소 구현 게이트: **2단계에서 멈춤**. 기존 IROS 공식 실행기·shared HiddenBrowser·DesktopObserver와 설치된 PDF/JSON 도구를 재사용했다. 신규 브라우저 runner·생산 추출기·DB 적재 코드·의존성은 만들지 않았다. 표본 의미 해석은 현재 조정실 에이전트가 원문 화면과 대조해 수행했고, 파일 변환·숫자 검사·직렬화만 도구로 처리했다.

표본 승인 범위는 1건700원·최대10건·총7,000원, 기존 선불 수단, 말소사항 포함·주민번호 미공개다. 추가 토지·매매목록·공동담보목록·신탁원부의 유료 조회는 실행하지 않았다. `--until pay`로 정확히1건·700원을 확인한 뒤 `--until save`로 결제와 원문 수령을 수행했다. 공식 코드를 바꾸지 않았고 수집용 Chrome은 실행마다 정리했다.

### 다음 구현에서 재개할 위치

현재 요청의 **표본 조사와 저장 모델 설계는 완료**다. 운영 적재·파일 다운로드·목록 추가 수집은 아직 승인/구현되지 않은 별도 단계다.

설계의 23개 테이블은 파일/판독 이력, 원문 근거, 분석용 사실, 문서 사이 식별이라는 다른 책임을 나눈 논리 모델이다. 실제 구현에서 기존 공통 저장소·당사자 식별 기능을 재사용할 수 있으면 같은 책임의 새 테이블을 중복 생성하지 않는다. 특히 transaction_observations는 여러 건물 문서의 같은 전체 매매가격을 한 번만 집계하면서 원본별 판독 이력을 보존하기 위해 transactions와 분리했다.

이 설계를 기준으로 다음 범위를 합의하면 구현할 수 있다: 중앙 스키마/수집 역할 담당자 확정 → 기존 PDF 파서의 셀/말소선 생산 구조 개선 → 10개 보관 원문을 결제 없이 재판독하는 공식 구조화 경로 → 스키마/제약/영역별 저장 validator → 마운트 파일 조회 어댑터·인증 링크 → 검증 후 표본 적재. 토지·집합건물과 목록 표본은 별도 추가 열람 범위를 정해 확보한다.

재개 시 이 문서와 `manifest.json`·`structured_samples.json`을 읽고 실제 원격 Git·DB·디스크 상태를 다시 대조한다. 이미 결제한 10건을 다시 검색·결제하여 시작하지 않는다. 현재 샘플의 페이지 기반 근거는 조사에 충분하지만 생산 계약의 행·필드별 bbox/span과 자동 수락 조건은 구현 후 검증해야 한다.

기획은 controlroom의 이 문서가 정본이며 코드와 결합될 실제 CONTEXT/ADR/SQL/테스트는 적용 단계에서 원격 코드 저장소의 기존 결정과 연결한다. GBrain에는 장기 설계 제안과 표본에서 확인한 제약만 기록하고 원문 개인정보·결제 비밀값은 넣지 않는다.

## 10. 표본 충분성 검토와 추가 조사 제안

검토일: 2026-09-17. 주인님 요청은 추가 조사의 필요성 검토다. 아래의 건수·선정 기준은 **제안**이며 신규 유료 열람, 수집 코드 변경, 운영 DB 적용을 실행한 기록이 아니다.

### 판단: 추가 원문 확인이 필요하다

10건은 소유권·담보의 기본 모델을 발견하는 데 유용했다. 복잡한 지분 이전, 신탁 이전·귀속, 채무자 변경, 다수 권리의 일괄 말소와 공동담보 구성원 일부 소멸도 있었다. 그러나 서로 다른 일반 건물 10개를 읽었다는 사실만으로 토지·전유부분·대지권과 목록의 저장 계약이 검증된 것은 아니다.

이번 검토에서 로컬과 마운트 보관본의 `structured_samples.json` SHA-256이 모두 `b51c0e1efc27bf9acb1fa95aad3ef15d630b07bd59e38bafd39f512837d78bf0`임을 다시 확인했다. 같은 자료의 집계와 실제 코드가 판단 근거다.

| 확인 영역 | 기존 표본의 직접 근거 | 아직 확인하지 못한 부분과 영향 |
|---|---|---|
| 물건 유형 | 일반 건물 10개, 토지 0개, 집합건물 전유부분 0개 | 지목·토지 면적 이력, 전유부·1동 건물·대지권의 서로 다른 표제 구조 |
| 물건 사이 연결 | 공동담보에 다른 토지·아파트가 적힌 원문 참조 | 관련 물건의 별도 고유번호·명의자·권리와 실제 일치하는지 미확인 |
| 매매가격 | 매매 취득 17행 중 8행은 매매목록 미수령, 9행은 본문 가격 미기재. 가격 관측 0개 | 숫자로 확인된 가격의 저장·단위·범위·다물건 반복 집계를 실제 사례로 검증하지 못함 |
| 공동담보 | 본문의 목록 번호와 일부 구성원 해제 기록 | 목록 원문과 복수 물건의 권리를 대조한 동일 담보권 식별·중복 제거 |
| 신탁 | C06의 신탁 이전·귀속 2행 | 신탁원부 원문 없음. 위탁자·수탁자·수익자·우선수익자와 변경·금액 조건의 구조화 |
| 취득·권리 변형 | 매매·보존·증여·신탁, 근저당·전세·압류 등 | 상속·경매 취득, 가등기와 본등기, 지상권·지역권, 근저당 금액 변경·일부 이전·말소회복 등의 실제 판독 |
| 자동 판독 | 공식 코드는 텍스트를 세 section과 번호별 원문으로 분리함. C04에는 층수 분리 오류 | 표 칸·여러 표제 subsection·이어진 행·필드별 말소선을 반영한 자동 구조화는 구현 전 |

매매목록이 있으면 본문에 가격 대신 목록 번호를 기록하는 방식이므로, 일반 건물만 더 읽어서는 가격 검증의 빈틈을 계속 남길 수 있다. [부동산등기규칙 제124·125조](https://law.go.kr/LSW/lsLinkCommonInfo.do?chrClsCd=010202&lspttninfSeq=112874)

대지권은 목적 토지의 일련번호·종류·비율과 연결되어 기록된다. 집합건물의 여러 표제 영역을 한 건물의 면적·소유 지분과 같은 값으로 취급하면 물건과 권리를 잘못 연결할 수 있다. [부동산등기규칙 제88조](https://www.law.go.kr/LSW/lsSideInfoP.do?docCls=jo&joBrNo=00&joNo=0088&lsiSeq=266847&urlMode=lsScJoRltInfoR)

신탁원부·공동담보목록·매매목록은 별도 포함 신청이 있는 경우 증명서에 포함하는 자료다. 목록 번호를 발견한 것과 목록 내용을 확보한 것을 구분해야 한다. 한 구분건물의 증명서는 1동의 건물 표제와 해당 전유부분을 함께 담을 수 있으므로 표제 영역의 반복도 정상 입력으로 다뤄야 한다. [부동산등기규칙 제30조](https://www.law.go.kr/lsLinkCommonInfo.do?chrClsCd=010202&lsJoLnkSeq=1026156285)

### 권고 규모: 추가 등기 20개와 목록·원부 6개

회사 수가 아니라 **서로 다른 등기 대상과 확인할 관계**를 센다. 한 회사의 관련 건물·토지·전유부분이 여러 등기 문서로 나뉠 수 있다. 목록·원부는 물건 수에 더하지 않고 원문 자료 수로 관리한다. 첨부가 본문 PDF에 함께 들어오면 별도 PDF 파일이나 별도 유료 신청이 아닐 수 있다.

| 추가 자료 | 목표 수 | 선정 기준 | 이 자료로 검증할 저장 관계 |
|---|---:|---|---|
| 토지 등기 | 10개 | 기존 C01·C02·C04·C06·C14의 관련 토지를 우선 확인하고, 다필지·지목 변경·분할/합병 이력을 가진 토지를 보완 | 건물-토지 연결, 명의자/담보 범위 차이, 지목·면적·전후 물건의 연결 이력 |
| 집합건물 전유부분 등기 | 6개 | 모기지 대상 회사의 정확한 사업장 호실 또는 명시된 매매·공동담보의 관련 호실. 둘 이상의 건물군에서 선정 | 1동 건물·전유부·호실·대지권 목적 토지의 구분, 여러 필지의 대지권, 명시된 대지권 미등기/별도등기 |
| 추가 일반 건물 등기 | 4개 | 신규 신탁, 상속/협의분할, 경매/가등기 본등기, 근저당 금액 변경·권리 일부 이전 등 기존에 없는 변형을 우선 | 취득 원인별 지분 승계, 권리 변경 대상·범위, 일반적인 설정/말소로 환원할 수 없는 사건 |
| 매매목록 | 2개 | C04의 여러 공유자 지분 취득을 참조하는 목록과 C06 등 다른 거래의 목록을 우선 | 계약 전체 가격과 자산/지분별 가격 구분, 거래 구성원, 같은 거래의 가격 1회 집계 |
| 공동담보목록 | 2개 | 다른 물건의 권리와 대조할 수 있는 목록, 구성원 일부 소멸 이력이 있는 목록을 우선 | 같은 담보권 식별, 구성원 이력, 물건별 관측 금액의 중복 집계 방지 |
| 신탁원부 | 2개 | C06의 참조 원부와 다른 신탁 사례의 원부. 변경 내용이 있다면 함께 확인 | 신탁 당사자 역할·수익 구조·기간·조건과 권리 변경 관계 |

이 구성은 **추가 등기 20개와 첨부 원문 6개**를 확인하는 첫 조사 규모다. 기존 10개까지 합치면 등기 대상은 30개다. 전체 모집단의 정확도·유형 비율을 추정할 통계 표본 수가 아니며, 30개라는 숫자로 모든 부동산 변형을 보장하지 않는다.

희귀한 변형이 토지나 집합건물에서 확인되면 일반 건물 4개 몫을 중복 목적으로 채우지 않고 조정한다. 원문을 얻지 못한 유형은 미검증으로 남긴다. 해당 유형을 확보했다고 가정하거나 이름만 다른 비슷한 건물로 빈칸을 채우지 않는다. 후보별 목표 유형·선정 근거·확인 결과·미수령 사유를 기록한다.

기존 열람 단가 700원이 그대로 적용된다는 가정에서 추가 본문 등기 20개는 14,000원이다. 목록·원부의 실제 신청 가능 여부·포함 방식·화면 금액은 아직 확인하지 않았으므로 총액을 확정하지 않는다. 기존 10개 PDF의 재판독에는 새 열람료가 필요하지 않다.

### 조사 순서와 표본 배정

1. **기존 복잡 사례를 연결해 본다.** 관련 토지 5개와 매매목록 2개·공동담보목록 1개·신탁원부 1개를 우선 대상으로 삼는다. 같은 거래와 담보의 다른 면을 확보하면 새 회사만 읽는 것보다 가격 범위·당사자·중복 문제를 직접 확인하기 쉽다. 본문이 새로 필요하면 정확한 고유번호와 실제 열람 조건을 먼저 확정한다.
2. **빠진 유형을 보완한다.** 토지 5개·집합건물 6개·일반 건물 변형 4개와 나머지 공동담보목록 1개·신탁원부 1개를 보완한다. 같은 유형 안에서는 둘 이상의 건물군·서식 이력을 확보하고, 가능한 후보에서 무작위 선정해 특정 익숙한 원문만 고르지 않는다.
3. **설계에 쓰지 않은 자료로 대조한다.** 추가 본문 20개 중 5개(토지 2·집합건물 2·일반 건물 1)는 설계 보완에 원문을 사용하지 않고 남겨 둔다. 나머지 자료로 정리한 모델이 이 5개의 실제 사실·관계·누락 상태를 담을 수 있는지 확인한다. 5개에서 새 핵심 관계가 발견되면 설계를 보완하고, 이후 미사용 자료로 다시 확인할 범위를 정한다.

목록 원문을 받은 후 관련 물건을 정확히 식별할 수 있다면 그 물건을 토지/전유부분 몫에서 우선 선정한다. 공동담보 목록에 있다는 사실만으로 회사 소유나 실제 채무를 확정하지 않는다. 주소 무결과·복수 일치·주소 아닌 값은 기존 5개 제외 사례처럼 무결제 선택 실패로 보존한다.

### 논리 모델에서 먼저 재검토할 부분

아래는 원문 확인 후 확정할 설계 항목이다. 이번 검토에서 새 테이블을 추가하거나 23개 논리 테이블을 운영 스키마로 고정하지 않는다.

| 재검토 항목 | 현재 제안의 한계 | 추가 원문에서 확인할 내용 |
|---|---|---|
| 토지-건물-전유부분 연결 | `parent_building_id`와 주소만으로 다필지·다건물 연결을 표현할 수 있는지 검증 전 | 관계마다 대상 물건·관계 종류·적용 범위·관측/변경 근거를 여러 행으로 보존할 필요. 같은 지번이라는 이유로 자동 연결하지 않음 |
| 여러 필지의 대지권 | `property_descriptions`에 제안한 대지권 종류/비율만으로는 어느 목적 토지의 권리인지 명확하지 않음 | 목적 토지의 문서 내 일련번호·원문 참조·확인된 토지 UID·종류·정확한 비율·변경 이력의 대응. 여러 토지를 한 비율로 덮어쓰지 않음 |
| 1동 건물의 정체성 | 전유부분의 부모 FK가 별도 등기 고유번호를 가진 일반 건물이라고 전제하면 잘못 연결할 수 있음 | 1동 표제의 공통 건물 표시와 독립 등기 대상의 구별. 확인되지 않은 부모 등기 UID를 생성하지 않음 |
| 분할·합병·폐쇄/이기·경정 | 문서/표제 이력 보존은 있으나 전후 물건·사건 연결의 실제 계약은 미검증 | 이전과 이후 대상, 연결 원인과 날짜, 원문 참조와 확인된 UID. 단순 지번 변경과 자산 분리를 구분 |
| 신탁 내용 | 본문 당사자 표기와 범용 권리 역할만으로 원부의 수익자·우선수익자·변경 조건을 충분히 담는지 미검증 | 당사자의 역할·적용 기간·권한/금액 조건과 개정 원부 연결. 우선수익 금액을 근저당 최고액이나 실제 잔액으로 바꾸지 않음 |
| 권리와 사건의 분류 | `other` 원문 보존은 가능해도 중요한 변형의 분석 필드·현재 상태 계산은 검증 전 | 가등기 본등기·경매·지상권·지역권·금액 변경·일부 이전·말소회복을 기존 설정/말소 관계로 충분히 표현할 수 있는지 확인 |
| 문서 범위와 완전성 | 건물 10개의 세 section 계약만으로 집합건물의 여러 표제 영역을 판정할 수 없음 | 토지/일반 건물/집합건물/목록/원부별 필수 영역과 명시된 공란·미등기·접수 처리 중 표시를 구분 |

### 조사 종료와 설계 확정의 기준

건수 달성만으로 끝내지 않는다. 다음 조건을 함께 확인해야 물리 DB 설계를 확정할 근거가 생긴다.

- 토지·일반 건물·집합건물의 실제 원문을 확보하고, 우선 지원할 주요 관계는 서로 다른 실제 사례 2개 이상으로 확인한다. 다필지 대지권이나 희귀 권리 변형을 확보하지 못하면 그 유형은 지원 범위에서 미검증으로 표시한다.
- 매매가격이 숫자로 기재된 원문 사례와 다물건/지분 거래의 가격 범위를 확인한다. 가격을 얻지 못하면 가격 적재·중복 집계 계약이 검증됐다고 판정하지 않는다.
- 복수 물건의 공동담보를 목록 원문과 등기 사건으로 대조한다. 신탁원부도 본문의 번호·당사자·변경 이력과 대조한다. 미해결 구성원이 있는 정확한 포트폴리오 합계는 생성하지 않는다.
- 대상 UID, 금액 종류·통화, 지분, 원인/접수 날짜, 당사자 역할, 말소·부분 변경의 대상과 범위가 원문 근거와 맞는다. 핵심 값의 오류를 평균 정확도 점수로 상쇄하지 않는다.
- 문서/판독 버전, 같은 거래의 여러 관측, 공동담보와 당사자의 여러 역할을 함께 조회해도 가격·최고액이 중복되지 않는다. 같은 금액인 서로 다른 권리를 제거하지 않는다.
- 설계에 쓰지 않은 마지막 5개 본문을 구조화했을 때 새 핵심 개체·관계나 기존 필드 의미의 변경 없이 실제 사실과 미확인 상태를 담을 수 있다. 이것은 제한된 표본에서의 안정성 근거이며 전체 변형에 대한 보증은 아니다.
- 보관 10개 PDF와 추가 원문을 공식 자동 추출 경로로 재판독해 같은 계약을 검증할 수 있다. **원문 조사·수작업 구조화가 잘 된 것과 자동 추출·DB 적재가 잘 되는 것은 다른 완료 조건**이다. 자동 경로의 최종 검증은 구현 후 수행한다.

지원 범위 밖 변형은 원본·원문·식별/판독 상태를 보존하고 미해결 영역의 분석값 확정만 보류한다. 새 변형을 일반 매매·대출·전체 말소로 강제로 해석하거나 추출 실패를 금액 0으로 저장하지 않는다.

IROS 원문을 추가로 읽어도 실제 대출 잔액·금리·만기가 자동으로 확보되는 것은 아니다. 그 분석은 별도의 금융 자료를 확인하는 후속 범위다. 이번 추가 조사 목표는 **등기에서 확인할 수 있는 사실과 연결 관계를 정확히 저장할 모델을 검증하는 것**이다.

### 이번 검토의 변경·검증과 재개 정보

- 변경 범위: 이 설계 문서의 충분성 검토·표본 계획, `iros-model/CONTEXT.md`의 물건 연결/대지권 용어, 프로젝트 문서 색인만 보완한다. 새 수집·적재 코드·DDL·권한·예약 작업·배포·유료 조회는 실행하지 않는다.
- 수정 전 기준선: 대상 문서에 기존 diff/staging 없음. 별도 운영서버 통합 문서의 사용자 변경은 작업 범위 밖으로 보존. 코드 정본은 clean 상태의 main `e9c013929378815c7294f52c9e76c330ef285ce9`이고 GitHub main과 일치했다.
- 최소 구현 게이트: 2단계에서 멈춤. 기존 표본·설계·용어·문서 색인을 재사용하며 수집 도구나 분석 프로그램을 추가하지 않는다. 확인 검색은 `parse_registry_text`, `parse_registry_pdf`, `대지권`, `공동담보`, `매매목록`, `신탁원부`다.
- 수정 후 확인: 같은 JSON의 일반 건물10/매매17행/가격 상태8+9 집계, 로컬·마운트 SHA-256 일치, 23개 기존 논리 테이블 보존, 추가 본문20/첨부6 수량, 문서 링크3개·diff 검사를 확인했다. 원격 코드의 clean 상태와 기존 HEAD, 범위 밖 통합 문서의 SHA-256도 보존됐다. 이 문서 검증으로 자동 판독 정확도나 운영 DB 적용을 통과 처리하지 않는다.
- 다음 행동: 추가 조사 범위를 진행하게 되면 먼저 기존 사례의 관련 토지와 참조 목록·원부의 실제 선택·신청 가능 여부·비용을 확인한다. 기존 PDF를 다시 결제하지 않고 재사용한다. 이번 검토의 제안만으로 새 20개 등기와 6개 첨부를 자동 결제하지 않는다.

## 11. 승인된 추가 조사 실행과 재개 정보

2026-09-17 주인님이 10절의 추가 등기20개·목록/원부6개 제안에 "OK 진행해"라고 승인했다. 이 절이 10절의 추가 조사 미승인 상태를 대체한다. 10절의 조사 목적·선정·종료 기준은 유지한다.

- 실행 목표: 기존 복잡 사례의 관련 토지·목록을 먼저 확인하고 토지10/집합건물6/새 변형 일반 건물4와 매매목록2/공동담보목록2/신탁원부2를 확보한다. 유형이 겹치면 불필요한 중복을 줄이고 확인하지 못한 유형은 사유를 남긴다. 마지막 본문5개는 설계 보완에 쓰지 않고 대조한다.
- 승인된 효과: 필요한 IROS 열람·선불 결제·PDF 수령, 전용 마운트 원본 보관, 조사용 구조화, 실제 원문에 따른 논리 모델 보완. 신청마다 정확한 고유번호·종류·개수·화면 금액을 확인한다. 기존 단가700원의 신청은 최대26회/18,200원으로 실행 상한을 두며 첨부 포함으로 줄어든 비용을 기록한다. 단가가 다르면 금액/포함 방식의 근거부터 확인한다.
- 변경 경계: 기존 공식 `scripts/iros_dom.py`·`iros_ssp.py`에서 추가 자료 수집에 필요한 기능과 직접 테스트만 보완할 수 있다. 브라우저 수명주기는 shared HiddenBrowser를 재사용한다. 운영 DB 스키마·역할·적재, 웹 배포·문자·예약 작업·기존자료 삭제는 이번 조사 범위에 포함하지 않는다.
- 수정 전 기준선: 원격 main `e9c013929378815c7294f52c9e76c330ef285ce9`, clean, GitHub main과 일치. Windows 설치본의 두 IROS 파일 SHA-256은 정본과 일치. 공식 관련 pytest78개가 통과했다. 전용 IROS Chrome 잔여 PID는0이다. 다른 controlroom 문서의 기존 변경은 보존한다.
- 최소 구현 게이트: 2단계에서 멈춤. 공식 실행기·기존 DesktopObserver·선불 결제/PDF 저장·기존 표본 파일과 설치된 PDF 도구를 재사용한다. 검색/추가사항/목록 선택 기능은 실제 화면을 조사한 뒤 필요한 경우 해당 공식 단계에 통합한다. 새 브라우저/결제 runner나 운영 DB 적재 코드는 만들지 않는다.
- 작업본: `C:\\iros-agent\\studies\\20260917_expand20_model\\`. 보관 정본: 기존 DB 서버 `/mnt/ceoloan/registry/studies/20260917_expand20_model/`. 원본은 기존 content-addressed original 경로를 재사용한다. 회사/개인정보가 포함된 원문·JSON은 Git/GBrain에 넣지 않는다.
- 경로/검증: 원격 공식 코드 확인 → Windows 동일 설치본 → 숨은 Chrome 검색·선택·추가사항·결제전 확인 → 승인 범위 결제·PDF → 원본 해시/마운트 → 원문 화면·표 구조와 사실 대조 → 조사용 구조화/모델 보완. 결제 완료·수령 실패는 기존 view-only로 재개하고 재결제하지 않는다. 입력 데스크톱과 도구 Chrome 전경 전환·잔여 PID를 별도로 확인한다.
- 현재 위치: 수집과 원문 판독 완료. 조사 JSON·최종 필드 계약·보관 해시와 코드 리뷰 결과를 정리한다. 운영 적용은 후속 단계다.


### 추가 수집 경로 보완 및 코드 리뷰 계약

- 원천: 주인님의 추가 등기20개·첨부6개 승인과 이 절의 범위, 기존 공식 IROS 실행기 계약.
- 역할: 기존 숨은 Chrome에서 확인한 토지/건물/호실을 선택하고, 요청한 목록이 포함된 신청을 결제해 원문을 수령한다. 의미 판독·운영 적재는 이 코드의 책임이 아니다.
- 리뷰 경계: base `e9c013929378815c7294f52c9e76c330ef285ce9`와 원격 작업트리의 `scripts/iros_dom.py`, `iros_ssp.py`, 두 직접 테스트. CLI→DomRunner→match_result_row→기존 PDF parser/summary의 직접 계약을 확인한다.
- 입력: 기존 회사 주소와 실제 IROS 행에서 확인한 고유번호/종류; 선택한 공동담보·매매·영구보존 목록. 추가 인증은 중단하고 원문 비밀값을 기록하지 않는다.
- 절차: 기존 로그인/검색/신청/개인정보 미공개/결제/PDF 경로를 유지한다. WebSquare 처리 모달이 끝나야 단계 완료로 판단한다. 개별 목록은 실제 대상 UID와 맞는 행만 선택한다.
- 출력: 신청/선택 목록번호·결제 결과·PDF·고유번호/세 section 검사 결과와 실패 단계를 summary로 남긴다. 실제 목록 본문 수령은 조사에서 별도 대조한다.
- 보호: 기존 78개 pytest 기대값과 브라우저 소유권/정리, 정확한 주소 경계, 1건700원, 기존 파일/자료/인증/서비스/DB 권한을 보존한다.
- 비목표: 운영 DB/DDL/역할/배포/스케줄/금융 자료 연결·기존 C04 의미 파서 오류·생산 완전성 승인. 기본 구조 검사만으로 의미 정확성을 주장하지 않는다.
- 근거: 원격 diff와 두 직접 테스트, 공식 preflight/paid/view-only summary 및 실제 PDF. 기본 관점은 변경 diff와 직접 호출/소비자이고, 실제 IROS 신청/선택/페이지 계약도 대조한다.

2026-09-17 첫 첨부 신청은 목록 행을 선택했으나 결제대상 첫 페이지의 이전 신청을 선택해, 첨부 없는 기존 물건의 PDF만 수령했다. 실제 비용700원과 PDF6쪽을 보존하며 첨부 수령으로 집계하지 않는다. 결제대상은 10행씩 여러 페이지이고 새 신청은 마지막에 추가됐다. 이 사실에 따라 `pay`를 전체 페이지/건수 대조→기존 선택 해제→이번 신청의 마지막 행 UID/종류 확인→1건700원 검사로 보완한다. 기존 신청은 삭제하지 않는다. 이 경로로 새 첨부 PDF가 확인돼야 첨부 수집 성공이다.

### 최종 실행 결과

- 기존78개 검사를 보존하고23개를 추가한101개가 통과했다. 루트 에이전트가 고정된 리뷰 계약으로4파일 전체 diff와 직접 호출/소비자를 검토했으며 승인된 finding과 열린 material contract question은 없었다.
- 추가 물건20개=토지10·집합건물6·건물4, 연결 원천회사19개, 고유번호20개는 기존10개와 중복되지 않는다. 회사 주소 연결이며 회사 소유 확인값은 아니다.
- 실제 PDF24개/191쪽:20본문114쪽, 추가 재열람4파일77쪽. 이 중 A01은 이전 신청 선택으로 받은 첨부 없는6쪽 문서여서 성공 첨부로 집계하지 않는다.
- 원문으로 확인한 논리 첨부14개=매매목록8·공동담보목록3·신탁원부3. 반복 인쇄된 같은 목록은1개로 센다. 첨부는 본문에 포함된 것도 있어14개의 별도 PDF나 추가 결제를 뜻하지 않는다.
- 영수증이 확인된 유료 신청24회, 추가16,800원. 이전 신청 선택으로 지출된700원을 포함해 보존한다. 기존10회7,000원과 합계23,800원. 승인 상한26회/18,200원 이내다.
- PDF 저장 실패4대상(L05/U01/U02/T01)은 기존 결제의 view-only에서 수령했다. T01 보안 프로그램 안내 뒤에도 설치·보안 설정을 변경하지 않고 기존 신청의 공식 재열람에서 수령했다.
- 보류5개는32테이블 모델과15개 판독의 파일/해시를 동결한 후 확인했다. 원래 모델을 수정 없이 통과시킨 것은 아니다.13절의 실제 공백을 보완한v2.1을 같은5개에 재대조했고 새로운 독립 보류 표본은 남아 있지 않다.
-20개의 현재 소유 지분 합계는 모두1이며 숫자/날짜/권리 관계를 원문에 대조했다. 근저당·가압류·전세금·우선수익 한도·계약가격의 금액 종류를 분리했다.
- 마운트 원본의 SHA-256과 수령 파일 해시를24건 대조했다. 입력 데스크톱 Default 전후, 공식 호출의 도구 Chrome 전경 이벤트0·호출후 소유 Chrome PID0을 monitor로 확인했다. 일반 조사 probe 전부에 같은 관측이 있었던 것으로 확대하지 않는다.

### 재개 정보

공식 수집 코드 변경은 원격 main `864420e`로 저장하고 GitHub ceoloan/main에 push했다. Windows 실행본 두 파일은 같은 SHA-256이다. 제품 웹 배포는 실행하지 않았다.

조사/모델 보완 결과는 최종 v2.1이다. 다음 단계는 승인된 스키마/수집 역할/적재 transaction 및 자동 의미 판독의 구현 계획이다. 본 조사에서는 운영 DB·권한·웹 서비스·배포를 바꾸지 않았다. 변형 검증은 담보권 피담보채권 제한·등기기록 이기·건물만 담보·공동1순위 신탁을 우선한다. 일반 무작위20건 반복보다 확인한 위험별 검증 사례와 독립 검증 표본을 확보한다.

## 12. 추가 원문으로 보완한 저장 모델

추가20물건과 실제 목록·스캔 신탁원부에서 확인한 필드는4절의32개 논리 테이블에 통합했다. 최초23개에서 문서구성·물건관계·대지권·신탁9개를 추가했다. 회사 정보는 company.companies 참조를 유지하고 원본/판독 사실은 중앙 real_estate 저장 소유를 제안한다.

- 집합건물의 반복 표제부·1동/전유부/목적 토지를 분리했고 별도 고유번호 없는1동 설명을 가짜 부모 물건으로 만들지 않는다.
- 동일 순위 아래 가등기와 본등기를 분리하고 임의의 순위번호 UNIQUE를 제거했다. 근저당 목적에 대지권이 추가되는 명시 사건은 동일 담보 관계로 연결한다.
- 표제 이력의 분할970→433㎡와 신규537㎡ 참조, 별도 등록된3층 부분, 반복49.16㎡ 문구를 보존한다.
- 매매목록 가격은 계약 전체 값으로1회 보존한다.65억원이라는 같은 금액의 서로 다른2021·2023계약을 합치지 않는다.
- 64.2억원 동일 공동담보권이 건물1·토지2에 반복됨을 목록으로 확인했다.19,260,000,000원을 대출액으로 합산하지 않는다. 나머지2물건 본문 미확인이라 전체 포트폴리오 완전성은 미확인이다.
- 신탁원부3개를 판독했다. 같은2021년 당사자·조건·12억원 한도의 토지/건물 원부2개도 담보재산·원부번호가 다르다. 계약 이미지23쪽 중19쪽이 같고4쪽이 다르지만 실제 동일 피담보채권 식별은 미확인이다. 서로 다른 실제 대출2건으로 세거나 금액을 무조건 합산하지 않는다.
- 현재2025년 신탁은 수탁은행1곳과 공동1순위 우선수익기관3곳이다. 기관별 한도34.8/14.4/21.6억원, 합계70.8억원은 해당 신탁의 우선수익 한도 관측일 뿐 실제 잔액이 아니다. 고정 신탁기간·자동 연장·기관별 비용 부담·처분비 공식도 따로 보존했다.
- 스캔 신탁의 계약 분석 핵심 항목은 원문 화면으로 판독했다. 스캔 본문은 PDF 텍스트층이 없으며 자동 OCR·전 조항 전사·필드좌표 의미 검증 완료를 주장하지 않는다.
- 원문 텍스트층과 화면의 은행명 불일치, 기존/작업중 판독의 이름·날짜·금액 오타를 발견해 정정 관측으로 기록했다. 이전10건·모델 동결15건은 보존한다.
- 실제 영수증 승인 시각과 신청목록/재열람 표시시각을 구분했다. 저장 실패4건은 공식 view-only로 재개했고 재결제하지 않았다.

운영 자동 의미 추출기, 필드 단위 좌표 validator, 중앙 DB 마이그레이션·전용 수집 역할·원자적 적재, 인증 다운로드 엔드포인트는 아직 구현하지 않았다. 조사 결과의 완성을 운영 자동 적재 경로의 완성으로 판정하지 않는다.

## 13. 보류 표본 대조와 v2.1 보완

비보류15개와 논리 테이블32개의 모델을 `model_spec_v2_frozen.md` 및 `model_contract_v2.json`으로 고정하고 해시·시각을 남긴 뒤 L09/L10/U05/U06/B04의 본문23쪽을 열었다. 이 기록은 기계 검증용 JSON Schema나 운영 DDL이 아니다. **고정 v2가 변경 없이 모든 보류 표본을 수용했다는 종료 조건은 충족하지 못했다.** 새 핵심 테이블은 필요하지 않았으나 아래 관계·분석 필드를 추가해야 했다.

| 표본 | 실제 확인한 내용 | 기존 모델과 보완 |
|---|---|---|
| L09 | 기존1/14+6/14가 남고 나중에1/2을 받아 현재1/1. 금액·은행·날짜가 같은 설정2개는 접수번호가 다름 | 기존 지분 누적·사건 식별·한 말소→복수 권리로 표현 가능 |
| L10 | 근저당권부채권의 가처분. 분할로 이전 등기에서 전사된 담보의 원래 설정 접수와 전사 접수가 다름 | 채권 대상 가처분 관계와 전사 출처를 추가 |
| U05 | 보존만 있고 을구는 명시적으로 기록사항 없음. 목적 토지와 대지권 비율 별도 | 기존 전유부분/대지권/확인된0건 계약으로 표현 가능 |
| U06 | 대지권이2022년에 기록됐지만2017년 근저당은 '건물만에 관한 것임' | 원문 범위 보존 외에 분석용 담보 범위·범위 명시 부기 종류를 추가 |
| B04 | 등기기록 과다로2023년에 이기. 목록의 옛44번과 현재2번은 같은 본건 담보의 연속. 근저당4개는 모두 말소됐지만 현재 신탁등기 존재 | 등기기록 연속·목록 구성원 승계·제한된 이력 범위를 명시. 신탁원부 별도 확보·대조 |

v2.1의 추가 계약:

- `entry_relations.relation_kind`에 `encumbers_secured_claim`, `transcribed_from_prior_register`, `continues_registered_right`를 추가한다. `target_scope`에 `secured_claim`을 추가해 L10의 가처분 항목→근저당 설정 항목을 연결한다. 부동산 자체의 가처분과 구분한다. 이전 기록을 실제로 수령하지 못한 관계는 `to_entry_id NULL`, `target_reference_raw NOT NULL`, `resolution_status=unresolved_prior_register`로 보존하며 이전 항목 UUID를 만들지 않는다.
- 분할 전사는 원래 `rights.setup_cause_date/setup_receipt_date`를 유지하고 별도 `registry_entries.subrecord_kind=split_transcription`에 전사 접수일/번호·원문 순서·근거를 저장한다. 전사 접수를 새 담보 설정이나 새 대출로 세지 않는다. `property_relations`의 실제 분할 참조와 연결한다.
- `rights.registered_object_scope`에 `whole_property/ownership_share/building_only/land_right_only/unit_and_land_right/secured_claim/unknown`을 둔다. `right_changes.change_kind=scope_clarification`은 명시된 범위 부기와 관측일을 저장하며 금액 변경이나 새 대출로 만들지 않는다. 과거 적용 범위가 원문에서 확인되지 않으면 소급해 단정하지 않는다.
- `property_relations.relation_kind=register_continuation`, `reference_role=prior_register/current_register`, `record_transcription_date`, `record_transcription_reason_raw`를 추가한다. 이전 등기 UID가 없으면 NULL과 원문 참조를 보존한다. 물리 필지 분할과 다른 관계다. `registry_documents.history_coverage=transcribed_subset`, `history_cutoff_reason_raw`로 B04의 보존 범위를 표시하며 이 문서의2개 취득을 물건의 전체 취득 이력으로 보고하지 않는다.
- `collateral_members`에 `member_ordinal_raw`, `predecessor_member_observation_id nullable`, `change_kind_raw`, `member_scope_kind/member_scope_raw`를 추가한다. 같은 목록 안의 B04구성원1→7을 연결하고 이기로 옮겨진 상태와 해지를 구분한다. 행7개·물건 참조6종·확인된 UID1개를 각각 집계한다. 옛 행의 말소선만 보고 본건 담보가2023년에 끝났다고 판단하지 않는다.
- 계산된 취득 지분은 `ownership_interests.share_resolution_status=calculated_from_verified_transferors`와 계산식·근거를 보존한다. L10의 최종 '소유자' 기록은 기존992/3306을 남기고 다른 두 공유자의2314/3306을 취득한 결과다. 원문이 취득 지분1/1을 직접 적었다고 저장하지 않는다.

v2.1은 이5개를 다시 대조해 사실을 표현하도록 보완한 모델이다. 보완 후의 **새로운 독립 보류 표본**으로 일반성이 검증된 것은 아니다. 근저당권부채권 가처분·기록 이기·건물만 담보 범위는 이번 조사에서 각각1개 실제 사례이므로 해당 변형의 자동 적재 승인은 추가 표적 검증을 필요로 한다. 다필지 대지권, 외화 담보, 말소회복·경정의 복잡한 연쇄, 여러 수익순위·증서의 신탁 변경은 아직 지원 검증 범위 밖이다.
