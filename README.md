# 조정실 프로젝트 문서

개발 에이전트는 조정실에서만 실행합니다. 기획·리서치·작업 계획은 이 비공개 저장소에서 관리하며, 서버의 코드·데이터·미디어와 실행·검증 명령은 기존 SSH 경로로 사용합니다. 공통 지침·스킬은 kmh-agent-kit가 정본입니다.

## 위치와 사용

- 실제 문서 원본: `C:\Users\chaconne\projects\_control-docs\<project>`.
- 각 조정실의 `docs`는 해당 원본의 `docs`를 연결합니다. 그 경로에서 문서를 편집하면 같은 파일이 바뀝니다.
- 프로그램·테스트가 읽는 파일, 코드와 함께 바뀌는 기술 계약, 제품 자체로 배포되는 스킬은 코드 저장소에 유지합니다.
- 보관 위치 변경은 오래된 계획을 다시 승인하거나 운영 코드를 배포한 것을 뜻하지 않습니다.
- 비밀값·고객 원본·DB·미디어·실행 산출물은 이 저장소에 추가하지 않습니다. 필요한 비밀값은 승인된 실행·복구 용도에 따라 양쪽에서 사용하되 교체·복구 기준을 하나로 관리합니다.

## 프로젝트

- [ceoloan](ceoloan/docs/README.md)
- [exdigm](exdigm/docs/README.md)
- [fundkeeper](fundkeeper/docs/README.md)
- [rndlog](rndlog/docs/README.md)
- [ziin](ziin/docs/README.md)
- [venture](venture/docs/README.md)
- [gbrain](gbrain/docs/README.md)
- [im-not-ai](im-not-ai/docs/README.md)
- [kmh-agent-kit](kmh-agent-kit/docs/README.md)

## 이력과 다른 조정실에서 복구

편집할 때 변경 문서와 비밀값 혼입 여부를 검토하고, 해당 경로만 `git add -- <경로>`로 추가해 커밋·push합니다. 기존 사용자 변경을 함께 올리지 않습니다. Git 원격은 비공개 `chaconne67/control-room-docs`입니다.

새 조정실에서는 인증된 Git으로 이 저장소를 `projects/_control-docs`에 clone하고 각 프로젝트의 `docs`를 대응하는 `<project>/docs`에 연결합니다. 이미 있는 자료는 내용과 이력을 비교하기 전에 덮어쓰지 않습니다. 이 문서 저장소의 Git 이력과 원격 저장은 프로젝트 코드·고객자료·비밀값의 백업을 대신하지 않습니다.

원문 79개의 전송 해시를 검증한 뒤, 첫 커밋 전에 키 리터럴 1개 제거·코드 참조 링크 9개 연결·기존 누락 링크 1개 표시·비밀값 보관 규칙을 정리했습니다. `provenance.json`에 원본과 저장본의 SHA-256 및 변경 이유를 구분해 기록했습니다.
