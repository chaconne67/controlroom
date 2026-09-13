# 코코넛 AI 챗봇 고도화 설계

## 개요

현재 챗봇(support 앱)은 Claude API + tool 3개로 제한된 Q&A만 가능. 이를 하이브리드 RAG 기반 범용 Q&A 시스템으로 확장하여 펀드키퍼 서비스 전반에 대한 질문 응대가 가능하도록 한다.

## 요구사항

- 서비스 구조, 사용법, 전략 원리(AWT/BAA/MIX)에 대한 범용 Q&A
- 전략 설명: 개념 + 사용자 설정값 기반 설명, 내부 로직은 개념 수준만
- 개인 데이터 조회: 포트폴리오, 리밸런싱 이력, 계좌 잔고, 주문 내역, 월간 리뷰
- 접근 제어: 비로그인 → 일반 Q&A만, 로그인 → 개인 데이터 조회까지
- 관련 없는 질문은 사전 분류로 차단, 부드럽게 유도
- 사용량 제한: 추후 운영 데이터 보고 결정 (현재는 3초 rate limiting만)
- 지식 관리: 코드베이스에서 자동 추출

## 아키텍처

```
사용자 질문
    ↓
[입력 분류기] ← Gemini Flash-Lite로 펀드키퍼 관련 여부 판별
    ↓ (관련 없음 → 부드러운 거절 응답, API 호출 없음)
    ↓ (관련 있음)
[의도 분석] ← 개인 데이터 조회 필요 여부 판단
    ↓
    ├─ 일반 Q&A → [하이브리드 RAG 검색] → context + system prompt → Gemini 응답
    │
    └─ 개인 데이터 필요 → [하이브리드 RAG 검색] + [Tool Use] → Gemini 응답
                           (서비스 지식)         (계좌/전략 DB 조회)
```

## 모델 구성

| 구성요소 | 모델 | SDK | 호출 시점 |
|---|---|---|---|
| 지식 빌드 (contextual 요약) | Claude Sonnet 4.6 | `anthropic` | 빌드 시 |
| 임베딩 | Gemini `text-embedding-004` | `google-genai` | 빌드 시 |
| 입력 분류 | Gemini 3.1 Flash-Lite | `google-genai` | 실시간 |
| 챗봇 응답 + Tool use | Gemini 3.1 Flash-Lite | `google-genai` | 실시간 |

## 하이브리드 RAG 시스템

### 지식 빌드 파이프라인 (`manage.py build_knowledge`)

```
코드베이스 소스
    ↓
[자동 추출기] ← 모델 정의, 뷰 로직, 템플릿 텍스트, 전략 코드 등
    ↓
[의미 단위 청킹] ← 클래스/함수/설정 블록 단위로 분할
    ↓
[Contextual 요약 생성] ← Claude Sonnet 4.6로 각 chunk에 맥락 요약 추가
    ↓
[저장]
    ├─ ChromaDB (벡터 인덱스) ← Gemini embedding API로 임베딩
    └─ BM25 인덱스 ← 키워드 검색용
```

- 한 번 빌드하면 코드베이스 변경 전까지 재빌드 불필요
- 필요 시 deploy.sh에 자동 빌드 포함 가능

### 자동 추출 대상

| 소스 | 추출 내용 |
|---|---|
| Django 모델 (`models.py`) | 필드 구조, 관계 → 서비스 데이터 구조 설명 |
| 뷰/URL (`views.py`, `urls.py`) | 기능 목록, 사용 흐름 |
| 전략 코드 (`simulation/`, `portfolio_*/`) | 전략 개념, 설정 파라미터 (내부 로직은 개념만) |
| 템플릿 (`templates/`) | UI 텍스트, 사용자에게 보이는 용어 |
| 설정/상수 | 리밸런싱 주기 옵션, 자산군 분류 등 |

### 검색 흐름 (실시간)

```
사용자 질문
    ↓
    ├─ ChromaDB 벡터 검색 → top-K 결과
    ├─ BM25 키워드 검색 → top-K 결과
    ↓
[RRF 랭킹] ← 두 결과를 합산/재정렬
    ↓
상위 N개 chunk → Gemini context에 삽입
```

## Tool 구성 (총 7개)

### 기존 (3개)

| Tool | 설명 |
|---|---|
| `query_user_portfolios` | 사용자 포트폴리오 목록/기본 정보 |
| `query_portfolio_detail` | 포트폴리오 전략 설정, 종목, 성과 지표 |
| `query_asset_info` | ETF/자산 기본 정보, 수익률 지표 |

### 신규 (4개)

| Tool | 설명 | 조회 소스 |
|---|---|---|
| `query_rebalancing_history` | 최근 리밸런싱 이력 (날짜, 변경 종목/비중) | `RebalancingSchedule` 등 |
| `query_account_balance` | 계좌 잔고, 평가금액, 총 수익률 | `ClientAccount`, KIS API |
| `query_order_history` | 최근 매매 내역 | `Order` 모델 |
| `query_monthly_review` | 최근 월간 리뷰 리포트 | `MonthlyReport` 모델 |

- 로그인 사용자에게만 활성화
- 운영하면서 추가/수정 예정

## 입력 사전 분류

- Gemini Flash-Lite로 간단한 분류 prompt 호출
- 결과: `related` → 본 파이프라인 진행, `unrelated` → 부드러운 거절
- 비로그인 사용자의 개인 데이터 질문 → "로그인 후 이용 가능합니다" 안내
- max_tokens 최소화로 토큰 소비 극소

## 파일 구조

```
support/
├── views.py          ← ChatView 리팩토링 (Gemini SDK로 전환)
├── tools.py          ← tool 4개 추가
├── classifier.py     ← 입력 사전 분류기 (신규)
├── rag.py            ← RAG 검색 엔진 (신규)
└── management/
    └── commands/
        └── build_knowledge.py  ← 지식 빌드 커맨드 (신규)

data/
└── knowledge/
    ├── chroma/       ← ChromaDB 저장소
    └── bm25_index/   ← BM25 인덱스
```

## 접근 제어

| 사용자 상태 | 일반 Q&A | 개인 데이터 조회 |
|---|---|---|
| 비로그인 | O | X (로그인 안내) |
| 로그인 | O | O |

## 비용 구조

- **빌드 시**: Claude Sonnet (요약) + Gemini Embedding (임베딩) — 코드 변경 시에만
- **실시간**: Gemini Flash-Lite (분류 + 응답) — 저비용
- **사용량 제한**: 추후 운영 데이터 보고 결정
