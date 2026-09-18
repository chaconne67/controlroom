# 쟁점 판정 결과 파일 포맷

`{stem}-rulings.md`에 적용되는 표준 포맷. `{stem}`은 대상 문서의 파일명에서 확장자를 제거한 값이다.

## 구조

```markdown
# Rulings — {topic} / {stem}

Status: IN_PROGRESS | COMPLETE
Last updated: {ISO 8601}
Rounds: {N}

## Resolved Items

### Issue {N}: {title} [{SEVERITY}]
- **Resolution:** ACCEPTED | REBUTTED | PARTIAL | USER_DECIDED
- **Intent alignment:** aligned | stretching | off-scope
- **Summary:** 판정 결론 1-2문장
- **Action:** 대상 문서에 직접 반영할 구체적 변경 내용 (ACCEPTED/PARTIAL인 경우)

## Disputed Items

### Issue {N}: {title} [{SEVERITY}]
- **레드팀:** {레드팀의 현재 주장}
- **저자:** {저자의 현재 반박}
- **Intent alignment:** aligned | stretching | off-scope
- **Evidence type:** code_reference | execution_result | data | logical_reasoning
- **Round:** {현재 라운드 수}
```

## Resolution 상태값

| 상태 | 의미 |
|------|------|
| `ACCEPTED` | 레드팀 이슈를 수용, 대상 문서에 직접 반영 |
| `REBUTTED` | 저자 반박이 승인됨, 변경 없음 |
| `PARTIAL` | 이슈의 일부만 수용 |
| `USER_DECIDED` | 에스컬레이션 후 사용자가 결정 |

## 완료 조건

모든 항목이 Resolved로 이동하고, Disputed Items가 비어있으면 Status를 `COMPLETE`로 변경한다.
