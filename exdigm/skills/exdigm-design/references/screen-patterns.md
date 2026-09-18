# Screen Patterns

## 프로젝트 메뉴

- 모든 프로젝트 업무는 프로젝트 메뉴 안에서 끝낸다.
- 후보자 검색·바구니·추천 선정은 하나의 Workspace modal 흐름이다.
- 후보자 진행은 한 줄 card list에서 이름·stage progress·setting icon으로 동시에 본다. 상세는 modal로 열고 닫으면 list로 돌아온다.
- 프로젝트 목록과 생성·수정 화면은 같은 바깥 layout(`main max-w 1280`, `px-8 py-8`, `#main-content` 단일 scroll)을 쓴다. 좁은 form 폭은 내부에만 둔다.
- JD file·text는 편집 가능한 원천 입력이다. 공고문·사이트별 게시 데이터는 생성된 읽기 전용 출력이다.
- 생성 output은 source input과 같은 정보 card 안에서 보인다. output이 source와 달라지면 인라인 경고로 재생성을 요구하고 사이트 실행은 숨긴다.

## 후보자 Workspace

- 한 후보자를 연락 → 사전 미팅 → 추천 → 면접 → closing으로 처리한다.
- 현재 단계는 기본으로 열고 다른 단계는 펼침으로 확인한다.
- X, footer 닫기, backdrop, ESC는 같은 닫기 결과를 내고 내부 클릭은 닫히지 않는다.
- modal 내부 card는 form·alert·선택처럼 독립 의미가 있을 때만 쓴다.

## 검색·알림·칸반

- 검색은 voice/text 자연어 입력이 먼저다. 결과 → 바구니 → track 진입은 하나의 modal 흐름이다.
- 모든 알림은 web system notification에 남기고, Telegram은 시간 민감하거나 결정을 요구할 때만 쓴다.
- Application card의 stage progress는 발굴을 제외한 6단계를 보이고, 칸반은 상태별 container/pill variant를 쓴다.

## References와 card hover

- References는 대학·기업·자격증 3-tab과 tab당 table 하나로 구성한다.
- hover lift는 클릭 가능한 card만 쓴다. card를 `a` 또는 `button`으로 표현해 시각과 semantic을 맞춘다.
