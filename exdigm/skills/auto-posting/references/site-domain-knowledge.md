# Site Domain Knowledge (필수 정보만)

사이트별 레거시 스킬 6개(jobkorea, saramin, peoplenjob, businesspeople, incruit, exdigm-homepage)를 2026-07-09에 점검·증류 후 삭제하고, 코드에 없는 필수 정보만 여기 남겼다. 재생성하지 않는다.

권위 순서: `sites/<site>.py` 코드 → `site_maps/<site>/field-map.json`(entrypoints, auth, field_groups, actions, stop_conditions, unresolved_controls 보유) → 이 문서. 이 문서와 코드가 다르면 코드가 이기고 이 문서를 갱신한다.

셀렉터·진입 URL·로그인 폼·필드 채우기·에디터 처리(비즈니스피플 Namo `_set_namo`, 엑스다임 SmartEditor `SET_IR`)·사람인 2FA 메일 매칭·test 모드 삭제 정리는 모두 코드에 구현되어 있으므로 여기 반복하지 않는다.

## 자격증명 env 변수 (`auto_posting/.env`)

| Site | 변수 |
| --- | --- |
| jobkorea | `JOBKOREA_URL/ID/PW` |
| saramin | `SARAMIN_URL/ID/PW`, `SARAMIN_CERT_PHONE` |
| peoplenjob | `PEOPLENJOB_URL/ID/PW` |
| businesspeople | `BUSINESSPEOPLE_URL/ID/PW` |
| incruit | `INCRUIT_URL/ID/PW` |
| exdigm | `EXDIGM_HOMEPAGE_URL/ID/PW` |

## 공고 관리(읽기/검증) URL

posting 경로 밖에서 게시 결과를 눈으로 확인할 때 쓴다.

- jobkorea: `https://www.jobkorea.co.kr/Corp/GiMng/List`
- saramin: `https://hiring.saramin.co.kr/recruit`
- peoplenjob: `https://www.peoplenjob.com/headhunting/jobs`
- businesspeople: `https://www.bzpp.co.kr/hire/recruithome?flLanding=Y`
- incruit: `https://recruiter.incruit.com/jobpost/jobpostmng.asp`
- exdigm: `http://www.exdigm.com/bbs/board.php?bo_table=position`

## 2FA 사실 (2026-07-10 실측 갱신)

- **사람인**: 상시 2FA 존재, 코드 구현 완료.
- **잡코리아**: 상시 2FA는 없다(주인님 확정, 데스크탑 신뢰 기기에서는 안 뜸). 단 **새 기기/브라우저**로 개인정보 조회 페이지(공고등록 포함)에 접근하면 **신규 기기 인증**(TwoFactorAuth)이 1회 뜬다. 코드가 이메일 인증으로 자동 통과한다(`_pass_new_device_2fa`: 이메일 인증 탭 → 가입자 대표 선택(`button.dev-auth[data-register="true"]`, ceo@exdigm.com) → `#btnSendCert` 발송 → IMAP 코드 조회 → `#certNum` 입력 → `#btnCheckCert`). 통과하면 영속 브라우저 프로필이 신뢰 기기로 등록되어 이후 재인증 없음 — **공유 브라우저 프로필(`runtime/auto_posting/browser-profile`)을 지우면 인증이 다시 발생**하므로 지우지 않는다.
- 잡코리아 계정은 서치펌(`서치펌`) 타입으로 로그인한다. **로그인·공고등록 URL 직행은 봇 플래그**(jkConfirm 보안문자 차단)를 유발한다 — 반드시 사람 경로: `Corp/Index` 진입 → 로그인 버튼 클릭 → `#devpopCorpLogin` iframe(요소 id로 접근), 등록은 홈에서 공고등록 메뉴(`li.devRecruit > a`, `.active-fixed`는 스크롤 상태 클래스라 셀렉터에 넣지 않음) 클릭. 차단이 걸리면 `autoposting --site jobkorea --action captcha`로 화면 캡처 → 에이전트가 판독 → `--code`로 제출.

## 사이트별 함정 (코드 확장 시 주의)

