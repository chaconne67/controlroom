# 코코넛 AI 챗봇 고도화 구현 계획

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 펀드키퍼 챗봇을 하이브리드 RAG + Gemini Flash-Lite 기반 범용 Q&A 시스템으로 고도화

**Architecture:** 코드베이스에서 자동 추출한 지식을 ChromaDB(벡터) + BM25(키워드) 하이브리드 검색으로 retrieve하고, Gemini Flash-Lite가 tool use와 함께 응답 생성. 입력 사전 분류로 관련 없는 질문 차단. 지식 빌드 시 Claude Sonnet 4.6으로 contextual 요약 생성.

**Tech Stack:** Django 4.1, google-genai SDK, anthropic SDK, ChromaDB, rank_bm25, Gemini text-embedding-004

**설계 문서:** `docs/plans/2026-03-10-chatbot-enhancement-design.md`

---

### Task 1: 의존성 설치

**Files:**
- Modify: `pyproject.toml`

**Step 1: 패키지 추가**

```bash
cd /home/work/fundkeeper
uv add chromadb rank_bm25
```

필요한 패키지:
- `chromadb` — 벡터 DB (로컬 persistent 모드)
- `rank_bm25` — BM25 키워드 검색

`google-generativeai` (0.8.5+)와 `anthropic` (0.79.0+)는 이미 설치됨.

**Step 2: 설치 확인**

```bash
uv run python -c "import chromadb; import rank_bm25; print('OK')"
```

Expected: `OK`

**Step 3: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "feat: chromadb, rank_bm25 의존성 추가 (챗봇 RAG용)"
```

---

### Task 2: 지식 자동 추출기 (Extractor)

**Files:**
- Create: `support/knowledge_extractor.py`

**목적:** 코드베이스에서 지식 chunk를 자동 추출. 각 chunk는 `{"source", "category", "title", "content"}` 형태.

**Step 1: 추출기 구현**

`support/knowledge_extractor.py` — 아래 소스들에서 지식 추출:

| 추출 함수 | 소스 | 추출 방식 |
|---|---|---|
| `extract_models()` | 전체 앱의 `models.py` | AST 파싱으로 클래스/필드 추출, 서비스 관점 설명 생성 |
| `extract_views()` | 전체 앱의 `views.py` + `urls.py` | URL 패턴 + 뷰 클래스/함수명 → 기능 목록 |
| `extract_strategies()` | `simulation/`, `portfolio_*/` | 전략 클래스의 docstring, 설정 파라미터, 개념 설명 |
| `extract_templates()` | `templates/**/*.html` | UI 텍스트, 메뉴 항목, 도움말 텍스트 추출 |
| `extract_constants()` | 설정 파일, 상수 정의 | 리밸런싱 주기 옵션, 자산군 분류 등 |
| `extract_service_guide()` | 직접 작성 | 서비스 개요, 사용법, FAQ (하드코딩 텍스트) |

각 추출 함수는 `list[dict]`를 반환:

```python
{
    "source": "myportfolio/models.py",
    "category": "models",       # models | views | strategy | ui | constants | guide
    "title": "MyPortfolios 모델",
    "content": "사용자 포트폴리오 설정을 저장하는 모델. 필드: name(포트폴리오명), ..."
}
```

메인 함수 `extract_all() -> list[dict]` 가 모든 추출 함수를 호출하여 전체 chunk 리스트 반환.

**참고 — 추출 대상 앱 목록:**
- 포트폴리오: `myportfolio`, `portfolio_awt`, `portfolio_baa`, `portfolio_mix`
- 시뮬레이션: `simulation` (models, tools, simulation.py)
- 리밸런싱: `rebalancing_info`
- 계정: `myaccount`, `fkuser`
- 데이터: `etfs`, `krx_filter`
- 기타: `recipe`, `monthly_report`, `retire`, `support`

**Step 2: 테스트**

```bash
uv run python -c "
import django; import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'fundkeeper.settings.local'
django.setup()
from support.knowledge_extractor import extract_all
chunks = extract_all()
print(f'Total chunks: {len(chunks)}')
for c in chunks[:3]:
    print(f'  [{c[\"category\"]}] {c[\"title\"]}: {c[\"content\"][:80]}...')
