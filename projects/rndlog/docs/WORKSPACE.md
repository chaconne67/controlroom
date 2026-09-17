# RNDLOG Windows 조정실

RNDLOG(R&D LOG / R&D NOTE)는 기업부설연구소·연구개발전담부서의 연구개발 증빙을 준비하고 관리하는 업무다. 개발·기획·문서 제작을 판단하는 에이전트는 Windows 조정실에서 실행한다. 기획은 조정실 docs에서 관리하고, 고객자료·산출물·공통 제작 자원의 저장 정본은 main `chaconne@49.247.192.127`에 둔다.

## main에 유지하는 실제 자료 구조

```text
/srv/consolidation/data/files-standby/workspace/
├── companies/              # 회사별 실제 업무공간
│   └── <정식 회사명>/
│       ├── sources/
│       │   ├── original/   # 고객이 제공한 원본, 변경 금지
│       │   └── intake/     # 수신메모·링크·카카오톡 캡처
│       ├── research/       # 해당 회사·기술·시장·논문 조사
│       └── deliverables/
│           ├── drafts/     # 작성·검토 중인 산출물
│           └── final/      # 실제 최종 산출물
└── resources/              # 여러 회사에 공통으로 쓰는 제작 자원
    ├── references/         # 제도·법령·공통 리서치
    ├── samples/            # 기존 보고서와 풀세트 샘플
    ├── templates/          # DOCX 디자인·양식
    └── tools/              # 생성·검증 도구
```

## 코드와 자료의 접속

조정실은 `C:\Users\chaconne\projects\rndlog`, main 코드 저장소는 `/home/chaconne/projects/rndlog`다. 서버의 프로젝트 루트는 symlink가 아닌 실제 Git 저장소다. `ssh chaconne@49.247.192.127`로 접속해 코드는 해당 프로젝트에서, 고객자료는 위 실제 workspace에서 관리한다. 자료 접속 프로그램은 코드 저장소의 `deploy/workspace_storage_gateway.py`이며 기존 제한 SSH 프로토콜과 고객자료 권한을 유지한다. 공통 DB·Docker Compose·복구 설정은 `/srv/consolidation/infra`에 있다.

## 구분 원칙

### `companies/`

특정 회사에 귀속되는 모든 것을 정식 법인명 아래에서 관리한다.

- 고객이 보낸 원문 파일과 이미지
- 수신 경로와 파일목록
- 해당 회사에 한정된 조사자료
- 작성 중인 보고서
- 검토 완료한 실제 산출물

### `resources/`

특정 회사의 소유물이 아니며 여러 회사의 산출물을 만들 때 공통으로 사용하는 자료다.

- 연구소 제도·법령·공통 조사자료
- 보고서 샘플과 샘플 풀세트
- DOCX 스타일 참조와 서식
- 생성·검증 스크립트

공통 샘플을 고객 최종 산출물로 계산하지 않고, 고객 원본을 `resources/`에 넣지 않는다.

## 서버 역할

| 서버 | 역할 |
|---|---|
| Windows PC | 전체 작업 조정, 기획·지침 관리, 자료 수신과 결과 검토 |
| main `chaconne@49.247.192.127` | `/home/chaconne/projects/rndlog`의 코드·Git·자료 접속 프로그램, 위 실제 자료 정본과 웹서비스 런타임, SSH 실행 명령 |
| 옛 DB·rndlog 주소 | main으로 전달하는 기존 호환 접속과 보관 자료. 새 코드 수정·자료 쓰기 정본은 main |
| `kmh-agent-kit` | RNDLOG 단일 워크플로우 스킬 정본 |
| GBrain 공용 `default` | 공통 운영정책·구조·결정 기록. 개인 공간의 원문은 복사하지 않음 |

## 신규 산출물

- 신규 공식 산출물은 DOCX다.
- 작업본은 `companies/<회사>/deliverables/drafts/`에 둔다.
- 검증 완료본은 `companies/<회사>/deliverables/final/`에 둔다.
- 기존 HTML/PDF는 각각 `drafts/`, `final/`에서 원형 보존한다.
- 자료 검토·문서 제작·고객 확인의 조건은 현재 `rndlog` 스킬을 적용한다.

## 조정실 문서

기획·작업 계획은 [문서 색인](README.md)에서 찾는다. Windows의 companies·resources는 기존 준비본이며 main 정본을 자동으로 덮어쓰거나 동기화하지 않는다.
