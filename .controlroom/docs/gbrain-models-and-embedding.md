# GBrain Models And Embedding

이 서버의 GBrain은 검색/저장과 distillation 모델이 서로 다른 문제라는 전제에서 설정합니다.

## Embedding

검색 품질에는 임베딩이 필요합니다. 현재 기준:

- Provider: Google
- Model: `google:gemini-embedding-001`
- Dimensions: `768`
- Chunk embedding column: `vector(768)`
- Fact embedding column: `halfvec(768)`

확인:

```bash
~/.gbrain/bin/gbrain_with_google_env.sh config get embedding_model
~/.gbrain/bin/gbrain_with_google_env.sh stats
~/.gbrain/bin/gbrain_with_google_env.sh embed --stale --dry-run
```

`embedding_disabled: true`, `embed=0%`, `stale chunks`가 보이면 검색 품질이 제한됩니다. 이 문제는 distillation 모델을 Gemini로 바꾸는 것과 별개입니다.

## Distillation

일일 distillation은 GBrain의 `dream` 엔진을 래핑합니다. 핵심은 새 분류기를 만드는 것이 아니라 Codex JSONL 로그를 transcript corpus로 바꾸고, GBrain dream이 worth-processing과 pattern synthesis를 수행하게 하는 것입니다.

기본 모델:

```bash
GBRAIN_DREAM_MODEL=openrouter:google/gemini-3-flash-preview
```

직접 Google provider가 dream verdict provider로 연결되지 않는 경우가 있어 OpenRouter Gemini를 기본값으로 둡니다. 모델은 `GBRAIN_DREAM_MODEL` 환경변수로 교체할 수 있습니다.

## Secret Policy

래퍼는 `GEMINI_API_KEY`와 필요한 경우 `OPENROUTER_API_KEY`만 읽습니다. `DATABASE_URL`과 `OPENAI_API_KEY`는 GBrain subprocess 환경에서 제거합니다.