"
```

Expected: chunk 목록 출력, 최소 50개 이상

**Step 3: Commit**

```bash
git add support/knowledge_extractor.py
git commit -m "feat: 코드베이스 지식 자동 추출기 구현"
```

---

### Task 3: 지식 빌드 커맨드 (build_knowledge)

**Files:**
- Create: `support/management/__init__.py`
- Create: `support/management/commands/__init__.py`
- Create: `support/management/commands/build_knowledge.py`

**목적:** `manage.py build_knowledge` 실행 시:
1. `extract_all()`로 chunk 추출
2. Claude Sonnet 4.6으로 각 chunk에 contextual 요약 추가
3. Gemini `text-embedding-004`로 임베딩 생성
4. ChromaDB에 저장 (persistent, `data/knowledge/chroma/`)
5. BM25 인덱스 생성 후 pickle 저장 (`data/knowledge/bm25_index.pkl`)

**Step 1: 디렉토리 생성**

```bash
mkdir -p support/management/commands
touch support/management/__init__.py
touch support/management/commands/__init__.py
mkdir -p data/knowledge
```

**Step 2: 커맨드 구현**

`support/management/commands/build_knowledge.py`:

```python
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = '코드베이스에서 지식을 추출하여 RAG 인덱스를 빌드합니다'

    def handle(self, *args, **options):
        # 1. extract_all()
        # 2. contextual_summarize() — Claude Sonnet 4.6
        #    각 chunk에 대해:
        #    prompt: "이 코드/텍스트가 코코넛 자산관리 서비스에서 어떤 역할을 하는지
        #             사용자 관점에서 2-3문장으로 요약하세요."
        #    결과를 chunk['context'] 필드에 추가
        # 3. embed_chunks() — Gemini text-embedding-004
        #    chunk['content'] + chunk['context']를 합쳐서 임베딩
        # 4. save_to_chroma() — ChromaDB persistent client
        #    path: data/knowledge/chroma/
        #    collection: 'fundkeeper_knowledge'
        # 5. save_bm25_index() — rank_bm25
        #    한국어 형태소 분석 or 공백 토크나이징
        #    pickle로 data/knowledge/bm25_index.pkl 저장
```

**Contextual 요약 호출 예시:**

```python
import anthropic

client = anthropic.Anthropic()
response = client.messages.create(
    model="claude-sonnet-4-6-20250514",
    max_tokens=200,
    messages=[{
        "role": "user",
        "content": f"다음은 코코넛(coconut.ai.kr) 자산관리 서비스의 코드/텍스트입니다.\n\n"
                   f"[소스: {chunk['source']}]\n[카테고리: {chunk['category']}]\n\n"
                   f"{chunk['content']}\n\n"
                   f"이 내용이 서비스에서 어떤 역할을 하는지 사용자 관점에서 2-3문장으로 요약하세요."
    }]
)
chunk['context'] = response.content[0].text
```

**Gemini Embedding 호출 예시:**

```python
from google import genai

client = genai.Client()
text = f"{chunk['context']}\n{chunk['content']}"
result = client.models.embed_content(
    model="text-embedding-004",
    contents=text,
)
embedding = result.embeddings[0].values  # list[float], 768차원
```

**ChromaDB 저장 예시:**

```python
import chromadb

client = chromadb.PersistentClient(path="data/knowledge/chroma")
collection = client.get_or_create_collection("fundkeeper_knowledge")
collection.upsert(
    ids=[f"chunk_{i}" for i in range(len(chunks))],
    embeddings=[c['embedding'] for c in chunks],
    documents=[c['content'] for c in chunks],
    metadatas=[{"source": c['source'], "category": c['category'],
                "title": c['title'], "context": c['context']} for c in chunks],
)
```

**BM25 인덱스 저장 예시:**

```python
import pickle
from rank_bm25 import BM25Okapi

tokenized = [doc['content'].split() for doc in chunks]
bm25 = BM25Okapi(tokenized)
with open('data/knowledge/bm25_index.pkl', 'wb') as f:
    pickle.dump({'bm25': bm25, 'chunks': chunks}, f)
