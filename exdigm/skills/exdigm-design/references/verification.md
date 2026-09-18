# UI Verification

## 공통 검수 질문

- 화면만 보고 버튼 결과와 다음 행동을 알 수 있는가?
- 선택지가 같은 위계인지 상·하위인지 배치에서 구분되는가?
- 지금 해야 할 일과 나중에 볼 정보가 분리되는가?
- 라벨·badge·chip이 업무 판단에 필요한가?
- 모바일에서 닫기·scroll·하단 action이 막히지 않는가?

## 검수 절차

1. 원격 `/home/chaconne/exdigm-debug`에서 `scripts/debug_workspace.sh status`와 `run`으로 대상 서버를 준비한다.
2. 실제 브라우저에서 수정한 화면을 연다.
3. 정적 변경은 수정 전후 화면을 캡처하고 디자인 계약과 비교한다.
4. 동적 변경은 [interaction-acceptance.md](references/interaction-acceptance.md)의 클릭 전·처리 중·결과 후 검사와 console/network 확인을 수행한다.
5. 사용자가 screenshot으로 지적한 문제는 같은 route와 비슷한 상태에서 재현해 고친다.

서버 준비, 대상 UI, 브라우저 캡처 중 하나라도 확인하지 못하면 UI 작업을 완료로 보고하지 않는다. 배포에서만 깨지면 개발/배포 build 경로 차이를 먼저 조사한다.

`403` 또는 `/accounts/login/`이면 Gate 6의 SSH 포워딩과 일회성 로그인 정보를 다시 확인한다. 운영 URL로 바꾸지 않는다.
