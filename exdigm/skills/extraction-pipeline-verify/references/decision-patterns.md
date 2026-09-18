# 결함 패턴과 해결

영구 수정된 패턴 + 미해결 한계 + 진단 매트릭스.

## 영구 수정된 결함 패턴

### docx field code 텍스트 누출

`INCLUDEPICTURE`, `MERGEFIELD`, `HYPERLINK` 등 Word field-code가 추출 텍스트에 그대로 남아 LLM 입력으로 흘러감 → 후보자 이름·값으로 오인 위험.

**수정 위치**: `sanitizers.py::sanitize_input_text` `_FIELD_CODE` + `_HEX_BLOB` 정규식.

### 생년 정규식이 한국어 표준 표기 못 잡음

`1981년 1월 9일생` 형식은 매치 실패해서 1981년 출생자가 SKIP됨.

**수정 위치**: `text.py::extract_birth_year_from_text` patterns 배열.

추가 정책: 검출 실패 시 **PASS** (false negative 회피). 파일명 보조(`parse_filename`)는 한국어 이름 토큰이 있어야 동작.

### 파일명 separator 한정

`김영덕-56 충남대` 같은 공백 separator, `강병배(SK)68,한양대` 같은 comma+괄호 직접 인접.

**수정 위치**: `filename.py::_split_tokens` separator 확장 + 괄호 expand 시 양쪽 dot 추가.

### 자기소개 압축이 학력/경력 섹션 잘라먹음

self-intro 헤더(About Me 등) 발견 후 STRUCTURED 헤더(Education/Career/Skills/...)로 종료 안 하면 정형 섹션이 통째로 사라짐.

**수정 위치**: `text.py::_compress_self_intro_region` + `_STRUCTURED_SECTION_HEADER` 정규식.

`_FORM_LABEL_ONLY`에서 STRUCTURED 키워드 빼면 안 됨 (헤더 라인이 form label로 분류돼 종료점 잃음).

### STEP1 source_section 라벨링 약함

같은 회사가 여러 섹션에 있을 때 LLM이 한 섹션만 추출 → Step 2 위조 탐지 input 부족.

**수정 위치**: `prompts.py::STEP1_SYSTEM_PROMPT`에 위반 사례 + 올바른 처리 예시 명시.

### cross-version 비교가 한국어 ↔ 영문 표기를 위조로 오인

이전 저장은 한국어, 새 추출은 영문 → "삭제됨" + "소급 추가됨" RED 페어 발생 → verdict=fail.

**수정 위치**: `integrity.py::_match_careers`
- `_company_keys` — `company` + `company_en` 둘 다 normalize set
- 두 단계 매칭: (1) 회사 키 set 교집합 → (2) 시작 월 일치 fallback

학교는 동일 패턴 적용 시도했으나 진짜 학교 위조 케이스(같은 year/degree에 다른 학교) 못 잡음 → institution name 매칭만 유지.

## 미해결 — 정책 결정 또는 외부 작업 필요

| 한계 | 영향 | 대응 가능 방향 |
|---|---|---|
| 학교명 음역(가천대 ↔ Gachon) | EDUCATION_CHANGED RED false positive | 음역 매핑 사전 또는 LLM-based 매칭 |
| 일학병행 정상 케이스 | CAREER_EDUCATION_OVERLAP YELLOW 노이즈 | 같은 institution + degree=phd/master 자동 dismiss |
| 503 트래픽 스파이크 | 시간대별 빈도 변동 | 모델 변경 거론 금지 — 시간대 회피·retry로 대응 |
| `Education.status` 영문 음역 | 졸업/Graduated 매핑 없음 | 영문 status canonicalize |

## verdict=fail 진단 매트릭스

```
field_scores 모두 1.0?
├── 예 → 추출 정상. cross-version 또는 Step 3 RED 원인.
│   ├── "X 경력이 삭제됨" + "Y 경력이 소급 추가됨" 페어 → cross-version 매칭 실패
│   │     → 한국어 ↔ 영문 표기 차이? company_en 매칭 작동 확인.
│   ├── "교육기관 변경: A → B" → 음역 한계 (현재 미해결)
│   ├── PERIOD_OVERLAP RED → 진짜 위조 (동시 재직). 정상 동작.
│   └── DURATION_MISMATCH RED 큰 차이 → 진짜 위조 의심
└── 아니오 → 추출 누락. STEP1·STEP2 결과 직접 확인.
```

## 새 이력서 형식 발견 시 진단 순서

1. 표본 1건 직접 추출 결과 확인 → 정상이면 끝.
2. 비정상이면 단계별 추적:
   - 텍스트 깨짐 → `text.py::extract_*` (.doc / .docx / .pdf)
   - 핵심 정보 잘림 → `preprocess_resume_text` 휴리스틱 (특히 자기소개 압축)
   - LLM 형식 못 따라감 → `prompts.py` 예시 추가
   - cross-version false positive → `integrity.py::_match_*`

## 결함 보고 형식

```
### 발견
원본 vs 결과 대조에서 X 케이스가 비정상

### 원인
- 코드 추적: file:line
- 휴리스틱 false positive vs 진짜 결함 구분

### 해결 옵션 (반드시 추천 명시)
A. ... (의미 / trade-off)
B. ... (권장 — 이유)
C. ...

### 권장: B
- 근거
- 작업 범위
- 다른 우선순위가 있으시면 알려주세요
```