```

**Step 3: 실행 테스트**

```bash
uv run python manage.py build_knowledge
```

Expected: chunk 추출 → 요약 생성 → 임베딩 → 저장 완료 메시지. `data/knowledge/chroma/` 및 `data/knowledge/bm25_index.pkl` 생성 확인.

**Step 4: Commit**

```bash
git add support/management/ data/knowledge/.gitkeep
git commit -m "feat: manage.py build_knowledge 커맨드 구현"
```

**주의사항:**
- `data/knowledge/chroma/` 와 `bm25_index.pkl`은 `.gitignore`에 추가 (빌드 산출물)
- Claude API rate limit 고려 — chunk가 많으면 batch 처리 + sleep 필요
- 진행 상황 출력: `self.stdout.write(f"Processing {i+1}/{total}...")`

---

### Task 4: RAG 검색 엔진

**Files:**
- Create: `support/rag.py`

**목적:** 사용자 질문 → 하이브리드 검색 → 상위 N개 chunk 반환

**Step 1: RAG 엔진 구현**

`support/rag.py`:

```python
class RAGEngine:
    """하이브리드 RAG 검색 엔진 — ChromaDB(벡터) + BM25(키워드) + RRF 랭킹"""

    def __init__(self):
        # ChromaDB persistent client 로딩
        # BM25 인덱스 pickle 로딩
        # 싱글턴 또는 모듈 레벨 초기화

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        # 1. Gemini embedding으로 query 벡터화
        # 2. ChromaDB에서 top_k * 2 검색
        # 3. BM25에서 top_k * 2 검색
        # 4. RRF(Reciprocal Rank Fusion)로 합산
        # 5. 상위 top_k 반환

    def _rrf(self, vector_results, bm25_results, k=60):
        # RRF 점수 = sum(1 / (k + rank)) for each result list
        # 두 결과를 합산하여 최종 순위 결정
```

**RRF 알고리즘:**

```python
def _rrf(self, rankings: list[list[str]], k=60) -> list[str]:
    scores = {}
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking):
            scores[doc_id] = scores.get(doc_id, 0) + 1 / (k + rank + 1)
    return sorted(scores, key=scores.get, reverse=True)
```

**모듈 레벨 싱글턴:**

```python
_engine = None

def get_rag_engine() -> RAGEngine:
    global _engine
    if _engine is None:
        _engine = RAGEngine()
    return _engine
```

**Step 2: 테스트**

```bash
uv run python -c "
import django; import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'fundkeeper.settings.local'
django.setup()
from support.rag import get_rag_engine
engine = get_rag_engine()
results = engine.search('BAA 전략이 뭔가요?')
for r in results:
    print(f'  [{r[\"category\"]}] {r[\"title\"]}: {r[\"content\"][:60]}...')
"
```

Expected: BAA 전략 관련 chunk가 상위에 나옴

**Step 3: Commit**

```bash
git add support/rag.py
git commit -m "feat: 하이브리드 RAG 검색 엔진 구현 (ChromaDB + BM25 + RRF)"
```

---

### Task 5: 입력 사전 분류기

**Files:**
- Create: `support/classifier.py`

**목적:** 사용자 질문이 펀드키퍼 관련인지 판별. 관련 없으면 부드러운 거절 메시지 반환.

**Step 1: 분류기 구현**

`support/classifier.py`:

```python
from google import genai

GEMINI_MODEL = "gemini-2.5-flash-lite-preview-06-17"  # 또는 출시된 정식 모델명 확인

CLASSIFY_PROMPT = """사용자 질문이 다음 범위에 해당하는지 판단하세요:
- 자산관리, 투자, ETF, 포트폴리오, 주식
- 코코넛/펀드키퍼 서비스 사용법
- 전략(AWT, BAA, MIX), 리밸런싱, 백테스팅
- 계좌, 수익률, 주문, 매매

"related" 또는 "unrelated"만 답하세요."""

SOFT_REJECT = ("죄송합니다, 저는 코코넛 자산관리 서비스 전문 상담원이라 "
               "해당 질문에는 답변이 어렵습니다. "
               "포트폴리오, 전략, ETF 등에 대해 물어보시겠어요?")


def classify(message: str) -> dict:
    """
    Returns:
        {"is_related": True} or {"is_related": False, "reject_message": "..."}
    """
    client = genai.Client()
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=f"사용자 질문: {message}",
        config=genai.types.GenerateContentConfig(
            system_instruction=CLASSIFY_PROMPT,
            max_output_tokens=10,
        ),
    )
    result = response.text.strip().lower()
    if "unrelated" in result:
        return {"is_related": False, "reject_message": SOFT_REJECT}
    return {"is_related": True}
