# 회사 README 파일 양식 방안

## 목적

벤처인증 작업의 중심 파일을 사람이 읽고 쓰기 쉬운 구조화 Markdown으로 전환한다.

기존 통합 JSON은 원자료, 포털 구조, 입력값, 본문, 상태가 한 파일에 섞이면서 복잡해졌다. 긴 한글 본문과 라벨이 JSON 문자열로 들어가 한글 깨짐 리스크도 커졌다.

앞으로는 회사별 `README.md`를 주 파일로 두고, 포털 구조는 공통 인덱스 파일로 분리한다. 자동화 스크립트는 `README.md`를 직접 파싱하여 공통 포털 구조와 매칭한다.

## 기본 구조

회사별 README 파일은 다음 위치에 둔다.

```text
companies/<회사>/README.md
```

포털 구조는 회사마다 바뀌지 않으므로 공통 파일로 둔다.

```text
shared/portal_structure/venture_fields.json
```

## 역할 분리

`README.md`는 사람이 읽고 에이전트가 작성하는 중심 문서다.

`shared/portal_structure/venture_fields.json`은 포털 화면 구조와 필드 인덱스를 보관한다.

자동화 스크립트는 `README.md`의 `field_id`를 읽고, 같은 `field_id`를 가진 포털 구조와 매칭해 입력한다.

## README.md 권장 구조

```markdown
# <회사명> 벤처인증 작업공간

## Information

### Extracted Documents

| source_id | document | status | summary |
|---|---|---|---|
| SRC-001 | src/SRC-001_<문서명>.md | ready |  |

### Distilled Context

#### company_positioning


#### main_services

- 

#### customer_problems

- 

#### existing_alternatives

- 

#### technology_differentiation

- 

#### target_customers

- 

#### competition_context

- 

#### commercialization_direction

- 

#### needs_confirmation

- 

## Fields

### field: company_name

```yaml
status: needs_confirmation
source: []
notes: []
```


### field: competition

```yaml
status: needs_confirmation
char_count: 0
source: []
notes: []
```


## Status

```yaml
batch_status: pending
current_phase: venture-phase1-bootstrap
needs_confirmation: []
```
```

## 포털 구조 파일 권장 구조

```json
{
  "fields": {
    "company_name": {
      "page_id": "company_info",
      "section_id": "basic",
      "label": "기업명",
      "input_type": "text",
      "selector": "",
      "required": true
    },
    "competition": {
      "page_id": "growth_strategy",
      "section_id": "market",
      "label": "경쟁사 분석",
      "input_type": "textarea",
      "selector": "",
      "required": true
    }
  }
}
```

## 자동화 적용 흐름

1. 자동화 스크립트가 `README.md`를 읽는다.
2. `### field: <field_id>` 블록을 파싱한다.
3. 각 field 블록의 YAML 메타데이터와 본문 값을 추출한다.
4. `shared/portal_structure/venture_fields.json`에서 같은 `field_id`를 찾는다.
5. `status: ready`인 필드만 포털에 입력한다.
6. `input_type`에 따라 text, textarea, radio, select, file 입력 방식을 적용한다.

## 장점

긴 한글 본문을 JSON 문자열 안에 넣지 않아도 된다.

사람이 README 파일을 열어 바로 검토할 수 있다.

작성 에이전트가 Markdown 본문을 자연스럽게 작성할 수 있다.

포털 구조는 공통 파일에 고정하므로 회사별 파일이 단순해진다.

포털 화면에 입력할 개별 값과 본문은 `field_id` 기준으로 포털 구조와 매칭된다.

## 주의사항

Markdown은 자유형 문서가 아니라 엄격한 구조화 문서로 사용한다.

필드 블록 제목은 반드시 `### field: <field_id>` 형식을 따른다.

필드 메타데이터는 반드시 fenced YAML 블록으로 둔다.

자동화 전에 `README.md` 구조 검증을 먼저 실행한다.

필드 구조가 깨지면 자동화 입력을 진행하지 않는다.

## 권장 전환 방향

기존 통합 JSON은 새 작업 기준으로 사용하지 않는다.

새 회사부터 `README.md` 중심 구조를 적용한다.

기존 회사 데이터는 필요할 때 `README.md` 구조로 이전한다.

포털 자동화는 최종적으로 `README.md`와 `venture_fields.json`을 직접 읽어 실행한다.
