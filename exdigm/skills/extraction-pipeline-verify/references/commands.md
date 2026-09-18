# Management Commands

각 단계 = 독립 `verify_*` management command. 모든 옵션은 `--help`로 확인.

## 명령 ↔ 단계 매핑

| 단계 | 명령 | non-obvious 옵션 |
|---|---|---|
| A | `select_test_files` | `--seed N` (재현), `--group-by-person` (같은 사람 dedupe) |
| B1 | `verify_download` | – |
| B2 | `verify_text_extract` | `--text-dir` (다음 단계 입력으로 사용) |
| B3 | `verify_text_quality` | – |
| B3.5 | `verify_birth_filter` | `--cutoff` (4자리 출생년도 또는 2자리 나이) |
| B4 단일 | `verify_llm_step1` | `--file-id` 1건 검증 — batch 전 동작 확인용 |
| B4 batch | `verify_llm_step1_batch` | `--filter-pass-from` (B3.5 PASS만), `--skip-existing` (재실행) |
| B4 audit | `verify_llm_step1_audit_v2` | – |
| B5 | `verify_llm_step2` | – |
| B7 | `verify_step3_analysis` | LLM 호출 없음, 빠름 |
| B8 | `verify_save` | `save_pipeline_result` 호출 (force는 email/phone 매칭으로 자동 update) |

## 진행 패턴

- B4 호출 전 `verify_llm_step1` 1건으로 LLM 응답 형태 확인.
- B4 batch는 PASS 케이스만 처리하도록 `--filter-pass-from` 사용.
- 중간 실패 시 `--skip-existing`으로 재실행.
- 토큰 사용량은 verify_* 명령이 결과 JSON에 자체 캡처.

## 백그라운드 실행

긴 단계는 `nohup setsid bash ... < /dev/null > log 2>&1 &` + `disown`. `PYTHONUNBUFFERED=1` 필수 (메모리 `feedback_python_unbuffered`).