```

**Step 2: 테스트**

```bash
uv run python -c "
from support.classifier import classify
print(classify('BAA 전략의 리밸런싱 주기는?'))    # related
print(classify('오늘 날씨 어때?'))               # unrelated
print(classify('내 포트폴리오 수익률 알려줘'))     # related
"
```

**Step 3: Commit**

```bash
git add support/classifier.py
git commit -m "feat: 입력 사전 분류기 구현 (Gemini Flash-Lite)"
```

---

### Task 6: Tool 확장 (4개 추가)

**Files:**
- Modify: `support/tools.py`

**목적:** 기존 3개 tool에 4개 추가. Gemini function calling 형식에 맞게 tool 정의도 변환.

**Step 1: 모델 조사에 따른 tool 구현**

추가할 tool과 실제 조회 소스:

| Tool | 실제 모델 | 비고 |
|---|---|---|
| `query_rebalancing_history` | `rebalancing_info.RebalancingSchedule`, `rebalancing_info.OrderList` | 최근 N건 |
| `query_account_balance` | `myaccount.MyAccount` + KIS API (`simulation.api.KisApi`) | 실시간 잔고 |
| `query_order_history` | `myaccount.TradeHistory` + `rebalancing_info.OrderList` | 최근 매매 |
| `query_monthly_review` | `monthly_report.services.build_report_context()` | 동적 생성 |

**주의사항:**
- `query_account_balance`: KIS API 호출 시 `MyAccountAuth`에서 토큰 필요. 토큰 만료 시 갱신 로직 포함.
- `query_monthly_review`: `monthly_report/models.py`가 비어있음. `monthly_report/services.py`의 `build_report_context()` 함수로 동적 생성.
- `query_order_history`: `order/models.py`가 비어있음. `TradeHistory` (myaccount)와 `OrderList` (rebalancing_info) 두 곳에서 조회.

**Step 2: Gemini function calling 형식으로 TOOL_DEFINITIONS 변환**

기존 Anthropic 형식 → Gemini 형식으로 변환:

```python
# Anthropic 형식 (기존)
{"name": "...", "description": "...", "input_schema": {"type": "object", ...}}

# Gemini 형식 (변환)
# google.genai.types.FunctionDeclaration 사용
```

**Step 3: 테스트**

각 tool을 직접 호출하여 결과 확인.

**Step 4: Commit**

```bash
git add support/tools.py
git commit -m "feat: 챗봇 tool 4개 추가 (리밸런싱/잔고/주문/월간리뷰)"
```

---

### Task 7: ChatView 리팩토링 (Gemini SDK 전환)

**Files:**
- Modify: `support/views.py`

**목적:** 기존 Anthropic SDK 기반 ChatView를 Gemini SDK로 전환하고, RAG + 분류기 통합.

**Step 1: ChatView 전체 흐름 재구현**

```python
class ChatView(View):

    def post(self, request):
        user = request.session.get('fkuser')
        message = ...  # 기존과 동일한 입력 파싱

        # 1. 입력 분류
        classification = classify(message)
        if not classification['is_related']:
            return JsonResponse({'answer': classification['reject_message']})

        # 2. RAG 검색
        rag_engine = get_rag_engine()
        rag_results = rag_engine.search(message, top_k=5)
        rag_context = "\n\n".join([
            f"[{r['title']}]\n{r['context']}\n{r['content']}"
            for r in rag_results
        ])

        # 3. System prompt에 RAG context 삽입
        system_prompt = SYSTEM_PROMPT + f"\n\n## 참고 자료\n{rag_context}"

        # 4. Tool 설정 (로그인 시에만)
        tools = GEMINI_TOOL_DECLARATIONS if user else None

        # 5. Gemini API 호출
        client = genai.Client()
        # ... Gemini chat completion with function calling
        # tool_use 루프 처리 (기존 Anthropic 루프와 유사)

        # 6. 세션 히스토리 저장
        ...

        return JsonResponse({'answer': answer})
```

**Step 2: 비로그인 사용자 지원**

- 현재 chatbot.html에 `{% if request.session.fkuser %}` 조건 → 제거하여 비로그인도 UI 표시
- ChatView에서 `user` 없으면 tool 비활성화, 일반 Q&A만 가능

**Step 3: 테스트**

```bash
# 서버 실행 후 curl로 테스트
curl -X POST http://localhost:8800/support/chat/ \
  -H "Content-Type: application/json" \
  -d '{"message": "BAA 전략이 뭔가요?"}'