- **미입력 필드는 사이트가 기본값으로 채운다** (2026-07-09 사고): 근무지를 입력하지 않으면 사람인·인크루트가 계정 주소(엑스다임 강남)와 재택근무 태그로 자동 표기했다. dry는 "입력한 필드"만 검증하므로 게시 후 공개 페이지 대조가 필수다.
- **공개 텍스트는 posting_text에서만**: 사람인 자격요건이 requirements 직역이라 고객사명("데상트")이 노출됐다. `_posting_text_section(body, "자격요건")`으로 단일화됨. requirements를 게시 텍스트에 직접 조립하지 않는다.
- **학력 계약**: `education_preference`는 채용 사이트에 입력할 최소 학력만 담고, 전공은 `education_fields`에만 담는다. JD에 최소 학력이 없으면 제품 정책상 `학사 이상`을 적용한다. JD에 학력무관이나 다른 최소 학력이 명시됐으면 그 값을 보존한다.
- saramin 해외 근무지: `해외지역` 체크 → 국가 콤보에서 선택(라벨은 **"중국.홍콩"**) → 상세 주소 입력. 국가를 고르기 전엔 주소 입력이 잠긴다. OptionList 컨테이너가 콤보박스마다 하나씩 있고 대부분 숨김이라 **보이는 것만** 스코프해야 하며, 국가 목록(236개)은 가상 스크롤이다. `재택근무 가능`은 해제한다.
- incruit 해외 근무지: `fn_RegionSelectLayer_Open()` → `InitRegionLayer()`(회사 주소 기반 기존 선택 초기화) → 국가 체크(`rgn_cd`, 라벨 **"중국"**) → **상세 도시 체크(`rgn_det`, 예 "상하이")** → `ApplyRegionLayer()`. 국가만 체크하면 등록되지 않는다(상세가 진짜 선택). 검증은 `#divSelectedRegion ul`의 칩으로 하고, 화면 상단 "근무지역 서울특별시>강남구"는 회사 주소 라벨이라 무시한다.
- saramin: 2FA는 반드시 `등록된 이메일로 인증` 선택 후 전화번호 확인(11자리 3-4-4 분할) 순서 — 주인님이 직접 교정한 순서다. 브라우저는 시스템 Chrome 선호(번들 Chromium이 307 리다이렉트 후 로그인 폼 렌더 불안정 이력). **직무 선택 모달**: 실측 분류표 SSOT는 `site_maps/saramin/job-category-options.json`(21카테고리/2,176아이템), LLM이 category+labels를 verbatim 선택(`_saramin_job_selection`, 멤버십 검증+재시도). 모달 안에 같은 텍스트의 추천/칩 버튼이 있어 카테고리 클릭은 반드시 `[class*="left-menu"]` 스코프로 해야 하고, 성공 판정은 클릭이 아니라 패널 전환(목표 라벨 가시화)으로 한다. **학력·급여 콤보박스**는 DOM `click()`이 선택 이벤트를 확정하지 못하므로 Playwright 포인터 클릭을 사용하고, 클릭 뒤 같은 콤보박스 표시값이 목표 라벨과 일치해야 성공이다.
- peoplenjob: 로그인 폼에 숨은 중복 input이 있고, 페이지에 '로그인' 텍스트가 여러 개라 **비밀번호 필드가 속한 폼 안의 제출 버튼만** 클릭한다(코드 구현 완료). `헤드헌팅 회원 서비스 개편` 공지 레이어가 남을 수 있다. **공고 등록은 유료 헤드헌팅 멤버십 필요** — 2026-07-09 만료 확인("채용공고 등록은 유료 헤드헌팅 서비스 이용회원에게 제공"), 재구매 전까지 게시 불가.
- businesspeople: 상세요강은 숨은 `textarea#textWorkdetail` 직접 fill 금지 — Namo 에디터 경유(코드 `_set_namo` 구현 완료). 로그인 후 `하루 동안 보지 않기` 공지 레이어 가능. 업종/직종 레이어는 **depth1(대분류) 클릭 → depth2-box(하위 아이템)** 구조다. 수확 시 반드시 `.depth1-box`/`.depth2-box`로 스코프해야 한다(그러지 않으면 태그 영역을 잘못 긁어 IT 카테고리가 1개만 잡히는 등 데이터 결손 발생 — 2026-07-09 실제 사고). 실측 트리 SSOT: `industry-options.json`(10/211), `job-options.json`(19/460) — LLM이 main+details를 verbatim 선택(`_businesspeople_selection`) + **직종 시맨틱 게이트**(직종=본질, 정보보안팀장을 총무/법무/사무로 오분류하는 것 차단, IT/[IT보안]으로 교정). 폴백 기본값은 삭제됨.
- incruit: 로그인 시 `기업회원` 탭 선택, `새로운 기기 로그인 안내`는 `등록안함`. 학력·업종 실측 라벨 기반 LLM 매핑(`INCRUIT_EDUCATION_OPTIONS` 6종, `industry-options.json` 15종). **학력=본질**: 공통 학력 계약으로 확정한 최소 학력을 정확한 사이트 라벨로 매핑하고, 불명확 라벨은 실패. **업종=부수**: 확정 못하면 빈 값으로 두고 게시 막지 않음. 학력 매핑은 워커(LLM), 엔진은 payload의 `education_label`을 클릭만.
- jobkorea: 숨은 라디오/체크박스는 label 클릭(`label[for=...]`)으로 처리한다(코드 구현 완료). 구조화 필드 실측 SSOT: 직무 `job-function-options.json`, 핵심역량 `core-competency-options.json`, **근무지역 `region-options.json`(27그룹/605개)**, 학력·기업형태는 코드 상수. 근무지역은 구인 요청 본질이라 option_id+option_label을 실측과 대조해 엄격 검증한다(불일치 시 재요청). 직무는 시맨틱 게이트까지. 2026-07-09 publish 성공(공고번호 49552064).
- exdigm(홈페이지): **공개 게시판이므로 Company 필드는 실제 고객사명이 아니라 익명 설명**("국내 제약, 바이오 대기업" 패턴)이다. 워커가 LLM으로 익명 설명을 생성하고(`_exdigm_company_descriptor`), 고객사명 포함 여부를 기계 검증한다. `requirements.exdigm_company_descriptor`로 사전 지정 가능. client.name을 그대로 넣으면 고객사 노출 사고다.

## 폐기된 접근 (재시도 금지)

- incruit 404: `/recruitmanage/recruitlist.asp`, `/jobpost/jobpost.asp` — 공고관리는 `jobpostmng.asp`가 맞다.
- exdigm 404: `https://www.exdigm.com/admin/`, `/admin/login/` — 어드민 로그인은 `bbs/login.php?url=...%2Fadm`이 맞다.
- 잡코리아 통합(일반기업) 로그인 페이지 — 이 계정은 서치펌 로그인만 성공한다.

## 히스토리 증거

- 최단 경로 검증: `docs/자료/site-shortest-routes-2026-06-25/`
- payload dry-run 증거: `docs/자료/site-payload-dryrun-2026-06-25/`
- 당시 필드별 confirmed/needs_mapping 상태는 현재 `sites/<site>.py` 구현으로 대체됨.
