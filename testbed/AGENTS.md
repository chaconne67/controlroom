# TestBed 조정실

- 모든 OS에서 `~/controlroom/testbed`를 업무 지침·스킬·문서의 진입점으로 사용한다. 공유 Git은 `git@github.com:chaconne67/controlroom.git`이다.
- TestBed는 FundKeeper의 코스콤 RA 테스트베드 업무다. 실제 코드·실행 서버·DB는 [FundKeeper 지침](../fundkeeper/AGENTS.md)을 따른다. 현재 코드는 main `chaconne@49.247.192.127:/home/chaconne/projects/fundkeeper`, Git은 `git@github.com:reneesoft/fundkeeper.git`의 `master`다.
- 데이터 작업은 main FundKeeper의 기존 MySQL 연결과 `TestBed2` 업무 코드를 사용한다. DB 저장·증권 주문·Drive 업로드·포털 제출은 서로 다른 외부 효과이므로 승인된 업무 범위만 실행한다.
- `skills/testbed/SKILL.md`와 업무에 맞는 하위 스킬을 읽는다. 최종 제출 서류의 정본은 Google Drive `MOA/테스트베드{차수}/준비서류/{전략}`이며 정확한 차수·전략·파일은 실제 Drive에서 확인한다. 조정실 Git에는 고객 원본·인증값을 넣지 않는다.