```

**Step 4: Commit**

```bash
git add support/views.py
git commit -m "feat: ChatView를 Gemini SDK 기반으로 전환, RAG + 분류기 통합"
```

---

### Task 8: chatbot.html 업데이트

**Files:**
- Modify: `templates/chatbot.html`

**목적:** 비로그인 사용자도 챗봇 UI 접근 가능하도록 수정.

**Step 1: 조건부 렌더링 변경**

```html
<!-- 기존: {% if request.session.fkuser %} ... {% endif %} -->
<!-- 변경: 조건 제거, 모든 사용자에게 표시 -->
<div x-data="chatbot()" x-cloak class="font-neo">
    ...
</div>
```

비로그인 시 초기 메시지 변경:
```javascript
messages: [{
    id: 0, role: 'bot',
    text: '안녕하세요! 코코넛 AI 상담입니다.\n포트폴리오, 전략, ETF 등 궁금한 점을 물어보세요.\n(로그인하시면 계좌 현황도 조회 가능합니다)'
}],
```

**Step 2: Commit**

```bash
git add templates/chatbot.html
git commit -m "feat: 비로그인 사용자도 챗봇 접근 가능하도록 수정"
```

---

### Task 9: .gitignore 및 환경 변수 정리

**Files:**
- Modify: `.gitignore`
- Modify: `.env` (또는 `config/info.py`)

**Step 1: .gitignore에 빌드 산출물 추가**

```
# RAG knowledge index
data/knowledge/chroma/
data/knowledge/bm25_index.pkl
```

**Step 2: 환경 변수 확인**

필요한 환경 변수:
- `GOOGLE_API_KEY` — Gemini API (embedding + Flash-Lite 응답)
- `ANTHROPIC_API_KEY` — Claude Sonnet (지식 빌드용, 기존 `CLAUDE_API_KEY`와 별개일 수 있음)

**Step 3: Commit**

```bash
git add .gitignore
git commit -m "chore: RAG 빌드 산출물 gitignore 추가"
```

---

### Task 10: 통합 테스트 및 검증

**Step 1: 지식 빌드 실행**

```bash
uv run python manage.py build_knowledge
```

**Step 2: 서버 실행 후 시나리오 테스트**

```bash
uv run python manage.py runserver 0.0.0.0:8800
```

테스트 시나리오:

| 시나리오 | 예상 동작 |
|---|---|
| 비로그인 + "BAA 전략이 뭔가요?" | RAG 검색 → 전략 개념 설명 응답 |
| 비로그인 + "내 포트폴리오 알려줘" | "로그인 후 이용 가능합니다" 안내 |
| 비로그인 + "오늘 날씨 어때?" | 사전 분류 → 부드러운 거절 |
| 로그인 + "내 포트폴리오 알려줘" | tool 호출 → DB 조회 → 포트폴리오 목록 |
| 로그인 + "리밸런싱 언제 했어?" | tool 호출 → 리밸런싱 이력 응답 |
| 로그인 + "계좌 잔고 알려줘" | tool 호출 → KIS API → 잔고 응답 |

**Step 3: 최종 Commit**

```bash
git add -A
git commit -m "feat: 코코넛 AI 챗봇 고도화 완료 (하이브리드 RAG + Gemini Flash-Lite)"
```

---

## 구현 순서 요약

```
Task 1: 의존성 설치
    ↓
Task 2: 지식 자동 추출기
    ↓
Task 3: 지식 빌드 커맨드 (build_knowledge)
    ↓
Task 4: RAG 검색 엔진
    ↓
Task 5: 입력 사전 분류기
    ↓
Task 6: Tool 확장 (4개 추가)
    ↓
Task 7: ChatView 리팩토링 (Gemini 전환)
    ↓
Task 8: chatbot.html 업데이트
    ↓
Task 9: .gitignore 및 환경 변수 정리
    ↓
Task 10: 통합 테스트
```

**병렬 가능 구간:**
- Task 2, 5, 6은 서로 독립적 → 병렬 구현 가능
- Task 4는 Task 3 완료 후 (인덱스가 있어야 검색 가능)
- Task 7은 Task 4, 5, 6 모두 완료 후 (통합 지점)
