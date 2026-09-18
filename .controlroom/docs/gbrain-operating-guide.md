# GBrain Operating Guide

GBrain은 사용자가 직접 쓰는 노트 앱이 아니라 에이전트가 작업 기억을 이어받기 위한 운영 레이어입니다.

## Why

사용자는 프로젝트 기획, 코드 작성 방향, 디버깅 이유, 모델/필드 설정 근거, 반복 피드백을 매 세션 다시 설명하지 않아야 합니다. 에이전트는 그 내용을 장기 지식으로 저장하고 다음 세션에서 검색해 적용해야 합니다.

## Before Work

의미 있는 작업 전에는 GBrain을 먼저 조회합니다.

```bash
~/.gbrain/bin/gbrain_with_google_env.sh query "작업 주제 agent operating protocol work rules" --no-expand
```

직접 읽을 필요가 큰 페이지:

- `agent/gbrain-operating-protocol`
- `feedback/codex-work-rules`
- `project/exdigm-operating-context`
- `project/gbrain-agent-memory-loop`

## During Work

저장 후보는 다음 기준으로 판단합니다.

- 사용자가 같은 패턴을 반복해서 지적했다.
- 다음 세션의 행동이 달라져야 한다.
- 프로젝트 고유 사실, 운영 절차, 모델/필드/설계 이유가 생겼다.
- 트러블슈팅 결과가 재사용 가능하다.
- 에이전트가 놓친 판단 기준을 보강할 필요가 있다.

저장하지 않을 내용:

- 일회성 실행 로그
- 단순 명령 결과
- 비밀값
- 코드로 바로 확인 가능한 파일 목록의 장황한 복사

## After Work

코드·스크립트·설정·서비스·schema·자동화 변경 뒤에는 `code-review-loop`를 실행합니다. 리뷰 루프 뒤 새 규칙이나 놓친 판단 기준이 생기면 GBrain에 저장합니다.
