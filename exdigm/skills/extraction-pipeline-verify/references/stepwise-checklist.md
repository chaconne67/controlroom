# 단계별 결정 포인트와 도메인 함정

각 단계의 일반 동작은 코드와 `--help`로 확인 가능. 여기는 **실수하기 쉬운 결정·함정**만.

## A — 파일 선정

- `--seed` 명시해야 단계 재실행 시 같은 표본. seed 없으면 추출 결과 변동 비교 불가.
- `--group-by-person` 적용 시 같은 사람의 파일 변형이 한 그룹으로 묶임 (dedupe).

## B1 — 다운로드

특이 함정 없음. 503·인증 실패는 retry 내장.

## B2 — 텍스트 추출 + 전처리

**자기소개 압축이 학력/경력 섹션을 잘라먹는지 직접 확인**.
- `_compress_self_intro_region`은 self-intro 헤더(About Me 등) 발견 → STRUCTURED 헤더(Education/Career/Skills/...) 발견까지 압축.
- STRUCTURED 헤더가 영문/한국어 양쪽 변형을 모두 인식하는지 새 형식 발견 시 점검.
- 텍스트 표본 1–3건의 v1 → v2 비교를 `scripts/compare_preprocess.py`로 수행.

`_FORM_LABEL_ONLY` 정규식에서 `학력|education|경력|career|자격증|certification|어학|language` 키워드 빼면 안 됨. 뺐다간 STRUCTURED 헤더 라인이 form label로 분류돼 self-intro 종료점을 잃음.

## B3 — 품질 분류

압축이 과해서 50자 미만으로 떨어진 케이스가 too_short로 분류되는지 점검.

## B3.5 — 생년 필터

- 검출 실패 = SKIP 정책은 위험 (false negative). PASS 정책 권장.
- 파일명 보조(`parse_filename`)는 한국어 이름 토큰이 있어야 동작. 영문 이력서 파일명은 fallback 효과 없음 → 보수적 PASS.
- 한국어 표준 표기 정규식: `YYYY년 MM월 DD일생`, `YYYY.MM.DD생`, `D.O.B. MM.DD.YYYY` 4종 모두 반영.

## B4 — LLM Step 1

호출 전 1건 검증으로 source_section 라벨링·JSON 구조 확인 후 batch 진행.

503은 시간대 영향이 큼. 같은 모델·코드라도 한 시간 안에 빈도가 변함. 모델 변경은 사용자 명시 지시 시만 (메모리 `feedback_no_model_swap`).

### audit 해석

자동 휴리스틱이 잡는 false positive 패턴 (이걸 "결함"으로 결론 X):
- 본문에서 거론된 타사·기관·부서명 ("나노전자", "참여기업: 삼성전자, 하이닉스 반도체")
- 영문 일반 단어 ("Embedded S/W")
- 워크숍 참가 같은 이벤트성 이력 라인
- 본문 헤더 텍스트 ("SUMMARY OF WORK EXPERIENCE", "DETAILED WORK EXPERIENCE")

audit recall이 낮은 outlier 3–5건을 직접 원본 ↔ 결과 대조 → 진짜 LLM 누락 vs 휴리스틱 한계 분리.

precision이 낮으면(결과에 있는 회사가 원본에 없음) 환각 의심 → 실제 환각인지 normalize 차이인지 직접 확인.

## B5 — LLM Step 2

raw careers 갯수 → 통합 careers 갯수가 의미있게 줄어드는지 확인. 줄지 않으면 LLM이 source_section 별도 추출을 그대로 두고 통합 안 한 것 → integrity flag 비교 가치 손실.

flag 분류:
- LLM type (`DATE_CONFLICT`, `DURATION_MISMATCH`, `COMPANY_DUPLICATE`, `SHORT_DEGREE_SUSPECT`, `OTHER`) — 위조 의심
- 코드 type (`PERIOD_OVERLAP`, `CAMPUS_DEPARTMENT_MATCH`, `BIRTH_YEAR_MISMATCH`, `CAREER_DELETED`, `STEP2_VALIDATION`) — Step 3·검증기에서 추가
- LLM이 코드 type 사용하면 안 됨 (프롬프트에 명시).

## B7 — Step 3 코드 분석

YELLOW 분류:
- `CAREER_EDUCATION_OVERLAP` 정규직 + 학교 동시 → 박사과정·일학병행 정상 케이스 다수. 같은 institution + degree=phd/master면 검수자가 빠르게 dismiss.
- `CAMPUS_MISSING` 멀티캠퍼스 대학 (한양대 서울/ERICA, 고려대 안암/세종, 단국대 죽전/천안) — 이력서에 보통 없는 정보. 너무 자주 발생하면 노이즈 정책 검토.

RED:
- `PERIOD_OVERLAP` 동시 재직은 진짜 위조 의심. 단, 인수인계 기간(3개월 이하) 제외됨.
- `CAREER_DELETED` cross-version 비교에서 한국어 ↔ 영문 표기 차이를 위조로 오인할 수 있음 (B8 진단 참고).

## B8 — DB 저장

**verdict=fail 진단 순서**:

1. `field_scores` — 모두 1.0이면 추출은 정상. fail 원인은 cross-version 또는 Step 3 RED.
2. `issues` 메시지 패턴 확인:
   - "X 경력이 삭제됨" + "Y 경력이 소급 추가됨" 페어가 있으면 → cross-version 매칭 실패. 이전 저장과 새 추출의 회사명 표기가 다른지 (한국어 ↔ 영문) 확인.
   - "교육기관 변경: A → B" → 같은 학교의 음역 차이일 수 있음 (가천대학교 ↔ Gachon University). `_education_match_keys`는 institution name 매칭만 — 음역은 한계.
3. 진짜 위조 신호:
   - PERIOD_OVERLAP RED (김수정 패턴: 같은 기간 4개 회사)
   - DURATION_MISMATCH 큰 차이 (2년+ 차이는 진짜 의심)
   - SHORT_DEGREE 학사 4년 미만에 정당 사유 없음
   - CAMPUS_DEPARTMENT_MATCH 학과가 특정 캠퍼스에만 있는데 미명시

## 결함 발견 → 수정 → 검증 사이클

```
1. audit 또는 직접 검증으로 의심 outlier 발견
2. 표본 원본 ↔ 결과 대조 → 진짜 결함 vs false positive
3. 결함이면:
   - 영구 코드 수정 (text.py / sanitizers.py / filename.py / prompts.py / integrity.py)
   - 신규 회귀 테스트 추가
   - pytest 통과 확인
   - 영향 단계 재실행 (B2 변경 → B2.. 부터 / 프롬프트 변경 → B4부터)
4. false positive면 audit 휴리스틱 보강 또는 메트릭 해석 가이드 갱신
```