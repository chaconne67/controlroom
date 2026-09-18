---
name: extraction-pipeline-verify
description: 이력서 데이터 추출 파이프라인을 단계별로 격리해 검증하고 결함을 발견·수정한다. 한꺼번에 전체를 돌리는 대신 한 단계씩 결과를 직접 확인하면서 진짜 결함과 휴리스틱 false positive를 분리한다. 트리거 — "추출 품질 검증", "단계별 검증", "extraction 점검", 새 LLM 모델·새 프롬프트·새 전처리 변경 후, 운영 데이터에서 비정상 verdict가 자주 나오는 경우.
---

# Extraction Pipeline 단계별 검증 스킬

## 핵심 원칙

1. 한 단계씩 돌리고 사용자에게 결과 보고 후 다음 결정.
2. 자동 audit 메트릭이 낮으면 표본 3–5건 직접 대조 후 결함과 false positive 분리.
3. 결함이면 영구 코드 수정 + 신규 회귀 테스트 + 영향 단계 재실행.
4. 옵션 제시 시 추천과 근거 명시 (메모리 `feedback_recommend_dont_dump`).
5. 사용자가 명시 지시하지 않으면 LLM 모델 변경 거론 안 함 (메모리 `feedback_no_model_swap`).

## 실행 경계

- 중앙 에이전트가 SSH로 `/home/chaconne/exdigm-debug`에서 실행한다.
- B1~B7은 운영 비밀값 없이 최소 합성 자료로 검증한다.
- B8 저장 검증은 `scripts/debug_workspace.sh create`로 만든 일회성 DB에서 실행한다.
- 운영 DB 확인이 필요하면 `scripts/debug_workspace.sh shell-readonly`로 조회만 한다.
- 운영 데이터 저장·백필·repair는 주인님의 명시적 승인 없이는 실행하지 않는다.

## 9단계

```
A    파일 선정      카테고리별 random N개
B1   다운로드       Drive → 임시 바이너리
B2   텍스트 추출    extract_text + preprocess
B3   품질 분류      ok / too_short / garbled / empty
B3.5 생년 필터      cutoff (텍스트 + 파일명 보조, 검출 실패 시 PASS)
B4   LLM Step 1     raw 추출 + audit
B5   LLM Step 2     career·education 정규화
B7   Step 3 분석    period/edu overlap, campus, cross-version (LLM 없음)
B8   DB 저장        save_pipeline_result
```

각 단계는 독립 management command로 실행하고 JSON 스냅샷으로 결과를 보존한다.

## 참조 문서

- [references/stepwise-checklist.md](references/stepwise-checklist.md) — 단계별 결정 포인트와 도메인 함정
- [references/commands.md](references/commands.md) — management command 핵심 옵션
- [references/decision-patterns.md](references/decision-patterns.md) — 발견된 결함 패턴과 진단 매트릭스
- [scripts/](scripts/) — 단계 사이의 ad-hoc 분석 스크립트 (B2 패턴 분석, 전후 비교 등)
