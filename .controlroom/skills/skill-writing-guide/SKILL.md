---
name: skill-writing-guide
description: "Use when writing or reviewing Codex skills, Claude skills, prompt guides, agent instructions, or reusable task directives, especially to decide what information belongs in the instruction and what should be removed. Focuses on including non-obvious domain facts, irregular patterns, and behavior-changing rules while removing obvious, redundant, or low-value wording."
---

# 스킬 내용 작성 원칙

스킬/프롬프트에 "무엇을 넣고 뺄지" 판단하는 기준. 용어 일관성, 불필요한 문장 삭제, 예시 설계 같은 일반 프롬프트 품질은 `$prompt-guide`를 따르고, 이 스킬은 스킬 고유 결정만 다룬다.

## 반드시 포함 (AI가 알 수 없는 것)

- DB 고유값: PK, ID, 매핑 관계 등 AI가 유추할 수 없는 값
- 불규칙 패턴: 시트별 컬럼 차이, API 반환값 함정 등
- 도메인 고유 규칙: 외부에서 참조할 수 없는 비즈니스 로직
- 지침, 규칙 등 지켜야 할 사항

## 줄이거나 생략 (AI가 추론 가능한 것)

- 계산 전개식, 프로그래밍 상식, 일반적인 패턴 등 AI가 유추 가능한 내용
- 파일 목록, 세부 항목 등 AI가 도구를 호출해서 확인 가능한 것
- 모순의 부존재 등 부가 설명이 필요 없는 내용

## 사례 활용

사례를 언제 파일에 남길지 판단한다. 예시의 형태·경계 설계는 `$prompt-guide`의 최적화된 예시 규칙을 따른다.

- 사례에서 규칙을 도출했으면 **규칙만 남기고 사례는 삭제**
- 사례가 필요한 경우: 규칙만으로 설명이 어려운 불규칙 패턴
- 남기는 사례는 규칙 아래 "예시"로 배치하고 2~3개로 최소화

## 부재 메타 vs 매너 규칙

문서/프롬프트에는 **지금 일어나는 일과 그 위치**만 적는다. 다루지 않는 기능, 단계, 시스템, 필드의 부재 자체를 알리는 표현은 빼도 행동에 변화가 없으므로 인지만 심을 뿐이다.

**판정**: 이 문장이 없을 때 독자가 그 잘못된 행동을 자발적으로 할 가능성이 실제로 있는가?

- **있다 -> 매너 규칙(유지)**: 안내가 없으면 어길 행동을 사전에 차단하는 도메인 가드.
- **없다 -> 부재 메타(제거)**: 안 할 일을 짚어 의문만 만든다.

기준은 **행동 개연성**이다. 문장 형식("~하지 마세요"/"~만 하세요")이 아니라 그 문장이 막는 행동을 빼면 정말 일어날 일인지로 판정한다.

> 행동 개연성 없는 안내는 주의를 분산시키고, 개연성 있는 안내만 실패를 막는다.

## 스킬 구현 금지사항

- **파일 관리 원칙**: 재활용 가능한 스크립트/설정은 스킬 디렉토리(`~/controlroom/.controlroom/skills/{스킬명}/` 또는 `~/controlroom/<프로젝트>/skills/{스킬명}/`)에 영구 보관하여 보강. 일회성 코드는 임시 생성 후 **즉시 삭제**. 아무 디렉토리에 방치하지 않음
- **하드코딩 금지**: 컬럼 번호, 행 번호, 매직 넘버 등을 코드에 직접 기입하지 않음. 헤더 탐지, 패턴 매칭, 설정 파일 등으로 동적 처리
