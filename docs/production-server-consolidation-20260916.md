# 운영서버 통합 계획 v2 — 새 호스트 준비, DNS는 마지막

작성일: 2026-09-16 (Asia/Seoul)
계획 정본: controlroom/docs/production-server-consolidation-20260916.md
목표 호스트: chaconne@49.247.192.127, hostname main
상태: 신규 서버 준비·검증 승인 · 공개 DNS 미변경 · 운영 데이터 정본과 쓰기 책임 미인계
대상: 기존 DB, Coconut/FundKeeper, RNDLOG, ZiiN, CEO Loan, GBrain 런타임·자료 게이트웨이·필요한 제품 런타임
제외: Exdigm 앱·운영서버·도메인 이전. 공용 DB를 쓰는 Exdigm 소비자의 기존 접속·업무 계약도 보호한다.


> 최신 상태: 2026-09-17 전체 인계·중단·복구 리허설과 별도 서버 cold 복원 결과는 14절을 먼저 읽는다. 준비 검증은 완료했으나 실제 운영 정본·DNS는 미인계다. 12~13절은 이전 시점의 기록으로 보존한다.

## 1. 사용자 결정과 완료 의미

- 기존 DB 호스트는 증설할 수 없으므로 새 호스트 49.247.192.127로 통합한다.
- 기존 서비스와 사용자 작업을 보존하면서 새 서버의 설치·복사·복원·시험·전환 준비를 실행하도록 승인받았다. 같은 준비 승인을 다시 요청하지 않는다.
- 지금 공개 DNS를 바꾸지 않는다. 옛 서버 해지·데이터 삭제·실제 고객 문자/메일·금융 주문·유료 작업도 실행하지 않는다.
- 마지막 단계에는 도메인의 DNS 연결만 바꾸는 것이 목표다. 그 전에 DB/파일이 최신 새 정본이 되고, 모든 쓰기·예약 작업의 책임 인계와 옛 IP의 전달 경로가 실제로 검증되어야 한다.
- 복사본으로 화면이 열리는 상태는 준비 완료가 아니다. DB/파일 최신성·단일 정본·배치·인증·갱신·복구가 확인되지 않으면 “DNS만 남음”이라고 보고하지 않는다.
- 주인님은 최종 인계를 위한 **야간 전체 접속 중단을 최대 5분**까지 허용했다. 준비 중 서비스는 계속 유지한다. 중단 시작부터 전체 서비스 재개까지 300초 안에 끝나는 전환·중단·복귀 절차를 리허설한 뒤 실제 인계에 진입한다. 이 승인은 DNS 변경이나 옛 서버 삭제 승인이 아니다.
- 개발 에이전트·지침·계획·판단은 controlroom에 둔다. 확인된 제품 AI 런타임만 운영 호스트로 옮기며 비밀값은 서버 간 보안 전송으로만 다룬다.
- 2026-09-17 추가 결정: Coconut 02:10 작업은 정상 캐시 생성만 이전한다. 기존 서버에도 없는 `update_gdrive.py` 단계는 별도 과제로 남긴다. `.env`를 Drive에 복사하는 `upload_to_gdrive.py`로 자동 대체하지 않는다.
- 2026-09-17 추가 결정: 야간 인계는 **한국 시각 22시 이후 아무 때나** 실행할 수 있다. 최대 300초와 사전 전체 리허설 조건은 그대로 적용한다. 구 rndnote `49.247.46.171`은 주인님이 삭제 완료와 RNDLOG로의 이전을 확인했으므로 운영 대상·잔여 writer 조사에서 제외한다.
- 2026-09-17 추가 결정: 기존 ChatGPT 구독 계정을 사용하는 Coconut의 짧은 내부 AI 응답 **1회** 시험을 허용했다. 다른 유료 배치·고객 발송·금융 주문 시험 제외 조건은 유지한다.

최소 구현 게이트: 2단계에서 멈춤 — 운영 이미지·Nginx·Certbot·Docker와 기존 제품 배포/자료 게이트웨이 구성을 재사용한다.
근거: 공유 실측의 Compose/Swarm·이미지·마운트·배포 스크립트·예약 작업. 신규 호스트에는 Docker와 Compose가 이미 설치됐다. 별도 관리 플랫폼·Kubernetes·HA를 만들지 않는다.

## 2. 현재 확인 상태와 원본 선택

아래는 공유 실측 시점의 상태다. 한 시점의 연결 수·디스크 여유는 소비자 부재나 대표 최대 부하 통과를 증명하지 않는다.

| 호스트 | 확인된 상태 | 아직 완료가 아닌 항목 |
|---|---|---|
| 신규 main 49.247.192.127 | Ubuntu 26.04 amd64, 16CPU, RAM 약 31.3GiB. Docker 29.8.1, Compose 5.5.1, containerd 2.3.5. 4개 앱·4개 내부 Nginx·공용 입구·격리 PG/MySQL와 지속 복제 대기본 기동. 2026-09-17 00:13 KST root 약 151GiB 여유 | 공개 80은 ACME 전용, 업무 HTTPS는 loopback 시험 포트. 공개 DB·운영 정본 없음. /dev/vdb 200GB는 미포맷 |
| DB 49.247.45.243 | PG16+pgvector, MySQL 8.4.8, ZiiN, GBrain, 자료 디렉터리, Portainer·phpMyAdmin·백업 timer 운영 | 실제 소비자 전체 목록·계정/허용 경로·복구 전체 범위 |
| Coconut 49.247.38.186 | Swarm 앱·Nginx, root cron 9개, claude-max-proxy user service 127.0.0.1:3456 | 제품 AI 의존성과 /openclaw 정상 기준. 설정 대상 18789에는 조회 당시 listener 없음 |
| RNDLOG 49.247.207.147 | Swarm 앱·Nginx, media 약 268MiB, .credential, funding 계열 cron 3개·hermes-gateway 활성 | 실행 주체별 쓰기/발송 경계·AI 런타임 사용 계약 |
| CEO Loan 49.247.205.170 | Compose 앱·Nginx, media 약 181MiB, funding 계열 cron 3개. 옛 로컬 DB 컨테이너 중지 | 배치/발송 범위. 중지 DB를 시작하거나 삭제하지 않음 |
| 구 rndnote 49.247.46.171 | 주인님이 삭제 완료·RNDLOG로 이전 확인. 운영 대상에서 제외 | 클라우드 삭제 기록은 별도 조회하지 않음. 현재 RNDLOG의 실제 앱·DB·자료·cron 경로는 13절에서 확인 |

| 제품 | 원본 소스 HEAD | 먼저 재현할 실제 실행 버전·주의점 |
|---|---|---|
| Coconut | master d0a3ca1d, clean | coconut:20260916133132, mynginx:같은 태그. 실제 image ID/digest·Entrypoint/Cmd 확인. 기동의 자동 migrate 경로를 시험에서 반드시 차단 |
| RNDLOG | main 6395b07, clean | rndlog_app/nginx:20260911013358. company_main, role rndnote, schema rndlog |
| CEO Loan | main efd6b94, clean | latest 태그 대신 실제 실행 image ID/digest 고정. company_main, role ceoloan, schema ceoloan, 기존 SSH 15432 경로 |
| ZiiN | main 427729d, clean | 실행 이미지 revision 9179f77. 최신 HEAD로 새 기능을 배포하지 않고 실제 이미지·컨테이너 유효 설정을 재현 |

- PG 데이터 /mnt/pgdata/prod는 약 6.2GiB다. company_main 약 3GB, gbrain 약 528MiB, ziin 약 8MiB 및 postgres·과거 시험 DB가 관측됐다.
- PG role exdigm은 관리자지만 exdigm이라는 DB는 관측되지 않았다. 이름이나 한 시점의 원격 연결 부재로 Exdigm의 사용 DB·스키마·접속 필요성을 결정하지 않는다.
- 추가 읽기 전용 확인: Exdigm 운영 앱의 DATABASE_URL은 자체 Exdigm_net의 exdigm_db:5432/exdigm을 사용한다. 이 사실은 주 앱의 DB 경로만 확정하며 다른 도구·공용 소비자의 부재를 증명하지 않는다. Exdigm 서비스와 설정은 변경하지 않았다.
- MySQL /mnt/data는 약 19.1GiB로 보존 binlog를 포함한다. fundkeeper 약 174MiB, price 약 1.64GiB와 moa/welgo/test_fundkeeper 등이 있다. 관측 테이블은 InnoDB이며 계정·grant·소비자 매핑은 미완료다.
- RNDLOG companies 약 438MiB·resources 약 16MiB는 DB 호스트의 정본이다. 운영 자료 SSH 게이트웨이는 기본 49.247.45.243와 바인딩된 키/known_hosts를 사용한다.
- Coconut data 약 79MiB, GBrain .gbrain 약 106MiB도 별도 런타임 상태다. DB만 복사하여 이 상태가 보존됐다고 판단하지 않는다.
- 기존 공개 기준선은 Coconut health 200/ok, RNDLOG / 200, ZiiN health 200/{"status": "ok"}, CEO / 302→/accounts/login/다. 로그인·저장·AI·배치 성공은 별도 확인한다.

## 3. 새 호스트의 공식 경로와 저장 책임

- 준비 중 공식 운영 경로는 기존 DNS → 기존 HTTPS 입구 → 기존 앱 → 기존 DB/파일이다. 새 앱은 격리된 복원본만 사용하며 운영 쓰기·cron·외부 효과를 실행하지 않는다.
- 선행 인계 후에는 옛 HTTPS 입구 → 고정 새 IP의 공용 Nginx → 제품 내부 Nginx → 새 앱 → 새 DB/파일 정본으로 연결한다. 마지막 DNS 변경은 이 경로의 첫 입구만 새 IP로 바꾼다.
- 신규 호스트는 설치된 Compose를 사용해 DB와 제품별 프로젝트를 분리한다. 원본 DB의 Swarm은 준비 중 그대로 유지한다. 원본 DB 엔진·스키마·이름의 업그레이드나 통합을 함께 하지 않는다.
- 공용 Nginx만 새 호스트의 웹 80·443을 소유한다. 제품 내부 Nginx는 static/media·인증 후 다운로드 책임을 유지한다. 입구↔제품 frontend 네트워크를 제품별로 분리하고 DB 접속은 허용된 앱/worker만 연결한다.
- 초기 경로는 /srv/consolidation 아래 충돌 없는 제품·DB·파일·시험 디렉터리다. 검증용 복원본과 지속 복제 대기본을 구분하여 시험 쓰기가 인계할 데이터를 바꾸지 않게 한다.
- 현재 root로 준비를 시작할 수 있다. 미사용 /dev/vdb 포맷은 준비의 선행 조건이 아니다. 이미지·복원본·로그·복구본·증분을 합친 실제 사용량과 여유를 계속 측정해 저장 배치를 확정한다.
- DB·SSH 자료 게이트웨이·GBrain은 일반 HTTPS 앱 프록시와 별도 접속 계약이다. 기존 비공개 소비자의 경로·허용 계정·포트를 새 정본에 연결하는 방법을 먼저 검증한다.
- Portainer·phpMyAdmin의 인증·관리 자료를 보존한다. 여러 Portainer 볼륨을 합치지 않으며 관리 도메인/허용 목록은 미정이다. DB/관리 포트를 인터넷 전체에 공개하지 않고 Docker 필터·클라우드 방화벽을 실제 소비자에서 검증한다.

## 4. 승인된 안전 준비와 기존 성공 보존

1. 원본 이미지 ID/digest·유효 환경·마운트·권한·실행 계정·DNS/TLS·cron/worker·외부 연동 기준선을 잠근다. 소스와 실행 이미지가 다르면 실행 버전을 우선한다.
2. 이미지·코드·DB 일관 백업·파일·필수 인증을 SSH/Git/아티팩트 보안 스트림으로 새 호스트에 준비한다. 비밀값을 문서·Git·GBrain·Windows 디스크에 저장하거나 출력하지 않는다.
3. 새 앱의 모든 기동 경로에서 migration·cron·worker·웹훅 수집·운영 DB 쓰기·실제 대외 효과를 차단한다. Coconut은 Entrypoint와 Cmd를 직접 대조해 자동 migrate가 실행되지 않는 기동을 검증한다.
4. 제품 컨테이너는 초기 외부 egress를 차단하고 격리 복원본으로 시험한다. AI/외부 연동이 필요한 검증은 실제 접근 권한·공식 시험 대상·안전한 시험 경로를 확인한 뒤 그 대상만 허용한다. 고객 발송·주문·유료 작업을 시험 성공 조건으로 사용하지 않는다.
5. 새 입구는 먼저 localhost 임시 포트와 SSH 전달/시험 접근 경로로 확인한다. 80·443 공개는 입구의 TLS·route·접근 차단 검증 후에만 하며, 정본/쓰기 책임 인계 전 업무 route는 비활성 상태로 둔다.
6. 로그인·세션·권한·조회/격리 저장·업로드/다운로드·AI·배치를 공식 진입점으로 검증한다. 모든 부모 폴더·UID/GID·단계별 실행 계정을 확인하고 실제 파일 수령/해시를 대조한다.
7. 각 준비 변경 뒤 기존 공개 기준선과 승인된 읽기 전용 소비자 경로를 같은 방법으로 재확인한다. 실패하면 이번 미검증 준비 변경만 격리/복구하고 기존 정본·서비스를 유지한다.

Coconut 원본 deploy.sh는 전체 stack 목록을 제거하므로 새 공유 호스트에서 실행하지 않는다. 전역 stack rm/down/prune·공용 호스트 전체 kill/cleanup을 제품 배포/cron에 반입하지 않는다. 필요한 제품 범위 진입점만 재사용·수정하고 코드 변경은 code-review-loop와 실제 공식 경로 검증을 수행한다.

## 5. 지속 최신성·모든 writer·정본 선행 인계

### 복제와 파일 증분의 열린 조건

| 대상 | 직접 관측 | DNS 전에 확인할 계약 |
|---|---|---|
| PG16+pgvector | wal_level replica, sender/slot 최대 각 10, 기존 slot 없음, archive off, replication hba는 loopback만 허용 | 같은 엔진/확장·역할/권한을 복원하고 전용 복제 역할·안전한 연결을 검증. 일관 초기 백업과 WAL 연속성·수신/적용 위치·지연·WAL 보존/디스크 한계를 확인. 원본 슬롯/허용 경로 변경이 필요하면 영향과 복구를 먼저 확정 |
| MySQL 8.4.8 | log_bin ON, GTID OFF, server_id 1, InnoDB | GTID를 임의 활성화하지 않고 일관 백업과 실제 binlog 좌표를 연결. 새 고유 server_id·복제 계정/권한·접근 제한·좌표 연속성·적용 지연·로그 보존을 검증. 백업 좌표 확보의 잠금/중단 영향도 확인 |
| media·Coconut data·RNDLOG companies/resources | 여러 호스트·볼륨과 SSH 게이트웨이에 분산 | 추가/수정/삭제·권한을 포함한 지속 증분, 마지막 쓰기 잠금 뒤 최종 동기화·해시, DB 참조와 같은 인계 시점 확인. 게이트웨이의 새 호스트·키·known_hosts·경로를 실제 시험 |
| GBrain·제품 AI 상태 | GBrain HTTP 3131 및 .gbrain, 기존 제품 인증·user service 활성 | 실제 역할/소비자·DB·파일·인증·source 선택을 연결. 개발 에이전트와 제품 런타임을 구분하고 새 공식 시험 성공 후 정본/접속 책임 인계 |

복제 로그가 끊기거나 파일/DB 시점이 어긋나면 최신 대기본을 다시 확보한다. 지연 값이 작다는 이유로 새 DB를 승격하지 않으며, 무중단은 실제 쓰기 잠금·진행 작업 배수·접속 전환이 검증되기 전 약속하지 않는다.

### 모든 쓰기와 예약 작업의 경계

- DB별로 옛/새 앱·worker·cron·수집 도구·GBrain·관리/백업 작업·자료 SSH 게이트웨이·진행 중 큐/외부 효과의 실제 소유자를 기록한다.
- RNDLOG와 CEO Loan은 company_main의 서로 다른 role/schema를 사용하지만 공유 자원·실제 작업 대상은 별도로 확인한다. 같은 funding cron 이름 3개가 양쪽에서 활성이라는 사실만으로 둘을 중복이나 같은 책임으로 분류하지 않는다.
- Coconut 가격/계좌/토큰/캐시·kill/cleanup·인증서 작업은 각각 실행 계정·입출력·마지막 완료/진행 위치를 대조한다. 새 호스트 전체를 다루는 정리 작업으로 바꾸지 않는다.
- 단일 정본은 DB와 파일의 쓰기 권한을 한 책임 아래 두는 것이다. 인계 중 옛 정본과 새 정본이 함께 독립 쓰기를 받게 하지 않으며 배치/외부 효과의 실행 소유권도 하나로 유지한다.

### DNS 이전의 실제 인계 순서

1. 실제 소비자와 공유 쓰기 경계, 허용 쓰기 잠금 시간, 새/옛 정본의 복구 방법을 확정한다. Exdigm 소비자가 어떤 DB/스키마·주소를 쓰는지 미확인이면 관련 DB 정본 인계를 보류한다.
2. 지속 복제·파일 증분을 유지한 채 새 제품의 입구/앱/인증/권한·안전한 연동·배포를 격리 시험한다. 필요한 역인계 또는 새 정본 유지 복구도 리허설한다.
3. 인계할 DB/공유 파일 범위의 옛 writer 전체를 잠그고 진행 중 거래·큐·파일 쓰기·외부 효과의 완료/안전한 중단을 확인한다. 완료 여부를 모르는 외부 효과가 남으면 재개하지 않는다.
4. 잠금 뒤 원본의 최종 WAL/binlog 좌표까지 새 대기본 적용을 확인하고 파일·진행 상태를 최종 인계한다. 옛 primary를 차단/대기 상태로 고정한 뒤 새 DB/파일만 쓰기 정본으로 연다.
5. 새 앱/worker/cron/GBrain/자료 게이트웨이가 같은 새 정본을 사용하도록 제품·공유 책임별로 재개한다. 옛 실행 주체 비활성·최신 완료/진행 위치·중복 방지 상태를 다시 확인한다.
6. 옛 제품 HTTPS 입구의 업무 요청을 고정 새 IP에 전달한다. SNI·인증서 검증·Host·신뢰할 forwarded 헤더·WebSocket/SSE·timeout을 유지하고 DNS 이름을 upstream으로 사용해 순환시키지 않는다.
7. Exdigm 등 보호할 기존 DB 소비자는 기존 접속 계약을 유지한 채 검증된 DB/SSH 전달 경로로 새 정본을 사용해야 한다. Exdigm 앱/서버를 옮기거나 미확인 권한 확대를 대신 수행하지 않는다. 성립하지 않으면 관련 인계를 완료로 처리하지 않는다.
8. controlroom의 GBrain 정본 source/접속과 비공개 파일 소비자도 검증 후 새 책임으로 넘긴다. 실제 인계 전 controlroom GBrain proxy는 기존 DB 호스트를 유지한다. 옛 IP/새 IP/기존 도메인·비공개 소비자가 같은 정본을 사용하는지 확인한다.

이 인계는 현재 미실행이다. 정본/쓰기 책임이 섞이거나 안전한 복구를 확인하지 못하면 기존 서비스를 정본으로 유지하고 인계 단계에 진입하지 않는다.

## 6. 도메인·TLS·갱신의 선행 준비

14개 이름의 A는 아직 옛 서비스 IP를 가리킨다. 관측에서 AAAA/CNAME은 발견되지 않았다. DNS 공급자·TTL·CAA·IPv6·DNSSEC·MX/TXT를 다시 잠그고 지금 수정하지 않는다.

| 제품·주소 | 현재 IP | 최종 IP | 독립 인증서 |
|---|---|---|---|
| coconut.ai.kr, www.coconut.ai.kr | 49.247.38.186 | 49.247.192.127 | coconut.ai.kr 및 www |
| rndlog.kr, www.rndlog.kr | 49.247.207.147 | 동일 새 IP | rndlog.kr 및 www |
| rndnote.co.kr 및 www, aishift.kr 및 www | 49.247.207.147 | 동일 새 IP | rndnote.co.kr·aishift.kr 각각 |
| ziin.site, www.ziin.site | 49.247.45.243 | 동일 새 IP | ziin.site 및 www |
| rogeon.kr, www.rogeon.kr | 49.247.205.170 | 동일 새 IP | rogeon.kr 및 www |
| synco.kr, www.synco.kr | 49.247.205.170 | 동일 새 IP | synco.kr 및 www |
| 관리 UI 주소 | 미정 | 확정 시 새 IP | 주소·접근 허용 목록 확정 후 별도 |

- 기존 인증서를 백업한 뒤 2026-09-17 00:15 KST 새 서버에서 7개 독립 인증서를 실제 재발급했다. SAN·키 대응과 14개 이름의 CA/SNI/route 검증을 통과했다. 만료일은 모두 2026-12-15 UTC다. 공개 443은 아직 업무에 연결하지 않았으며 loopback 18443으로 검증했다. 공용 입구의 proxy_ssl_verify_depth 4로 실제 체인을 검증한다.
- rndnote/aishift→rndlog.kr, synco→rogeon.kr, ziin.site→www.ziin.site의 HTTPS 이동과 URI/query/상태를 보존한다. 기존 50MB upload, media 읽기 전용 경로, funding_audio 공개 차단, 세션 secret/OAuth origin·인증 후 파일 경로도 유지한다.
- 웹 입구는 전용 인증서 저장소를 읽기 전용으로 사용한다. 기존 계보/키 저장소를 덮어쓰지 않고 cert-name·SAN·키 대응·파일 권한을 확인한다.
- HTTP-01은 DNS가 옛 IP인 동안 옛 공개 80에 도달한다. 옛 입구의 ACME 경로만 새 중앙 webroot에 전달하는 실제 경로를 확인한 뒤 CA staging dry-run을 수행한다. 업무 요청·HTTPS redirect와 분리하고 양쪽 IP의 도달을 검증한다.
- DNS-01은 실제 공급자 지원·접근 권한이 확보될 때만 대안이다. 로컬 검증 파일 조회나 인증서 복사로 CA 갱신 성공을 대신하지 않는다.
- 중앙 갱신과 nginx -t 성공 뒤 reload hook이 검증된 계보만 소유권을 이전한다. 기존 다른 도메인의 timer/계보는 유지하고 발급 주체 중복을 막는다.
- 옛 캐시 방문자용 HTTPS 입구도 유효 TLS를 계속 제공해야 한다. 전달을 유지하는 동안 갱신이 필요하면 책임자가 만든 인증서의 양쪽 입구 보안 전달·실제 TLS를 검증한다.

기술 근거: [Nginx 도메인 선택](https://nginx.org/en/docs/http/server_names.html), [Nginx HTTPS/SNI](https://nginx.org/en/docs/http/configuring_https_servers.html), [Certbot 발급·갱신](https://eff-certbot.readthedocs.io/en/stable/using.html), [Let's Encrypt 검증 방식](https://letsencrypt.org/docs/challenge-types/).

## 7. 실행 진행표와 통과 조건

| 단계 | 실행과 통과 조건 | 현재 상태 |
|---|---|---|
| A. 새 호스트 기반 | SSH·Docker/Compose·기본 실행 확인, 초기 /srv/consolidation 용량 확보 | 기반 설치·hello-world 완료. 추가 디스크 미할당 |
| B. 원본·소비자 잠금 | 실제 이미지/설정/파일/DB/계정/모든 writer·Exdigm/비공개 의존성·허용 잠금 시간 확인 | 주요 원본 실측 확보, 소비자·권한·업무 기준선은 미완료 |
| C. 격리 복사·복원 | 보안 스트림으로 이미지·일관 DB 백업·파일/인증 준비, migration/cron/egress 차단, 복원·권한 확인 | 운영 이미지의 레이어 대응 확인. PG company_main/gbrain/ziin·역할 및 MySQL 전체 dump 복원 성공. 앱 4개 시험 기동. 업무별 데이터·권한·파일 전체 대조는 진행 중 |
| D. 실제 시험 | localhost/시험 경로에서 TLS·제품 route·세션/권한·파일·격리 업무·안전한 AI/배치 검증 | 14개 이름 TLS/route, Coconut·RNDLOG·CEO 실제 HTTP 관리자 로그인, RNDLOG 공식 SSH 게이트웨이 업로드·다운로드·해시·rollback 통과. 제품 업무·SSO·AI·배치는 남음 |
| E. 지속 최신성·복구 | PG/MySQL 로그 연속성과 파일 증분, 새 정본 유지 복구/역인계, 다른 장애 영역 백업 복원·RPO/RTO 검증 | PG 물리 복제·MySQL binlog 복제, 두 대기본 재기동 후 읽기 전용/복제 유지 통과. 파일 5범위 5분 동기화 활성. 최종 인계/복구 리허설·다른 장애 영역 백업 검증 남음 |
| F. 정본·모든 writer 선행 인계 | 5절 잠금·최종 좌표/파일·옛 primary 차단·새 단일 정본·배치/GBrain/게이트웨이·옛 IP 전달 확인 | 미실행. 기존 정본/cron/공개 서비스 유지 |
| G. DNS만 남음 판정 | 8절 전체 준비 기준선 통과, 옛 IP/새 IP/도메인이 같은 최신 정본 사용, 실제 갱신/배치/복구·Exdigm 보호 확인 | 판정 불가. 단순 snapshot/health 성공으로 통과하지 않음 |
| H. 마지막 DNS 연결 | G 증거와 최종 사용자 지시가 있을 때 확정 14개 이름의 A만 새 IP로 변경, 캐시 기간 양쪽 경로 재검증 | 지금 수행하지 않음. TTL 등 사전 변경도 별도 확정 |
| I. 관찰·후속 정리 | 대표 업무·배치·갱신·복구 주기와 잔여 소비자를 확인하고 controlroom 상태 갱신 | 이전 후 단계. 옛 호스트 해지/삭제는 현 승인 밖 |

안전한 기반 설치·읽기/복사 준비는 독립적으로 계속한다. 실패하거나 미확인인 제품 뒤의 실제 인계는 보류하며, 공유 DB 정본 승격은 그 DB의 소비자·쓰기 경계를 함께 만족해야 한다.

## 8. 준비 완료 검증과 되돌리기

### “DNS만 남음”의 실제 증거

| 검증 범위 | 요구 증거 |
|---|---|
| 데이터 최신성·권한 | 원본 최종 WAL/binlog 적용, DB/파일 같은 인계 시점·집계/해시·UID/GID, 실제 컨테이너·SSH 소비자의 같은 정본 접근, 기존 role/schema 경계 |
| 모든 writer·예약 작업 | 옛 primary/앱/worker/cron/도구의 독립 쓰기 차단, 새 단일 정본·진행 상태·중복 방지, 배치 결과 최신성·안전한 시험 외부 효과 |
| TLS·프록시·인증 | 새 IP의 14개 이름 CA/SAN/SNI, 옛 HTTPS redirect, HTTP-01/DNS-01 실제 dry-run·hook, 양쪽 입구 TLS, Host/forwarded 헤더·세션/OAuth·WebSocket·50MB upload·공개 차단 |
| 제품 공식 경로 | Coconut 업무/가격·계좌·토큰·캐시·제품 AI, RNDLOG/CEO 권한/격리 저장·자료/수집/시험 발송, ZiiN widget·챗봇·리드/알림의 안전한 시험 |
| GBrain·비공개 소비자·Exdigm | 실제 runtime/source/인증·controlroom 접속 인계, 자료 SSH 게이트웨이 파일 수령, Exdigm 담당/승인된 읽기 전용 경로로 접속·업무 계약 동일 확인 |
| 운영·복구 | 한 제품 배포가 다른 앱/DB를 재시작하지 않음, 대표 부하·자원/로그/디스크 한계, 다른 장애 영역의 암호화 DB/파일/키/설정 백업 복원·RPO/RTO, 양방향 전달과 정본 복구 리허설 |

### 복구 범위와 실제 순서

- 준비 중 실패는 새 격리 복원본/설정만 복구하며 옛 정본을 유지한다.
- 인계 후 입구/앱만 복구할 때는 최신 새 DB/파일 정본을 유지하고, 복구할 옛 앱도 그 새 정본에 연결한다. 옛 stale DB/볼륨으로 되돌리지 않는다.
- 데이터 정본까지 옛 호스트로 복귀하려면 공유 DB/파일의 모든 관련 소비자·허용 잠금 시간을 먼저 확정한다. 공유 DB 정본 복구를 제품 단독 롤백으로 강행하지 않는다.

1. 해당 복구 범위의 양쪽 업무 입구를 유지보수 상태로 두고 옛→새 업무 전달을 먼저 해제한다. 새→옛 전달을 함께 켜 순환시키지 않는다.
2. 관련 새 writer 전체를 잠그고 거래·큐·파일·외부 효과의 완료/안전한 중단·최신 진행/중복 방지 상태를 확인한다. 미확인 외부 효과가 남으면 재개하지 않는다.
3. 앱만 복구하면 새 정본 접속을 검증한다. 정본도 복귀하면 새 쓰기까지 포함한 DB 역복제/재시드·파일 역동기화와 최종 좌표/해시를 리허설한 방법으로 검증하고 새 primary를 차단한 뒤 옛 primary만 연다. 예전 dump/snapshot 원복은 사용하지 않는다.
4. 선택한 최신 정본의 앱/worker/cron/게이트웨이만 단일 책임으로 재개한다. 옛 HTTPS 입구를 그 앱에 직접 연결하고 새 공용 입구의 해당 route는 고정 옛 IP로 연결한다. SNI/CA/Host·ACME/갱신 책임을 유지한다.
5. 옛 IP/새 IP/실제 도메인에서 같은 정본·유일 실행 책임·업무/파일·순환 없음 확인 후 필요한 DNS만 원복한다. 새 IP 캐시 전달을 유지하고 배치 결과/최신성·외부 효과 중복을 관찰한다.

최신 데이터 역인계가 성립하지 않으면 옛 stale 정본을 열지 않는다. 새 정본을 유지해 복구하거나 확인된 유지보수 상태를 보존한다. 제품 입구 복구는 다른 도메인을 유지하며 공용 입구 장애는 모든 전환 제품을 제공하는 검증된 공용 설정으로 복구한다. 새 호스트와 옛 ZiiN은 서로 다른 호스트이므로 v1의 같은 호스트 80·443 원복 절차는 적용하지 않는다.

## 9. 열린 전제·controlroom 정보·다음 재개

- 실제 DB 소비자/계정/스키마·Exdigm 기존 주소 유지 경로와 역인계 방법이 아직 열려 있다. PG/MySQL 전용 역할·제한 SSH 경로·초기 좌표·지속 복제는 구축하고 확인했다.
- 모든 writer·양쪽 funding 작업 범위·진행 큐/외부 효과, 자료/GBrain source·인증/user service의 제품 역할과 실제 새 경로를 확정해야 한다.
- 허용 중단은 야간 전체 접속 최대 5분으로 확정됐다. 데이터 손실 없는 인계를 목표로 최종 WAL/binlog·파일 동기화와 쓰기 차단을 검증한다. 장애 복구 RPO/RTO·대표 부하·백업 보관/다른 장애 영역 저장소·전체 복원은 별도로 확인해야 한다.
- 새 호스트 준비 중이라는 상태와 기존 운영 IP를 controlroom 정본/README 색인에 구분해 반영한다. 확인된 RNDLOG/CEO의 company_main·role/schema를 쓰며 새 IP를 이미 운영 중인 주소로 표기하지 않는다.
- 기존 Exdigm 수정/신규 문서 3개와 다른 사용자 작업은 보존한다. 이 작성자 작업은 본 계획만 갱신하며 README 등 다른 파일 변경은 주 에이전트가 별도 처리한다.
- 다음 공식 작업은 D의 격리 업무·자료 게이트웨이 검증, 코드/GBrain 런타임 보존과 B/E의 소비자·쓰기 경계·지속 복제 준비다. 준비 승인을 다시 묻지 않고 안전한 독립 작업을 계속하되 E/F의 열린 조건을 성공으로 가정하지 않는다.

현재 실행: 새 호스트 기반·격리 앱/DB 복원·14개 이름 TLS/기본 route·7개 인증서 실제 재발급·PG/MySQL 지속 복제·파일 증분 동기화 완료. 정본 승격·모든 writer 인계·공개 DNS 변경은 미실행. “DNS만 남음” 상태가 아니다.
검토 상태: v2 신규 호스트안 SHA-256 5EA4E3398DE674DBF6C3E20866EC0CC0B636BC874F1B712613CA09ABAFEB2099를 작성자와 운영/데이터·입구/TLS 두 비평가가 검토했으며 실행 가능한 추가 지적이 없었다. 이후 이 문서의 변경은 실제 진행·검증 증거 갱신이다. 설계 검토 통과가 운영 이전 완료를 뜻하지 않는다.
보존한 v1 판단: 롤백의 전체 writer 잠금·진행 상태 인계, 다른 제품의 공용 입구 보존, 새 IP 캐시의 역방향 전달. 기존 v1 스냅샷/판정 이력은 주 에이전트가 별도 보존했다.

## 10. 실제 준비 증거 — 2026-09-17 00:52 KST

- 새 서버 작업 정본은 `/srv/consolidation/infra`다. 최초 커밋은 `1021c78`이며 후속 설정·검증 수정은 별도 리뷰·커밋 대상이다. 비밀값·DB·자료는 Git 밖에 둔다.
- 새 공개 80은 인증서 HTTP-01 파일과 HTTPS 이동만 제공한다. 업무 HTTPS는 `127.0.0.1:18443`, 추가 시험 HTTP는 `127.0.0.1:18080`이다. 앱/시험 DB 네트워크는 internal이다. 운영 cron과 DB 쓰기 책임은 옛 서버가 유지한다.
- 제품 frontend 네트워크의 입구 `.2`와 자동 주소 `.128/25`를 분리했다. 이 네트워크의 호스트 gateway는 `.128`이다. 복제 전용 네트워크는 `172.30.22.0/24`, gateway `.1`이다.
- 격리 PG에 company_main·gbrain·ziin과 역할을 복원했다. MySQL 전체 백업 322,709,831바이트를 SHA-256 `32004a2f2e09c731472d28c51a8c58e6f140c5f56527715dd68ec3d8d9dc3e6f`로 대조하고 복원했다. 복원 후 FLUSH PRIVILEGES와 실제 앱 연결을 확인했다.
- PG 대기본은 같은 PG16+pgvector 이미지의 `pg_basebackup`으로 약 6.56GB 전체 클러스터를 복제했고 `pg_verifybackup`을 통과했다. 역할 `consolidation_replica_20260916`, 물리 슬롯 `consolidation_main_20260916`, WAL 보존 상한 4GB를 설정했다. 원본 hba/auto.conf 백업은 `/mnt/consolidation-20260916`에 있다.
- MySQL 대기본은 GTID OFF를 유지하고 server_id `20260916`을 사용한다. 일관 백업의 시작 좌표 `binlog.000114:648584166`에서 복제했다. 원본의 60초 초과 transaction 정리 작업이 백업을 종료하는 원인을 확인하여 읽기 전용 전용 백업 계정만 정리 대상에서 제외했다. 기존 작업의 주기·일반 거래 처리 기준은 유지했다. 수정 전 스크립트는 원본 호스트의 같은 백업 디렉터리에 보존했다.
- 복제용 MySQL seed 압축 파일은 322,710,947바이트, SHA-256 `35361d70405330e09a6339a8273ac9885692e795aa844d05961ae263e3c8b768`이며 새 대기본 복원은 460.3초에 완료했다. 전체 복원이 5분을 넘으므로 최종 중단 시간에 dump/restore를 수행하는 방식은 사용하지 않는다.
- 새 DB 두 대기본을 Compose로 다시 만든 후 PG recovery/streaming과 MySQL IO/SQL 복제·read_only·super_read_only를 확인했다. 원본 PG에서 replay 미적용량 0바이트, MySQL에서 지연 0초와 같은 적용 좌표를 관측했다. 다른 시험 앱/DB의 기동 시각은 동일했다. 이 순간의 지연 값은 최종 인계의 최신성 증명을 대신하지 않는다.
- DB 전송은 새 서버에서 옛 DB로 연결하는 제한 SSH service를 사용한다. 새 서버 DB 포트는 인터넷에 공개하지 않는다. 원본 authorized_keys의 기존 키를 보존하고 신규 키에 출발지/목적 포트 제한을 적용했다.
- 파일 standby 5범위는 companies/resources, GBrain 상태, Coconut data, RNDLOG media, CEO media다. 전용 출발지 제한·강제 읽기 전용 rrsync 키를 사용한다. 대상은 `/srv/consolidation/data/files-standby` 아래이며 원본을 삭제하지 않는다. 5분 timer가 활성이다.
- 파일 동기화는 첫 복사와 증분 재실행 모두 5범위 성공했다. timeout 한 건이 나도 다른 범위를 계속 실행하고 실패를 기록하는 검증을 통과했다. 00:13 증분은 약 2초였다. 최종 쓰기 잠금 뒤의 해시·DB 시점 대조와 300초 전환 리허설은 아직 수행하지 않았다.
- 4개 Git bundle을 검증·복원했다. 새 저장소는 `/srv/consolidation/repos/{fundkeeper,rndlog,ceoloan,ziin}`이다. ZiiN 코드 HEAD와 현재 운영 이미지 revision이 달라 실제 운영 이미지를 계속 사용한다. 기존 전역 stack 제거/prune 스크립트는 새 호스트에 활성화하지 않는다.
- 새 입구의 14개 도메인 이름에서 CA/SNI 검증과 기존 HTTP 상태/주소 이동을 통과했다. Coconut·RNDLOG·CEO는 시험 DB에 임시 계정을 만들어 HTTPS CSRF 로그인과 관리자 화면 200을 확인하고 계정/세션을 삭제했다. 이는 실제 고객 SSO와 모든 업무 흐름을 검증했다는 뜻이 아니다.
- RNDLOG 공식 자료 클라이언트로 새 SSH 게이트웨이 health·임시 파일 upload/download·SHA-256 대조·batch rollback을 통과했다. 임의 명령은 거절됐으며 시험 파일은 정리했다. 원본 자료 정본은 여전히 옛 DB 서버다.
- 옛 4개 Nginx의 HTTP-01 경로만 새 80으로 전달하도록 변경하고 nginx -t/무중단 reload·기존 공개 서비스·14개 challenge 응답을 확인했다. Coconut은 호스트 bind 설정에 반영됐다. RNDLOG/CEO/ZiiN의 저장소 배포 원본에도 현재 검증한 것과 동일한 변경을 반영했다. 변경 diff와 원본 컨테이너의 nginx -t를 확인했으며 애플리케이션 재배포는 수행하지 않았다.
- 7개 계보의 CA staging 재설정과 전체 renew dry-run이 성공했다. 복사된 예전 Docker 중지/시작 hook은 새 Certbot의 `--no-directory-hooks`로 제외했다. 실제 재발급 7개가 성공했으며 새 frontend/edge만 nginx -t 후 reload했다. 키 대응·SAN·14개 TLS 경로를 재검증했고 모두 2026-12-15 UTC 만료다. 중앙 갱신 service/timer를 설치하고 service의 실제 갱신 검사·nginx 검사/reload 경로를 통과했다. timer는 책임 인계 전까지 비활성이다. 옛 인증서 운영 책임 인계는 남은 작업이다.
- GBrain 코드·Bun·상태를 보존하고 새 격리 DB에서 공식 CLI의 공용 운영 프로토콜 조회를 확인했다. 새 HTTP 프로세스도 내부망에서 기동했다. 복사된 bootstrap token은 관리자용이며 MCP bearer token으로 간주하지 않는다. 원본과 새 복원본 모두 health·관리자 로그인·인증 후 sources 조회를 통과했고 응답 해시가 일치했다. 원본의 Google 환경 로딩 wrapper를 재사용하여 새 CLI 프로토콜 조회도 확인했다. 실제 조정실 source 전환과 외부 API 기능 검증은 남아 있다.
- 실전 전환용 `production-*` 앱 4개와 입구를 별도 네트워크에 기동했다. 실제 지속 복제 DB를 읽고, files-standby는 읽기 전용으로 마운트한다. 14개 도메인의 TLS/route를 loopback 28443에서 통과했고 각 앱의 옛 DB·인터넷 접속 차단을 실제 socket으로 확인했다. 공개 443과 운영 쓰기는 아직 열지 않았다.
- DB 대기본의 복제망 주소를 PG `172.30.22.10`, MySQL `.11`로 고정했다. 제품용 DB 망은 PG `172.30.40.10`, MySQL `172.30.41.10`이다. 망 추가 뒤에도 두 복제가 정상 기동했다.
- 옛 DB 호스트에 `consolidation-main-compatibility.service`를 준비했다. 기존 5432/3306을 유지하면서 private 35432/33306을 통해 새 대기본으로 연결한다. 기존 Nginx 이미지의 TCP 전달까지 포함한 별도 시험에서 PG recovery=true, MySQL read_only/super_read_only=true 응답을 받았다. 시험 컨테이너는 종료했다. 현재 실제 운영 DB 서비스와 포트는 교체하지 않았다.
- 새 예약 작업 11개는 Coconut 캐시·가격/마스터·토큰·계좌, RNDLOG 3개, CEO 3개, ZiiN 카카오 토큰 갱신이다. 기존 시간대·시각과 명령을 보존하고 Coconut의 고장 난 Drive 단계는 사용자 결정에 따라 제외했다. 원래 시간 제한이 없던 funding/Kakao 명령은 새 임의 제한을 적용하지 않는다. unit/timer·Compose 병합 검증을 통과했으며 모든 업무 timer는 비활성이다. 정본 인계 표식이 없을 때 문자 service를 시작해도 명령이 실행되지 않는 것을 확인했다.
- Coconut 배치의 실제 local 설정 진입점에서도 새 MySQL 별칭과 읽기 전용 복제본 연결을 확인했다. RNDLOG/CEO 예약 명령 6개는 전환용 실제 컨테이너의 --help 진입을 통과했다. 실제 문자·금융 주문·토큰 갱신은 시험 실행하지 않았다.
- 기존 공개 서비스·예약 작업·DB 정본·DNS·조정실 GBrain 접속은 유지한다. 새 인증서 발급과 복제 성공을 근거로 정본 인계나 DNS 준비 완료를 선언하지 않는다.

## 11. 5분 야간 인계의 실행 조건

1. 중단 시간 밖에서 모든 이미지·DB 대기본·파일 증분·인증서·제품별 시작 명령·옛 주소의 전달 경로·예약 작업 인계 명령을 준비한다.
2. 업무/비공개 소비자와 진행 중 작업을 확인하고, 격리 리허설에서 쓰기 잠금부터 전체 재개까지와 승격 전 중단 복귀 시간을 측정한다. 합계 300초 안의 실행 근거가 없으면 중단을 시작하지 않는다.
3. 최종 복제/파일 대조에 실패하거나 남은 시간으로 복귀가 불가능해지기 전에 승격을 취소하고 옛 단일 정본을 재개한다. 오래 걸리는 전체 복원·대량 복사는 이 시간 안에 넣지 않는다.
4. 승격 후에는 새 쓰기가 있으므로 옛 snapshot을 다시 열지 않는다. 검증한 새 정본 유지 복구를 사용한다. 이 경로까지 준비되지 않았으면 승격하지 않는다.
5. 실제 중단 시작/종료 시각·최종 WAL/binlog·파일 검증·writer 소유권·업무 재개 결과를 이 문서에 남긴다. 공개 DNS는 마지막에 별도 전환한다.

## 12. 사용자 중지와 다음 세션 인계 — 2026-09-17

# 운영서버 통합 — 중지 및 다음 세션 인계

기록 시점: 2026-09-17 01:36 KST
상태: **사용자 요청으로 작업 중지. 준비 중이며 DNS만 남은 상태가 아니다.**

## 1. 요청과 승인

- 새 서버: `chaconne@49.247.192.127` (hostname `main`). SSH 별칭 `main`은 없다.
- Exdigm을 제외한 DB·Coconut/FundKeeper·RNDLOG·CEO Loan·ZiiN 및 필요한 GBrain/자료 저장 경로를 통합한다.
- 준비 중 기존 서비스를 유지하고, 실제 데이터·파일·예약 작업 책임을 안전하게 인계한 뒤 마지막에 도메인 연결만 바꾸는 것이 목표다.
- 준비·설치·복사·격리 시험·조정실 정보 갱신은 이미 승인됐다. 같은 준비 승인을 다시 묻지 않는다.
- 최종 인계 시 **야간 전체 접속 중단 최대 5분(300초)**을 허용했다. 전체 전환·승격 전 취소·복귀를 리허설하기 전에는 중단을 시작하지 않는다.
- Coconut 02:10 작업은 **정상 캐시 생성만 유지**한다. 없는 `update_gdrive.py`는 별도 과제로 남긴다. 인증정보가 든 .env까지 복사하는 `upload_to_gdrive.py`로 대체하거나 실행하지 않는다.
- 공개 DNS 변경·옛 서버 삭제·실제 고객 문자/메일·금융 주문은 수행하지 않았다.
- 사용자가 01:34 KST경 작업 중지를 명시했다. 다음 세션이 재개하기 전에는 추가 이전을 실행하지 않는다.

## 2. 다음 세션이 먼저 읽을 정본

- 조정실: `C:\Users\chaconne\controlroom\docs\production-server-consolidation-20260916.md`
- 해당 프로젝트 docs/README와 조정실 카드에 통합 준비 상태와 원본/대상 주소가 반영돼 있다.
- 새 서버 설정: `/srv/consolidation/infra`
- 새 서버 중지 시점 증거: `/srv/consolidation/infra/validation-pause-state.json`
- 복원 시험 중지 기록(옛 DB): `/mnt/consolidation-20260916/offsite/restore-paused.json`
- Windows 작업 폴더: `C:\Users\chaconne\Documents\Codex\2026-09-16\new-chat-3\work`
- 이 폴더의 `stream_transfer.py`는 비밀값/덤프를 Windows 파일로 저장하지 않고 SSH 바이너리 스트림으로 전송한다.
- 개발 에이전트는 조정실에서만 실행한다. 서버에는 SSH로 명령·코드·빌드·시험을 실행한다.

## 3. 중지 후 실제 상태

| 대상 | 마지막 직접 확인 |
|---|---|
| 기존 공개 14개 도메인 | 원래 HTTPS 상태/주소 이동과 CA 검증 유지. HTTP-01 내용도 14개 모두 일치. DNS는 기존 4개 IP 유지 |
| 운영 DB | 옛 DB 서버가 정본. 원본 PG·MySQL·ZiiN·phpMyAdmin·Portainer 계속 실행 |
| PG 새 대기본 | recovery=true. 원본에서 streaming/async, replay lag 0 bytes |
| MySQL 새 대기본 | IO/SQL 모두 Yes, 지연 0초, IO/SQL error 0 |
| 파일 증분 | 5개 범위 5분 timer 활성. 마지막 제한 시간 45초 실행은 2.2초, 전 범위 exit 0 |
| 새 업무 예약 작업 | 11개 timer 모두 disabled |
| 새 인증서 timer | disabled. 수동 service 실행·검사·재읽기는 성공 |
| 새 정본 표식 | `/srv/consolidation/data/production-authority.json` 없음 |
| 실제 야간 중단/승격 | 실행하지 않음 |
| 격리 복원 시험 | 사용자 중지에 따라 시험 PG/MySQL 컨테이너 모두 stopped. MySQL 복원은 부분 상태 |
| 미완료 코드 리뷰 | 새 인프라 전체 code-review-loop와 커밋이 남음. 단위 검증을 전체 리뷰 완료로 간주하지 않음 |

DB/파일 복제를 유지한 것은 대기본 최신성을 보존하기 위한 현재 준비 상태다. 새 업무 worker·cron은 켜지 않았다.

## 4. 실제 경로와 준비물

### 호스트

| 이름 | SSH/IP |
|---|---|
| 기존 DB·ZiiN·GBrain | `DB` / 49.247.45.243 |
| Coconut | `coconut` / 49.247.38.186 |
| RNDLOG | `rndlog` / 49.247.207.147 |
| CEO Loan | `ceoloan` / 49.247.205.170 |
| 신규 | `chaconne@49.247.192.127` |
| 구 rndnote | 49.247.46.171. 2026-09-17 주인님이 삭제 완료와 RNDLOG 이전 확인. 운영 대상에서 제외. 13절 참조 |
| 제외된 Exdigm | 49.247.202.197. 주 앱은 자체 exdigm_db를 사용함을 읽기 전용 확인 |

SSH는 `BatchMode=yes`, `StrictHostKeyChecking=yes`를 사용한다. 새 서버 Docker는 `sudo -n docker`가 필요하다.

### 신규 런타임

- Ubuntu 26.04, 16 CPU, RAM 약 31.3 GiB. Docker/Compose 설치 완료.
- `migration-data`: 쓰기 가능한 격리 시험 DB. 운영 정본이 아니다.
- `migration-replicas`: 지속 복제되는 PG/MySQL. 실제 인계 대상이며 현재 읽기 전용이다.
- `migration-*`: 격리 앱·입구·GBrain 시험.
- `production-*`: 실제 복제 DB를 읽는 전환 대기 앱 4개·입구·GBrain. 파일은 읽기 전용, 앱 외부 통신 차단.
- 공개 80은 ACME/HTTPS 주소 이동용. 시험 입구는 loopback 18080/18443, 전환 대기 입구는 loopback 28080/28443.
- 공개 443·공개 DB 포트는 운영용으로 열지 않았다.
- `compose.activate.*.json`은 준비된 인계용 덮어쓰기 설정이다. **아직 적용하지 않았다.**
- `compose.activate.replicas.json`은 MySQL 승격 후 재시작에서도 읽기 전용/복제 자동 재개로 돌아가지 않도록 만든 설정이다. 승격 절차와 함께 추가 검증해야 한다.
- `networks.json`에 실제 20개 네트워크를 기록했다. `ensure-networks.py`는 없는 망만 만들고 기존 망의 subnet/gateway/internal/주소 범위를 검증한다. 현 상태에서 20개 모두 일치.
- 예전 `production-networks.json`은 `networks.json`으로 통합했다.
- 추가 디스크 /dev/vdb 200GB는 미포맷이며 건드리지 않았다.

### DB 복제

- PG16+pgvector, 물리 복제 slot `consolidation_main_20260916`, 전용 replication role.
- PG 대기본 `data/postgres-standby`, 새 복제망 IP 172.30.22.10, 제품망 172.30.40.10.
- MySQL 8.4.8, GTID OFF를 유지하고 binlog 좌표로 복제. 새 server_id 20260916.
- MySQL 대기본 `data/mysql-standby`, 복제망 172.30.22.11, 제품망 172.30.41.10.
- 새 `consolidation-db-transport.service`가 SSH로 옛 DB localhost 포트를 전달한다.
- 비밀번호·원본 환경·키는 `/srv/consolidation/secrets`에만 있다. 출력/문서/Git에 값을 넣지 않는다.
- 옛 DB의 3분 간격 장기 거래 정리 스크립트가 정합 백업을 죽이던 기존 동작을 확인했다. 이번 전용 읽기 전용 백업 계정만 제외하도록 좁게 수정했고 전체 MySQL dump 성공을 확인했다. 이 원본 스크립트 전체에는 비밀번호가 있으므로 cat/전체 diff 출력 금지.
- 원본 스크립트 백업: `/mnt/consolidation-20260916/kill_stuck_trx.sh.before-backup-exclusion`. 이 패치의 최종 범위 리뷰·기록도 남아 있다.

### 파일

- `sync-files.py`가 workspace(companies/resources), GBrain 상태, Coconut data, RNDLOG media, CEO media를 각각 제한된 rsync 키로 복제한다.
- 목적지: `/srv/consolidation/data/files-standby`.
- 각 소스의 forced command는 범위별 rrsync 읽기 전용이다.
- 이번 검토에서 정본 인계 뒤 옛 파일로 덮는 경로를 막았다. service ConditionPathExists와 스크립트 모두 정본 표식이 있으면 동기화를 거절한다.
- `--deadline-seconds 45` 지원. GNU timeout이 rsync/SSH 프로세스 그룹의 시간을 제한한다. 실제 정상 실행 2.2초.
- 정본 표식 직전에는 timer와 진행 중 sync를 명시적으로 멈추고 마지막 파일 장벽을 확인해야 한다. 표식만으로 이미 시작된 작업의 종료를 대신하지 않는다.

### 인증서와 웹

- 7개 독립 인증서, 총 14개 이름: coconut.ai.kr / rndlog.kr / rndnote.co.kr / aishift.kr / rogeon.kr / synco.kr / ziin.site 각각 www 포함.
- 7개 모두 실제 발급 성공, 2026-12-15 UTC 만료. 키 대응·SAN·14개 CA/SNI/route 검증 통과.
- 4개 Certbot 계보 묶음 모두 renew dry-run 성공. 원본의 Docker 중지/시작 hook은 새 Certbot에서 실행되지 않도록 제외.
- `renew-certificates.sh`는 실행 중인 시험/전환 대기 Nginx를 모두 검사하고 재읽는다. 원래 시험 입구만 재읽던 문제를 수정했고 실제 service exit 0.
- 원본의 ACME 경로는 local webroot 우선, 없을 때 고정 새 IP로 전달한다. 업무 HTTPS는 그대로다.
- 기존 인증서 갱신 책임·옛 HTTPS 입구의 새 서버 전달·최종 공개 80/443 인계는 아직 남아 있다.
- Coconut health 검증 경로는 **/health/**다. /health는 정상 301이므로 경로를 혼동하지 않는다.

### 자료 게이트웨이

- 새 `/home/chaconne/projects/rndlog`은 아직 **격리 검증용** `/srv/consolidation/data/rndlog-workspace`를 가리키는 symlink다.
- 인계 시에만 `files-standby/workspace` 정본으로 바꾼다.
- 직접 새 게이트웨이: 실제 공식 클라이언트 upload/download/hash/rollback 및 임의 명령 거절 통과.
- 옛 DB에 `/home/chaconne/consolidation-20260916/workspace-storage-forward` 준비.
- 전용 키: 같은 디렉터리의 `workspace-forward-ssh`, 새 호스트에 from=49.247.45.243 + restrict + 실제 gateway forced command로 제한.
- 이 두 번째 SSH 전달 경로도 health/upload/download/rollback/임의 명령 거절 통과. 시험 파일 SHA-256: a7471820f6c267d3467ef9ca5fad1cba9d7bb877fb3558db31bc11bc6798640c.
- 실제 원본 authorized_keys의 운영 gateway command는 아직 바꾸지 않았다. 합성 시험 폴더는 정리 완료.

### 기존 DB 주소 호환

- 옛 DB `consolidation-main-compatibility.service` 활성. 원래 운영 5432/3306을 건드리지 않고 private 35432/33306을 새 읽기 전용 대기본으로 전달.
- 기존 PG 서비스는 host publish, MySQL은 Swarm ingress publish다. 단순 서비스 scale 0 + 포트 바인딩으로 바꾸면 계약을 깨뜨릴 수 있다.
- 기존 Swarm 서비스 이름/망/publish를 보존한 Nginx TCP proxy 교체 방식을 준비 중.
- 원본 service inspect는 옛 DB `/home/chaconne/consolidation-20260916/{CentralDB_postgres,db_mysqldb}-before-cutover.json`에 비공개 보관.
- `{postgres,mysql}-compatibility-nginx.conf`와 결과 `compatibility-rehearsal-results.json`이 같은 디렉터리에 있다.
- 격리 Swarm 서비스에서 원본 DB → 새 읽기 전용 DB → 원본 DB의 실제 질의 확인:
  - PG 전환 14.4초 / 복귀 10.1초.
  - MySQL 전환 15.1초 / 복귀 6.8초.
- 시험 서비스/망 제거 완료. 실제 운영 Swarm 서비스는 교체하지 않았다.
- Docker service update에서 같은 target을 --mount-rm과 --mount-add로 동시에 주면 새 mount도 빠졌다. **같은 target 교체는 --mount-add만 사용**하는 경로로 수정·재시험했다.
- 이 부분 시험은 전체 300초 인계나 승격 후 복구의 검증을 대신하지 않는다.

### GBrain

- 새 validation과 production prewarm 모두 기존 Bun/CLI/Google 환경 wrapper를 재사용한다.
- `compose.production.gbrain.json`은 실제 PG 대기본과 files-standby/gbrain-state를 읽기 전용으로 사용한다.
- 공식 CLI 공용 프로토콜 조회 성공, SHA-256 13e52b1fe824c71c2cfc1ed1dd9325ce0561b0668dbe0ce164b336adc3a71a7e.
- HTTP health·관리자 login·인증 후 sources 조회 200, 원본/검증본과 동일 해시.
- bootstrap token은 관리자용이다. MCP bearer token으로 사용하거나 새 고객/클라이언트 토큰을 재발급하지 않는다.
- `compose.activate.gbrain.json`과 전용 outbound 망은 준비만 했다.
- 현재 조정실 GBrain CLI의 권위는 여전히 옛 DB다. 카드의 CLI 주소를 미리 바꾸지 않는다.
- 원본 GBrain 일일 03:30 memory-distill은 옛 .codex 개발 대화 이력을 읽는다. 그 이력은 새 서버로 복사하지 않았다. 개발 기록 작업과 제품 GBrain 런타임을 혼동해서 빈 새 이력으로 작업을 켜지 않는다.
- GBrain HTTP 기존 localhost3131 소비자/CLI·상태·갱신 책임 인계와 안전한 외부 연동 검증이 남아 있다.

## 5. 다른 서버에서 진행한 복구 시험 — 부분 완료

- 새 읽기 전용 대기본에서 PostgreSQL company_main/gbrain/ziin + globals, MySQL 전체 논리 백업 생성 성공.
- 백업 시각: 2026-09-16T16:00:58Z. 준비 복구 시험용이며 **최종 인계 시점 DB/파일 일관 snapshot이 아니다.**
- DB/파일/설정/비밀값/인증서/코드 복구 묶음을 GPG 공개키로 암호화하여 옛 DB에 보관했다.
- 암호문: `/mnt/consolidation-20260916/offsite/recovery-20260916T160058Z.tar.gpg`
- 크기 3,940,779,037 bytes; SHA-256 aef41e68ad9fad5e59dfbfc1c824073b4b4c77c4ab5412b360435fba7bf796d3.
- 복구 키는 옛 DB `/mnt/consolidation-20260916/recovery-keyring` (root 전용)에 있다. 값은 출력하지 않는다.
- 지문: 0F3D06E1AE97A45C967D09FBAF971ADE37BC528D.
- 암호문 checksum·GPG 무결성/복호화·추출 성공.
- 추출 경로: `/mnt/consolidation-20260916/offsite/restore-20260916T160058Z`.
- 시험 컨테이너: `consolidation-recovery-postgres`, `consolidation-recovery-mysql`. 각각 network=none, CPU 1, RAM 2GB, 전용 /mnt 데이터 폴더. **현재 둘 다 중지됨.**
- PG company_main: 전체 restore 성공 367.3초, 사용자 테이블 103개.
- PG globals: 원본 최초 관리자 이름 **exdigm**으로 initdb해야 GRANTED BY 권한 관계가 보존됐다. initdb가 이미 만든 정확한 `CREATE ROLE exdigm;` 한 줄만 제외하고 나머지를 ON_ERROR_STOP으로 복원했다.
- GBrain: 원본 event trigger `auto_rls_on_create_table` 소유자는 gbrain인데 현재 gbrain은 NOSUPERUSER다. 복구 시험 DB에서만 잠깐 SUPERUSER를 부여해 전체 restore 후 **finally에서 NOSUPERUSER로 되돌렸다**. 원본과 같은 owner/rolsuper=false 확인. 복원 17.7초.
- ZiiN: restore 성공 0.8초.
- MySQL: import 도중 사용자의 중지 요청으로 시험 DB를 정지했다. import exit 1/gzip -13은 이 정지에 따른 결과다. 부분 데이터이며 mysqlcheck는 실행하지 않았다.
- 성공한 PG 복원을 다시 할 필요는 없다. 다음 세션은 중지 기록을 읽고 **시험 MySQL만** 새 전용 데이터 디렉터리에서 전체 import 후 mysqlcheck/앱 권한 검증을 재개한다.
- `work/restore-offsite-backup.py`에는 최초 관리자 보정까지 반영돼 있지만, GBrain event trigger 소유자 복구 순서와 재개 경로는 아직 합쳐지지 않았다. 그대로 재실행하면 안 된다.
- 원본 DB·실제 새 대기본에 권한을 올리거나 dump를 복원한 적은 없다.

## 6. 저장소 상태와 보존해야 할 기존 작업

- 신규 infra Git base: `1021c78f67c3c266c7aa654a50fbc6aa8299e5b7`.
- 이후의 설정/스크립트/증거 파일은 **미커밋**이다. 다음 세션에서 git status/diff와 pause-state를 대조하고 보존한다.
- `README.md`는 초기 검증 전용 상태 설명으로 낡아 있다. 실제 production prewarm/replication/ports/activation/복구 경로를 반영해야 한다.
- 일부 발견 수정·단위 검증은 끝났지만 인프라 전체 code-review-loop는 완료하지 않았다.
- 원본 ACME 설정 3개는 범위 리뷰·nginx -t·공개 기준선 확인 후 커밋/게시 완료:
  - RNDLOG: 67d07991e755ab146e73fbbf35395d2f65699ec9
  - CEO Loan: e9c013929378815c7294f52c9e76c330ef285ce9 (remote 이름 ceoloan; origin은 로컬 bundle)
  - ZiiN 게시: 3f1d029ba75a5f96a62bbc714bc0099722bcfbe5
- ZiiN 기존 HEAD 427729d에는 미게시 사용자 기능 변경이 있었다. 이번 7줄 ACME 변경만 원격 9179f77 위에 게시하고, 현지 작업에는 그 게시 커밋을 merge했다. 현재 현지 HEAD 43e79e3705f6763fa1fd5a61f774d0649f1c06b3, clean. 기존 기능은 추가 배포/게시하지 않았다.
- 새 호스트에 복사한 제품 소스는 초기 commit을 유지한다. 현재 운영 이미지도 바꾸지 않았다. 배포 전 원본/새 복사본/실제 이미지의 차이를 다시 확인한다.
- 조정실의 다른 미게시 사용자 커밋은 유지하며 이번 문서만 별도 게시한다. `work/controlroom-publish`는 게시용 분리 worktree다. 전체 로컬 main을 무심코 push하지 않는다.

## 7. 다음 세션의 순서

1. 이 기록과 정본 계획, 실제 Git/컨테이너/복제/예약 작업 상태를 대조한다. 중지된 시험과 운영 서비스를 혼동하지 않는다.
2. 중지된 **격리 MySQL 복구 시험**만 재개한다. PostgreSQL 권한/이벤트 트리거 복구 순서를 공식 복구 절차에 통합한다. 백업 전체 검증 전에는 복구 완료라 하지 않는다.
3. 새 infra의 리뷰를 base 1021c78부터 다시 마무리하고 필요한 수정·실제 검증·설명서·커밋을 완료한다. 원본 장기 거래 정리 패치도 좁게 검토한다.
4. 옛 HTTPS → 새 고정 IP 전달, 실제 client IP, TLS/SNI, streaming/websocket, 기존 인증서 갱신 책임을 준비·검증한다.
5. GBrain HTTP/CLI·자료 symlink/forced command·원본/새 예약 작업·백업·관리 서비스의 실제 소유권 인계와 필요한 안전한 외부 기능 검증을 완료한다.
6. 모든 writer의 잠금/진행 작업 배수, 최종 WAL/binlog/파일 장벽, 옛 primary fencing, 새 승격·재시작 계약을 준비한다. 새 쓰기 후 옛 snapshot을 다시 열지 않는다.
7. 전체 서비스의 300초 전환·승격 전 취소·새 정본 유지 복구를 격리 리허설하고 시간을 측정한다. 이 근거가 없으면 실제 중단을 시작하지 않는다.
8. 준비가 모두 검증된 뒤 승인된 야간 인계에 들어간다. **공개 DNS는 그 뒤 마지막 단계로 남긴다.**

이 기록은 작업 중지 인계다. 통합 완료·전체 복구 통과·DNS만 남음으로 해석하지 않는다.

## 13. 2026-09-17 재개 후 확인·준비 결과

이 절은 12절의 중지 당시 기록을 갱신한다. 운영 DB·파일의 정본, 공개 DNS, 기존 공개 업무 입구와 조정실 GBrain 접속은 여전히 기존 서버에 있다. 승인된 실제 인계 시간은 한국 시각 22시 이후이며, 전체 300초 리허설과 새 쓰기 보존 복구가 통과해야 실행한다.

### 삭제된 rndnote와 현재 RNDLOG

- 구 `49.247.46.171`의 삭제와 이전 완료는 주인님 확인에 따른 사실이다. SSH 시간 초과만으로 삭제를 확인한 것은 아니며 클라우드 관리 기록은 조회하지 않았다. 이 서버를 미확인 운영 writer로 남기지 않는다.
- `49.247.207.147`의 실제 Swarm `Rndnote_app`은 `main.settings.deploy`와 Gunicorn으로 실행 중이다. 실제 앱의 SQL 연결은 `company_main` / `rndnote`이며 미디어 볼륨에는 253개 파일이 있다.
- `/home/work/rndnote`는 `/home/chaconne/rndlog`로 연결된다. 현재 저장소 HEAD는 `67d07991e755ab146e73fbbf35395d2f65699ec9`이며 clean이다. 이전 계획의 소스 HEAD와 달라졌으므로 신규 서버의 고정된 운영 이미지를 최신 소스로 바꾸지 않는다.
- RNDLOG와 옛 rndnote·aishift의 www 포함 6개 A 레코드는 모두 `49.247.207.147`이다. RNDLOG 고객 회사 자료는 설정대로 공용 DB `49.247.45.243`의 SSH 자료 게이트웨이를 사용한다. 이는 삭제된 서버에 의존하는 경로가 아니다.
- RNDLOG의 CEO 동기화·문자 발송·문자 전달 조회 cron 3개가 원래 시각에 등록돼 있다. 현재 실행 코드·설정에서 삭제된 IP를 찾지 못했다. 고객 문자나 메일은 시험 발송하지 않았다.

### 다른 서버에서의 암호화 백업 복원

- 고정된 준비 백업 `recovery-20260916T160058Z.tar.gpg`의 SHA-256과 성공한 PG 복원을 보존한 상태에서 MySQL 전체 import를 재개했다. 실제 인증된 TCP `SELECT 1`로 시작 준비를 확인하여 임시 시작 프로세스의 잘못된 성공 판정을 제거했다.
- 이미지에 없는 `mysqlcheck` 실행 파일 대신 설치된 기본 `mysql` 클라이언트의 동일한 `CHECK TABLE` 명령을 사용한다. import 완료 기록을 검사하는 재개 진입점을 공식 복구 스크립트에 통합하여 성공한 import를 다시 실행하지 않았다.
- 최종 결과 `/mnt/consolidation-20260916/offsite/restore-results-20260917T045611Z.json`: MySQL 테이블·뷰 1,818개 검사 모두 성공, 실제 앱 계정으로 fundkeeper·price 테이블 조회 성공. PG company_main 103개 사용자 테이블과 GBrain 이벤트 소유자·NOSUPERUSER 상태를 확인했다. 시험 컨테이너 두 개는 종료했고 복구 데이터는 보존했다.
- 복구 스크립트의 현재 저장 커밋은 main infra `c133267`이다. 이번 결과는 2026-09-16 준비 백업의 데이터 복원 검증이며 최종 인계 시점의 DB/파일 일관 백업 또는 전체 서비스 300초 리허설을 뜻하지 않는다.

### 옛 HTTPS 입구의 새 서버 전달 준비

- 네 옛 서버에서 별도 loopback `39443` 시험 컨테이너를 사용하고 새 서버의 제한된 임시 `29443` 입구로 전달했다. 실제 옛 공개 `443`은 바꾸지 않았다. 최종 설정은 새 고정 IP `443`으로 전달한다.
- 14개 도메인의 경로·쿼리 28건에서 원본과 응답 상태·주소 이동·CA/SNI 검증·HTTP 버전이 일치했다. 4개 제품의 요청 크기 경계 8건과 각 전달 구간의 실제 방문자 IP 보존·위조 IP 거절을 확인했다. 인증된 모든 업무 업로드나 실제 WebSocket/SSE 기능 검증으로 확대 해석하지 않는다.
- 옛 입구가 여러 인증서 이름을 하나의 고정 IP로 전달할 때 TLS 세션 재사용 때문에 이름 불일치가 발생했다. 동일 시험에서 16건 중 7건 실패를 재현했고 공통 옛 전달 설정 한 곳에서 세션 재사용을 끈 뒤 16건 모두 통과했다. 잘못된 SNI는 실제로 거절됐다. 새 내부 입구의 기존 동적 전달 설정에는 불필요한 동일 패치를 남기지 않았다.
- Coconut의 기존 Nginx 시작 wrapper는 옛 앱 응답을 기다리므로 최종 전달 컨테이너는 검증한 직접 Nginx 시작 명령을 사용해야 한다. 기존 앱의 재시작·기능 배포는 수행하지 않았다.

### DB와 GBrain 준비 설정

- 새 MySQL 대기본·승격 정의에서 원본 `innodb_lock_wait_timeout=15`, `wait_timeout=600`, `interactive_timeout=600`, `innodb_print_all_deadlocks=ON`을 보존했다. 실제 전후 조회와 앱 SQL 접속, 복제 IO/SQL 정상·읽기 전용 유지, 다른 앱 시작 시각 보존을 확인했다. 원본 이벤트는 0개이며 이벤트 스케줄러는 준비 상태 OFF, 실제 인계 정의에서는 원본처럼 ON이다.
- 새 호스트 CLI는 기존 컨테이너의 Bun·Google 환경 로딩을 재사용하는 `/srv/consolidation/infra/gbrain-host`로 연결된다. 공식 공용 프로토콜 get 성공과 원본/새 조회 결과 SHA-256 `13e52b1fe824c71c2cfc1ed1dd9325ce0561b0668dbe0ce164b336adc3a71a7e` 일치를 확인했다.
- 전환 대기 GBrain의 내부 HTTP health는 200이다. 준비 상태는 내부망과 읽기 전용으로 유지한다. 실제 인계 정의의 private `127.0.0.1:3131`과 별도 외부 API 망을 임시로 사용하여 새 HTTP health, 옛 DB의 별도 SSH 전달 포트, 기존 Google 인증으로 모델 목록 조회 200을 확인했다. 내용 생성·유료 시험을 하지 않았으며 시험 후 원래 내부망·읽기 전용으로 복귀했다.
- 옛 DB의 별도 `gbrain-forward` → 전용 제한 SSH 키 → 새 `gbrain-ssh-gateway` → `gbrain-host` → 기존 컨테이너 CLI 경로에서 같은 프로토콜 조회 결과를 확인했다. 임의 셸 명령은 거절된다. 원래 CLI 심볼릭 링크·기존 HTTP 3131·조정실 카드는 유지했고 새 전달 systemd 단위는 준비·검사만 했다.

### 격리 데이터·앱 전환과 새 쓰기 보존 복구

- 원본 운영을 멈추지 않고 새 서버의 실제 읽기 전용 대기본만 25.7초 중지하여 두 쌍의 별도 DB/파일 복제본을 만들었다. 경로는 `/srv/consolidation/work/handoff-rehearsal-20260917`이며 이 데이터는 운영 정본이 아니다. 복사 후 실제 대기본 PG 복구 상태·MySQL 읽기 전용/복제 정상과 다른 컨테이너 시작 시각 보존을 확인했다.
- 격리 OLD 쌍은 쓰기 가능, NEW 쌍은 PG 스트리밍 복제·MySQL IO/SQL 복제와 읽기 전용으로 준비했다. 실제 운영 이미지의 앱을 OLD 복제본에 연결하고 외부 연결은 내부망으로 차단했다.
- Coconut·RNDLOG·CEO Loan은 실제 HTTPS CSRF 로그인과 세션을 시험했다. ZiiN 운영 버전의 URL 설정에는 로그인 화면이 없으므로 기존 `/`·`/health/`와 DB의 시험 기록을 검증했다. 없는 로그인 기능을 추가하거나 성공으로 보고하지 않는다.
- RNDLOG의 공식 `store_customer_upload`와 `open_asset_download`를 사용하여 실제 SSH 자료 게이트웨이에 시험 파일을 저장하고 DB 정보·크기·SHA-256·수신 내용을 확인했다. 시험용 계정과 고객사·파일은 격리 복제본에만 존재한다.
- `rehearse-handoff.py abort-before-promotion`: 쓰기 앱 중지·거래 배수·최종 WAL/binlog 적용·2,320개 일반 파일과 소유자/권한 대조 뒤 OLD 정본으로 재개 **13.558초**, NEW는 읽기 전용 대기 상태 유지.
- `rehearse-handoff.py promote`: 같은 최종 장벽 뒤 OLD 두 컨테이너를 중지하고 재시작 정책 없음·데이터 읽기 전용 마운트로 다시 만들었다. PG native promote와 MySQL 승격 설정을 적용하고 NEW 앱·기존 세션·공식 파일 다운로드 검증까지 **30.120초**.
- `rehearse-handoff.py recover-new`: NEW에 새 파일과 DB 정보를 추가한 뒤 NEW DB·앱을 중지/재시작하여 새 기록·기존 파일·기존 세션 보존을 확인 **13.994초**. 옛 snapshot을 다시 쓰기 정본으로 열지 않았다.
- 시험 후 `cleanup`으로 앱을 준비 원래 설정에 복귀하고 자료 게이트웨이 symlink를 `/srv/consolidation/data/rndlog-workspace`로 복원했다. 격리 DB 4개는 모두 중지했고 자료·결과는 보존했다. 실제 `production-authority.json`은 없으며 실제 복제 대기본은 계속 읽기 전용이다.
- 위 시간은 **격리 DB/앱 구간**이다. 실제 옛 공개 전달·비공개 DB 접속·cron/GBrain 운영 책임 인계를 묶은 전체 300초 리허설로 보고하지 않는다. 결과는 main infra `validation-handoff-native-results.json`을 따른다.

### 예약 작업과 원본 일일 백업 보존

- 원본 Coconut 4개 제품 작업에는 실행 제한 시간이 없다. 새 준비 단위의 임의 31/61/3/6분 제한을 제거하여 원본처럼 `TimeoutStartSec=infinity`로 보존했다. 11개 제품 timer는 모두 비활성이고 정본 인계 표시가 있어야 작업을 실행할 수 있다.
- 옛 DB의 실제 일일 백업은 chaconne cron **03:40 KST**의 `/home/chaconne/bin/backup-ceo-loan-db.sh`다. 이 파일을 그대로 재사용하고 새 PG 컨테이너 선택과 전용 백업 폴더만 환경으로 지정한다. 보존 기간 14일, 완료 파일의 native 목록 검사와 완료 후 rename, 기존 cron처럼 재부팅 뒤 누락 작업 자동 실행 없음·시간 제한 없음으로 준비했다.
- 새 읽기 전용 대기본에서 원본 스크립트로 `/srv/consolidation/work/daily-backup-rehearsal-20260917/company_main_20260917143352.dump`를 생성했다. **570,841,838 bytes**, 50.9초, `pg_restore --list` 성공. 빈 시험 폴더에서 실행하여 기존 백업 이력을 삭제하지 않았다. 새 timer는 비활성이고 옛 cron은 유지 중이다.

### 인증서의 중앙 갱신과 옛 입구 전달

- 기존 rsync와 Nginx 재읽기 기능을 재사용하는 `distribute-certificates.py`·`certificate-receiver.py`를 준비했다. 전용 키는 새 고정 IP에서 인증서 archive/live 쓰기, 고정된 Nginx 검사·재읽기와 원본 인증서 복구만 허용하며 임의 명령은 실제 거절됐다. 기존 SSH 키 내용·소유자·권한을 보존했다.
- 원래 인증서 archive를 덮어쓰지 않고 같은 내용이면 기존 번호를 재사용하거나 새 번호로 추가한다. 원본의 private 복구 묶음을 옛 서버에 보존하고 새 archive 해시를 확인한 뒤 live 연결을 바꾼다. 실패하면 원본 live 연결을 복구한다.
- 네 옛 실제 TLS 입구에서 중앙 인증서 선택, 기존 archive/디렉터리 권한 보존, Nginx 검사·재읽기와 컨테이너 시작 시각 보존을 확인했다. 실제 14개 도메인의 CA·호스트명·응답·DNS가 유지되고 중앙 인증서 leaf가 일치한다. 유효기간은 2026-12-15다.
- 중앙 갱신 스크립트에 전달 단계를 연결하고 systemd 단위에 실제 정본 표시 조건을 추가했다. 새 timer는 비활성이다. 실제 인계에서 옛 갱신 실행 주체를 비활성화해야 갱신 책임도 완료다.

### 기존 Coconut 제품 AI 런타임의 연결과 1회 응답 검증

- Coconut 제품 AI의 원본 운영 이미지와 새 동일 이미지 모두 `/usr/local/bin/codex --version`에서 `/usr/bin/env: node: No such file or directory`·종료 127을 확인했다. 이미지에는 launcher만 있다. 원본 Coconut 앱과 이미지는 보존하고, 옛 DB 서버에 이미 설치된 Codex CLI 0.153.4의 정적 Linux 실행 파일과 동봉 자원 6개를 재사용했다. 약 335MB를 서버 간 전송했고 수신 해시·정적 실행 파일·기존 실행 옵션 지원을 확인했다.
- 새 Coconut에 `/srv/consolidation/data/product-codex-0.153.4`를 읽기 전용으로 연결하고 `CODEX_BIN=/opt/product-codex/bin/codex`를 지정했다. 원본 이미지 `sha256:f5501c4e097aac61aaec79235a29cb04d9445f51b6e0e731218c3680a2e189cf`, 모델 `gpt-5.5`, 기존 ChatGPT 인증과 API 키 없음은 보존했다. 별도 앱 소스 변경·이미지 재빌드·종속성 다운로드는 없다. main infra 저장 커밋은 `6d15106`이다.
- 주인님이 허용한 1회 시험에서 실제 제품 함수 `support.views._generate_with_codex_cli`를 호출했다. 고객 정보 없이 전달한 연결 확인 요청에 **13.735초**, 정상 종료, “내부 AI 연결이 정상적으로 확인되었습니다.”라는 실제 응답을 받았다. 추가 생성 호출은 하지 않았다.
- 시험 중 새 Coconut의 외부 연결만 임시로 열었다가 원래 내부 준비망으로 복귀했다. 인증·데이터와 제품 실행 파일의 읽기 전용 연결, 원본 이미지, 다른 컨테이너의 시작 시각을 보존했다. 시험 후 14개 도메인의 새 비공개 TLS 응답 기준선이 모두 일치했고 실제 PG 대기본·MySQL 읽기 전용 상태와 운영 정본 표시 없음도 유지됐다. 결과는 `validation-coconut-ai-one-response.json`이다. 장기 인증 갱신이나 실제 고객 상담 전체 기능을 별도로 검증한 결과로 확대하지 않는다.

### 남은 실행 조건

- 남은 필수 작업은 infra 전체 리뷰·설명서, 모든 운영 writer 잠금·진행 작업 배수, 비공개 DB/공개 HTTPS/GBrain/자료/예약 작업/백업/인증서의 실제 책임 인계를 묶은 300초 리허설과 최종 일관 복구 묶음이다. 통과 뒤 한국 시각 22시 이후 기존 승인으로 실제 인계한다. 공개 DNS 변경은 여전히 마지막 별도 단계다.

## 14. 2026-09-17 전체 격리 리허설·복원·조정실 기억 정리

이 절은 13절 이후 직접 실행한 결과다. **실제 운영 정본과 공개 DNS는 아직 기존 서버에 있다.** 한국 시각 22시 이후 실제 인계는 승인됐으며, 운영 writer의 진행 상태와 실제 전달·잠금 명령을 마지막으로 대조한 뒤 실행한다. 공개 DNS 변경, 서버 삭제, vdb 포맷은 현재 범위 밖이다.

### 조정실 기억 정리의 승인된 대상

- 주인님 결정은 ‘조정실의 새 대화 기록만 매일 정리하고 옛 서버 기록은 보관’이다. 원본 기억 판단 모델·프롬프트·보고서/ledger 처리는 기존 `memory_distill.py`를 재사용한다.
- Windows용 `gbrain/bin/memory_distill_controlroom.py`는 현행 Codex JSONL의 `response_item/message/user/input_text`를 읽는다. 같은 파일의 event 복사본은 중복 입력으로 삼지 않으며 옛 server 기록을 가져오지 않는다. 현행·legacy·날짜·역할·중복 event 입력과 실제 현재 기록 38개를 확인했다.
- 생성 자격은 이미 새 서버에 있는 `provider.env`를 SSH로 프로세스 메모리에만 읽는다. 키는 Windows 파일·Git·로그에 저장하지 않는다. OpenRouter 키의 read-only 확인은 HTTP 200이며 내용 생성 호출은 0회다. 이것은 모델 생성·계정 잔액·향후 인증 갱신을 검증했다는 뜻이 아니다.
- native Windows task `GBrain-Controlroom-Memory-Distill`은 매일 03:30, **첫 시각 2026-09-18 03:30 KST**, pythonw·숨김·동시 실행 IgnoreNew·실행 제한 없음으로 준비했다. **현재 비활성·실행 안 됨**이다. 실제 인계 때 원본 03:30 user timer를 먼저 중지한 뒤 켠다. 별도 native task가 내부 확인 기록을 남기는 시험만 했고 기억 생성 작업을 시험 실행하지 않았다.

### 전체 격리 경로를 한 시계로 측정한 결과

기존 공개 운영을 바꾸지 않고 네 옛 서버에 별도 이름/label의 Source HTTPS 전달·private DB 전달·native cron 확인 작업을 만들었다. DB/파일은 FULL 복제본이며, main 13개 native scheduler 사본과 Windows memory task 사본은 고객/금융/유료 명령 대신 내부 확인 기록만 쓴다.

| 경우 | Source 중지부터 최종 Source 확인까지 | 실제 확인 |
|---|---:|---|
| cold 잠금 뒤 체크포인트 확인 거부·승격 전 취소 | 58.376초 | OLD DB/앱/Source 입구/old cron 복귀, NEW 복제와 읽기 전용 유지 |
| 최종 delta 수신 뒤 NEW 정본 선택 직후 의도적 중단 | 121.733초 | OLD는 잠금 유지, partial promotion을 NEW에서 재개, DB/파일 새 쓰기 보존, NEW 실행 책임 |
| NEW 추가 기록 뒤 DB/앱 재시작 | 59.852초 | 기존 세션·자료·추가 기록 보존, OLD reopen 없음 |
| GBrain CLI·자료 forward 확인까지 포함한 NEW 재시작 | 63.604초 | Source private PG/MySQL·GBrain HTTP/CLI·자료 forward health 포함 |
| NEW DB/앱이 실제 중지된 상태에서 복구 진입 | 79.216초 | 먼저 NEW native 시작·앱 재개 후 검증, OLD 데이터/실행 주체 유지 잠금 |

- 14개 HTTPS 이름의 CA·호스트명·응답과 3개 관리자 로그인 세션, 방문자 IP·query 보존, Source private PG/MySQL writable single source, GBrain HTTP 200과 forwarded CLI 공용 문서 동일, 자료 전달 health 및 공식 RNDLOG 업로드/다운로드·DB 정보/크기/SHA-256을 확인했다. ZiiN에는 원본 로그인 route가 없어 기존 홈/health와 DB 기록을 검증했다.
- OLD 시험 폴더는 self bind read-only로 잠가 **root 쓰기도 EROFS**였고, NEW 전환 뒤 old cron의 확인 기록은 증가하지 않았다. NEW marker 전에는 13개 native service가 모두 차단됐고 marker 후에는 모두 실행됐다. Windows 확인 task 역시 유료 호출 없이 실행됐다. 원래 업무 명령의 대외 효과 검증으로 확대 해석하지 않는다.
- Source original container 시작 시각과 untagged cron bytes를 보존했고, Source 외부 IP만 허용하는 trial ingress는 Windows PC에서 HTTP 403이었다. 실제 old Swarm published endpoints와 운영 writer 인계는 아직 별도 실행 대상이다.
- 발견한 복구 순서 오류는 core 공식 진입점에 통합했다. cold 잠금 뒤 중지된 MySQL에 STOP REPLICA를 재실행하지 않으며, NEW marker 뒤 application profile OLD와 NEW 엔진 중지 상태 모두 먼저 NEW를 준비한다. Source controller 예외 복구는 확인한 isolated authority만 사용한다. GNU timeout으로 checkpoint 하위 작업 그룹의 시간 제한을 적용한다.

### 별도 장애 영역의 cold base·delta와 실제 복원

- 큰 기준본은 중단 시간 밖에서 만들었다. Source 수신과 독립 SHA-256 확인까지 **4,332,741,604 bytes**, 155.827초였다. FULL clone의 준비 데이터이며 실제 최종 운영 정본 백업으로 부르지 않는다.
- 최종 cold WAL/binlog/자료 장벽 뒤 native rsync `--only-write-batch`로 원래 기준본을 바꾸지 않고 delta를 만들었다. **1,880,470 bytes**, 34.391초, 별도 Source가 크기/SHA-256을 확인한 뒤 NEW 선택을 진행했다.
- 별도 Source에 보관한 암호문을 다시 SHA-256 확인·GPG 복호화하여 새 복원 Root에 추출했다. 큰 기준본 스트림은 조정실에 내용 파일을 저장하지 않고 557.5초가 걸렸다. 이 복원 시간은 준비 RTO 관측이며 300초 전환 시간과 다르다.
- tar 제외 규칙이 데이터 cache까지 빼고 socket을 보관하지 않아 처음의 basis 대조는 실패했다. 누락 10개 이외에는 bytes/UID/GID/mode가 모두 동일했다. 기준본과 원래 receipt를 보존하고 누락 cache와 socket 메타정보만 **60,434-byte 암호화 supplement**로 별도 수신했다. 이후의 producer는 infra cache만 제외하고 socket 메타정보를 manifest에 담는다. Socket은 live 프로세스가 아니라 rsync 기준본에 있던 inert filesystem entry로 복원한다.
- base + basis supplement + delta를 native `--read-batch`로 적용한 뒤 **DB/자료 전체 10,136개 일반 파일 및 자료 2,320개**, 경로·bytes·symlink·UID/GID/mode 해시가 최종 cold snapshot과 일치했다. 전체 data SHA-256 `98af64d72ebe7f04a7ad144ab9ba7c102aba74ac42d3fc8362860e1a239e1a96`, 자료 SHA-256 `f6b21b8088ce92b43faf1d23bdf2a6f71d88c828e649531f2393bef1b5b14cd0`이다.
- 빈 별도 Docker/containerd에 offsite runtime 묶음을 복원했다. 첫 image archive만으로는 MySQL config blob이 빠져 native 실행이 실패했다. Source 실제 engine에서 동일 amd64 MySQL을 내보낸 companion을 함께 로드한 뒤 **11개 frozen image/RootFS 일치와 11개 native 시작**, PG16.14·MySQL8.4.8·Certbot5.8 실제 버전을 확인했다. 초기 archive 단독을 완전한 복구 묶음으로 쓰지 않는다. Digest alias가 로드되지 않는 경우 manifest의 frozen ID 대응을 쓴다.
- 복원한 독립 image와 물리 데이터로 PG/MySQL을 **network=none·공개 port 없음**으로 시작했다. 최종 WAL 이상, 4개 제품의 DB fixture, 실제 MySQL Root TCP 인증, **mysql/sys 포함 1,818개 table/view**를 확인했다. 업무 schema만 세면 1,679개이며 이전 1,818 검사의 범위와 구분한다. 기존 논리 복원에서 실행한 전체 CHECK TABLE 성공도 별도로 보존한다.
- 이 시험의 필요한 묶음은 Source offsite의 `checkpoint-base-20260917T073034Z-9d57214d.tar.gz.gpg`, `checkpoint-base-20260917T081601Z-458be6dc.tar.gz.gpg`(basis supplement), `checkpoint-delta-20260917T080010Z-d4a2e30c.tar.gz.gpg`, `runtime-images-20260917T063001Z.tar.gpg`, `runtime-mysql-amd64-20260917T072200Z.tar.gpg` 및 기존 private recovery keyring이다. Runtime archive의 옛 infra snapshot을 최신 운영 설정 대신 쓰지 않는다.

### 원래 준비 상태 복귀와 남은 실제 실행

- 시험용 Source service/cron·SSH process/key, main trial ingress·native units, Windows 확인 task를 범위별로 제거했다. 실제 기억 정리 task는 비활성으로 남겼다. 데이터·암호문·receipt·결과는 보관한다.
- FULL core `cleanup`으로 5개 앱을 normal 준비 프로필과 gateway `/srv/consolidation/data/rndlog-workspace`로 돌렸다. FULL/BASIC clone은 모두 중지했고 별도 cold Docker/containerd도 본인 PID/argv를 확인한 뒤 종료했다. main 실제 daemon을 정지하지 않았다.
- 실제 PG recovery=true, MySQL read_only/super_read_only=1/1, IO/SQL=Yes, lag=0/error 없음과 file-sync timer active, real `production-authority.json` 없음을 확인했다. vdb·DNS·원본 운영 서비스/cron은 바꾸지 않았다.
- old DB의 general Certbot timer는 통합 대상 외 `rn.studio`, `office.exdigm.com` 계보도 소유한다. 이 timer는 유지하고 ZiiN 전용 갱신만 인계한다. 다른 세 Source의 대상 계보/갱신 주체와 중앙 7개 계보는 원래 계획대로 책임을 하나로 옮긴다.
- infra 준비 변경 71개는 `9d665c2`, 제품 Codex 연결은 `6d15106`, 파일 입력을 읽는 GBrain 전달은 `11199d9`에 리뷰·저장됐다. FULL checkpoint/whole/restore 후속 변경 10개는 직접 리뷰와 실제 실행 검증 후 main infra `1366b9a`에 저장했다. Windows adapter와 조정실 문서는 controlroom에서 범위별로 저장한다.
- 남은 일은 실제 Source service endpoint/원본 파일 경로/모든 운영 writer의 진행·외부 효과 상태를 고정한 실행 절차, 최종 실제 WAL/binlog·파일 장벽과 복구 묶음, 한국 시각 22시 이후 실제 단일 정본·자료/CLI/HTTP/예약/백업/인증서 책임 인계다. 시험 scheduler의 내부 기록을 실제 고객 발송 성공으로 취급하지 않는다. DNS 최종 변경과 서버 삭제는 별도 지시가 있어야 한다.

## 15. 2026-09-17 실제 인계 준비 완료·22:14 같은 작업 재개

**현재 실제 운영 정본은 기존 서버입니다.** 이번 준비 실행과 전체 격리 리허설을 통과했고 실제 인계 코드는 main infra `9d20f9d`에 직접 리뷰·저장했습니다. 주인님이 승인하신 오늘 22시 이후 조건에 따라 **2026-09-17 22:14 KST**에 이 작업을 한 번 재개하도록 Codex heartbeat `22`를 등록했습니다. 재개 때 원본 배포와 진행 업무를 다시 확인한 뒤 실행하며, 예약 등록을 실제 정본 인계 완료로 보고하지 않습니다.

### 별도 RNDLOG 운영 배포 보존과 복구 묶음 갱신

- 준비 도중 RNDLOG 원본에 별도 `20260917174751`, Git `998d6e6` 배포가 관측됐습니다. 앱/NG 이미지와 stack label만 바뀐 것을 원본 baseline과 대조했고 마이그레이션/DB 모델 변경은 없습니다. 기존 배포 전 private 기준선도 보관했습니다. 새 main 저장소·앱에 같은 배포를 반영하고 새로운 두 frozen image를 사용합니다.
- 앱 이미지 `sha256:bc0509a18718a42ada71b51f950175b6a67e5db77142ab2b3a9cbe18eb279d3c`, NG 이미지 `sha256:b5f4b12d5ec4be363230ae354eacf026c568fd48c9224948b252e4683ea3e9d4`입니다. 원본에서 받은 native OCI stream **633,897,984 bytes**, SHA-256 `504a9d1a012eba38eb3428936d3530b33990e948e4fd27701da1674763f51218`를 확인했습니다.
- 추가 encrypted runtime 묶음 `checkpoint-base-20260917T090856Z-10b8dd09.tar.gz.gpg`를 별도 Source offsite에 독립 수신했습니다. **631,407,643 bytes**, SHA-256 `5b6c8b037b68b7054c991dbdf4364e144dde55fc299a55635d53ac164bdd64ce`입니다. offsite 원본의 크기/해시 검증 → private keyring 복호화 → OCI 스트림 → 별도 engine load에서 두 ID/RootFS와 native 시작을 확인했습니다. main original 컨테이너 시작 시각은 유지했습니다.
- FULL 격리 NEW에 같은 최신 RNDLOG를 반영해 기존 세 인증 세션·공식 자료 입구·DB/파일 추가 쓰기 보존 복구를 확인했습니다. 시험 후 normal main 앱·자료 경로로 되돌리고 FULL/BASIC와 별도 engine은 중지했습니다. 옛 RND 이미지와 기존 runtime/MySQL companion 및 기존 암호문은 보존합니다.

### 실제 원본 명령의 준비 검증

- 네 원본에서 소유 시험 폴더로 native self-bind RO/systemd mount를 확인했습니다. root 쓰기도 EROFS였고 잠금 전 열린 writable FD는 별도 fixture로 재현해 cold proof에서 거부했습니다. 시험 마운트와 단위는 해제·제거했습니다. 실제 운영 데이터는 이 준비 시험에서 잠그지 않았습니다.
- actual main의 `restore-passive`는 **2.225초**에 DB를 restart=no/RO의 영구 cold로 고정하고 native proof를 만들었습니다. `resume-passive-sync`는 **3.477초**에 원본 기반 복제·normal read-only 앱·파일 동기화를 재개했습니다. 원본 공개 서비스/SQL/cron을 정지하지 않았습니다.
- 원래 Source overlay/private SQL service 계약을 별도 시험 service에서 사용하여 PG/MySQL proxy update **9.574/11.406초**, native identity 조회와 원래 published mode를 확인했습니다. main readonly 세션의 `ALTER SYSTEM ...=off`도 별도 offline PG에서 native 성공하여 승격 전 OLD 설정 복원을 막는다는 가설을 기각했습니다.
- 원래 Kakao Persistent timer의 마지막 9월 14일 실행 stamp를 별도 시험 timer에 복사하여 즉시 중복 실행 없음·다음 9월 21일 실행을 확인했습니다. actual timer는 인계 후 이 stamp를 반영하여 활성화합니다.
- Source local의 14개 CA HTTPS 이름과 별도 전달, 실제 공개 14개 TLS/status/redirect 기준선을 확인했습니다. 현재 실제 기존 관리자 세션으로 RNDLOG/CEO Loan의 `/admin/` HTTPS **200**도 확인했습니다. Coconut에는 현재 재사용할 유효 staff session이 없으므로 실제 세션 보존 증거를 주장하지 않습니다. FULL의 세 로그인 증거와 허용된 Coconut AI 1회 응답은 별도로 유지합니다.
- Source 고포트의 조정실 외부 접속은 timeout으로 원인 미확인입니다. local 고포트 성공을 actual 표준 443 인계 성공으로 대신하지 않습니다. 실제 443은 밤 실행의 필수 검증입니다. Source endpoint/시험 private service와 main 임시 edge를 소유 label로 제거했고, RNDLOG 임시 UFW 한 규칙도 제거 후 원래 OpenSSH/80/443/v6 규칙을 확인했습니다.
- main PG recovery=true/streaming, MySQL RO/SRO=1/1·IO/SQL=Yes·lag=0/error 없음, 파일 동기화 활성·normal 다섯 runtime과 정본 표시 없음, 새 timer 13개 disabled를 확인했습니다. Windows 기억 task 역시 disabled·첫 9월 18일 03:30입니다. main 별도 containerd/dockerd의 기록된 PID는 모두 종료 상태입니다.

### 실제 인계의 공식 경로와 실패 복구

- 조정실 `work/live-handoff-controlroom.py` → 네 Source `live-handoff-source.py` → main `live-handoff-main.py`가 기존 SQL/Swarm/Compose/systemd/파일 reader/backup helper를 사용합니다. quiesce 직전 원본 기준선을 다시 검사하며 알려진 진행 업무·writable FD가 있으면 시작하지 않습니다.
- 한 시계로 모든 운영 writer/대상 예약 작업 중지 → 파일 영구 RO → SQL 배수·원본 clean shutdown·DB 영구 RO → 최종 replication/파일 hash → actual main cold → immutable basis의 최종 live batch 암호화·별도 수신 확인 → main 정본 표시 → native 승격/RW·runtime/공용 입구·Source 전달 → 실제 공개/private/CLI/자료/OLD 잠금 검증 → timer/Windows task 책임 재개 순서입니다.
- 모든 정본 선택 전 명령은 전체 중단 시작 후 **180초의 남은 예산**에 제한됩니다. 독립 백업 수신이 그 안에 완료되지 않으면 **OLD 복구 120초**를 남기며 새 정본 표시를 쓰지 않습니다. hot live timing preview에서 관측한 rsync rc24는 백업 성공으로 취급하지 않습니다. 실제 최종 cold는 native rc0/정확한 hash/receipt가 필수입니다.
- 정본 표시 전 실패는 main passive/cold 확인 → main cold 고정 → Source 원래 writer 재개 → main 복제/파일 동기화 재개입니다. 정본 표시 후 실패는 NEW만 복구하며 새 DB/파일 쓰기를 유지합니다. UNKNOWN이면 OLD reopen을 거부합니다. 에러·복구 성공·전체 소요 시간은 각각 보존합니다.
- 실제 공개 14개 응답/CA/redirect, 기존 유효 세션, Source native PG/MySQL RW와 chosen identity, GBrain 공용 문서 hash·HTTP·공식 자료 health, Source OLD writer와 예약 중지·RO/reboot mount, main runtime을 확인합니다. 마지막에 원래 Kakao stamp를 반영하고 정상 timer **13개**와 Windows task를 켭니다. 실제 고객/금융/유료 업무 명령의 시험 실행은 없습니다.
- Windows daily task는 새 조정실 대화만 기존 모델/프롬프트로 매일 정리하며 옛 서버 대화/ledger/결과는 보관합니다. provider 키는 기존 main private 파일에서 SSH로 프로세스 메모리에만 읽습니다. 통합 외 `rn.studio`/`office.exdigm.com`를 소유한 옛 DB general Certbot timer와 비관련 작업·개인 Hermes/Portainer 자료는 보존합니다.

### 저장과 남은 검증

- `code-review-loop`는 주 에이전트가 수행했고 최종 승인 finding과 열린 material contract question이 없습니다. 수정 범위는 main native controller/Source controller/Windows 보관본, 기존 checkpoint/restore helper의 Live 분기·공용 hash, RND 두 확인된 이미지와 설명서 **8파일**입니다. py_compile·Compose config·diff 검사는 통과했고 main infra **`9d20f9d`**에 저장했습니다. 다른 validation JSON은 stage하지 않고 보존했습니다.
- 실제 final offsite base+supplement+이번 Live delta의 물리 복원을 전용 `checkpoint-live-physical-restore-20260917/root`와 기존 독립 Docker에 수행합니다. `restore-handoff-checkpoint.py --scope live`는 actual marker/receipt/cold hash가 맞아야 하며 최종 tree/자료 hash와 count, native read-batch, PG clean checkpoint 이상·actual cold 인증 테이블 수·MySQL table/view 수·DB identities를 확인합니다. 실제 운영 DB/파일에는 쓰지 않습니다. 이전 FULL delta를 actual final delta 대신 사용하지 않습니다.
- 같은 작업의 자동 재개 `22`는 오늘 **22:14 KST**, 한 번 실행입니다. 실제 인계 또는 구체적인 차단을 보고한 뒤 paused로 두어 중복 전환을 막습니다. Codex 앱과 조정실이 그 시각에 실행 가능한 상태여야 합니다. 중단됐으면 같은 작업에서 공식 `preflight` → `cutover` 입구로 재개합니다.
- **미실행 필수 결과:** 오늘 밤 실제 정본·공개 443/private SQL·자료/GBrain·writer/예약/백업/인증서 책임 인계와 300초 실측, actual final backup의 별도 물리 복원. 이 결과까지 확인해야 승인된 통합 실행 완료입니다. 공개 DNS 변경·옛 서버 삭제·vdb 포맷은 별도 지시가 필요합니다.

구체적인 조정실 실행/복구 명령은 이 작업 `outputs/운영서버_통합_야간실행절차_20260917.md`, 서버 설명서는 main `/srv/consolidation/infra/README.md`의 ‘실제 운영 인계 실행과 복구’ 절입니다. 실제 진행 상태의 정본은 이 문서 최신 절이며, 실제 실행 결과에 따라 갱신합니다.

## 16. 2026-09-17 실제 정본 인계·최종 백업 독립 복원 완료

**현재 운영 정본은 새 main `49.247.192.127`입니다.** 실제 전환은 한국 시각 **22:30:17~22:33:10**, 오류 후 NEW 복구와 공개/비공개 입구·정상 예약 책임 재개까지 **172.469초**로 승인된 300초 이내였습니다. 실제 최종 운영 체크포인트도 별도 보관한 암호문에서 독립 물리 복원해 파일 일치와 데이터베이스 실행을 확인했습니다. 공개 DNS는 기존 IP를 유지하며 기존 입구가 새 main으로 전달합니다. 아래는 이전 준비 상태를 대체하는 현행 결과입니다.

### 현재 위치와 단일 쓰기 책임

| 항목 | 실제 운영 위치·역할 |
|---|---|
| main SSH / 설정 | `chaconne@49.247.192.127`, `/srv/consolidation/infra` |
| 제품 코드 | `/srv/consolidation/repos/{ceoloan,rndlog,fundkeeper,ziin}`; 각각 기존 `main/main/master/main` 브랜치와 Git 원격 보존 |
| PostgreSQL | `migration-replicas-postgres-1`, primary·기본/현재 transaction RO off, system ID `7652763638438633511` |
| MySQL | `migration-replicas-mysql-1`, read_only/super_read_only `0/0`, UUID `4e7e0be7-b1dc-11f1-9224-566ecede885a` |
| 제품 runtime | `production-{coconut,rndlog,ceoloan,ziin}-web-1`, `production-gbrain-http-1`; 원본 이미지/인증/역할 보존 |
| 공개 입구 | main `production-edge-edge-1`의 80/443 + 옛 네 HTTPS 입구의 main 고정 IP 전달 |
| 자료 | `/srv/consolidation/data/files-standby/{workspace,gbrain-state,ceoloan-registry,coconut-data,rndlog-media,ceoloan-media}` |
| 공식 RNDLOG 자료 경로 | main `/home/chaconne/projects/rndlog` → 선택한 `data/files-standby/workspace` |
| GBrain | main 본체; 기존 DB SSH CLI·3131·자료 forced command가 새 main으로 전달 |
| 옛 운영 데이터 | 네 Source의 원래 파일·DB persistent self-bind RO, 원래 앱/SQL writer·대상 cron/timer 중지; 원래 SQL service는 데이터 mount 없는 private proxy |

`standby`라는 디렉터리·DB 컨테이너 이름은 기존 연결 보존을 위한 이름이며 현재 쓰기 정본 역할은 실제 native 상태와 `data/production-authority.json`으로 판정합니다. marker SHA-256은 `3084e58c675afe1db2df7c7b22b3b77338335908e2d4a73ca8c520a2e5462302`입니다. 정본 선택 뒤에는 OLD snapshot의 쓰기나 옛 배포를 재개하지 않습니다.

### 별도 저녁 배포 보존과 처음 오류의 처리

- 22:14 fresh preflight에서 Source CEO Loan의 20시대 별도 배포가 발견돼 전환을 시작하지 않았습니다. 소스는 `efc8f2ddff789084543a6ea7d47f089de8b0ab1d`, 실제 app/nginx는 `a5ceae7`/`7d976f5`였으며 기존 3개 registry 환경값·readonly transport key mount 변화만 확인해 보존했습니다. RNDLOG `998d6e6` 배포 역시 유지했습니다.
- Source `/mnt/ceoloan/registry`의 1,697개 등기/구조 자료를 여섯 번째 파일 scope로 최종 sync·hash·RO fence·cold backup/restore에 연결했습니다. 원래 좁은 SSH download 계약과 키를 유지하고 Main 선택 뒤 공식 자료만 전달하도록 했습니다. 기존 paid IROS/LLM 작업을 새 시험으로 실행하지 않았습니다.
- 첫 actual `cutover-result.json`은 **success=false**를 그대로 보관했습니다. 실제 오류는 **`A main product runtime is not healthy`**였습니다. CEO Loan 원본 healthcheck는 30초 뒤 처음 실행하고 timeout 10초인데 controller는 20초만 기다려 첫 probe 전에 거부했습니다. 실제 첫 probe는 22:32:33.472에 시작하고 exit 0이었습니다.
- 그때 이미 독립 백업 수신 뒤 durable NEW marker가 존재했으므로 자동 복구는 **main_new**에서 진행했습니다. OLD를 다시 열지 않고 전체 재개를 172.469초에 마쳤습니다. 정상 전환 결과와 처음 호출 성공 여부를 구분합니다.
- 기존 `verify_new`의 healthy 기준을 보존하면서 대기만 40초로 맞췄습니다. network=none/no ports native startup 변형은 20초에 starting, 30.365초에 healthy였고 40초 전에 통과했습니다. 실제 main `verify`와 네 Source `verify-new`도 통과했습니다. 이미 정상인 실제 앱을 이 수정 때문에 다시 시작하지 않았습니다.

### 실제 공개/비공개 경로 확인

- 14개 HTTPS 이름을 옛 IP와 새 main IP에 각각 강제 지정한 **총 28개 실제 TLS 요청**에서 CA/호스트명·HTTP 상태·redirect 계약이 일치했습니다. DNS를 먼저 바꾸어 검증을 대신하지 않았습니다.
- 옛 RNDLOG 전달과 직접 main으로 온 요청은 조정실의 실제 외부 방문자 IP를 유지했습니다. 임의로 넣은 `X-Forwarded-For` 주소는 방문자 IP로 신뢰하지 않았으며 unique request와 두 edge 로그를 대조했습니다.
- 기존 유효 RNDLOG/CEO Loan staff session으로 `/admin/` HTTPS 200을 확인했습니다. Coconut에는 재사용할 실제 유효 staff session이 없어 실제 Coconut staff 로그인 보존 검증은 미확인입니다. FULL 격리의 세 로그인 증거·이전에 허용된 Coconut 내부 AI 1회 응답 성공은 별도 증거입니다. 추가 AI 생성 시험은 없습니다.
- Source의 원래 private PG/MySQL 접속은 위 chosen DB identity·쓰기 가능 상태로 이어집니다. GBrain HTTP 200, 공용 운영 프로토콜 hash `5aeebdd90863c5d9b89135b8ac12ad6af94fa8d0f4d215a64a45a7331a14d741` 보존, 공식 RNDLOG 자료 forward health를 확인했습니다.
- 최신 CEO Loan 앱의 공식 `registry.storage.verified_file`로 원래 등기 자료를 받아 크기/내용 해시를 확인했습니다. 기존 Source 주소를 사용하는 앱의 제한된 download identity도 새 정본으로 전달합니다. Source 원본 파일의 권한·다른 authorized_keys 줄과 개인/비관련 서비스는 보존합니다.

### 정상 예약·백업·기억 정리 책임

- main의 원래 제품 업무 11개 + 03:40 회사 DB 백업 + 중앙 인증서 갱신, **13개 native timer가 enabled/active**입니다. 옛 실행 주체의 대상 cron/timer는 비활성이고 반복 파일 sync와 옛 DB 복제 터널은 disabled입니다.
- Kakao Persistent timer의 원래 마지막 실행 stamp를 옮겨 즉시 중복 실행을 막았으며 다음 원래 일정은 9월 21일입니다. 원본에 없던 `update_gdrive.py`나 `.env` 업로드를 추가하지 않았습니다.
- Windows `GBrain-Controlroom-Memory-Distill`은 enabled/Ready, 첫 **2026-09-18 03:30 KST**입니다. 기존 모델/프롬프트/판단 파이프라인을 보존하고 **조정실의 새 대화 기록만** 매일 읽으며 옛 서버 대화·ledger·결과는 보관합니다. 이 예약을 내용 생성 시험으로 수동 실행하지 않았습니다. 비밀값은 기존 main private 파일에서 SSH로 프로세스 메모리에만 읽습니다.
- 통합 외 `rn.studio`, `office.exdigm.com` 계보를 소유한 옛 DB general Certbot timer와 개인 Hermes/Portainer 자료·비관련 host maintenance는 유지합니다. 고객 발송·금융 주문·유료 배치의 수동 시험은 없습니다. 정상 예약의 예정된 실행과 대외 효과를 시험 실행 성공으로 혼동하지 않습니다.
- 이 작업의 22시 자동 재개 **heartbeat 22는 PAUSED**로 바꿔 중복 전환을 막았습니다.

### 실제 최종 checkpoint와 독립 물리 복원

정본 선택 전 Source final clean PG LSN **`12/C95E7770`**, MySQL **`binlog.000115:32317893`**·Source UUID를 확인했습니다. final cold delta는 별도 옛 DB 디스크에 **427,308,218 bytes**로 독립 수신됐고 SHA-256은 **`3be398d63a0107bf3b2362f5d25747bc0b5e8e5f21ed1549c7d919a7a5646b94`**입니다. Source receipt 시각은 **2026-09-17 13:31:59.997314 UTC**이며 이를 확인한 뒤에만 main marker를 썼습니다.

- Source offsite 원본의 크기/해시 재검증 → 기존 private keyring 복호화 → 전용 offline Root에 base/supplement/actual live delta 추출 → native `--read-batch` → cold tree 대조 → 독립 이미지 PG/MySQL 시작을 수행했습니다. 조정실에 백업 내용·비밀값 파일을 만들지 않았습니다.
- 기본 스트림 **513.7초**, basis supplement 0.6초, actual delta 49.2초, native apply **43.955초**, DB boot **4.404초**였습니다. 중단 후 수행한 이 복구 시험 시간은 172.469초 운영 전환 시간과 다릅니다.
- **전체 data 일반 파일 14,503개**, cold tree SHA-256 `8e94789d3ccc8c842f5b7535d4ab04e42b42228f07e884238690b5408d2a99fd`; **자료 4,015개**, SHA-256 `543d6317d89d3942b41aa4a29186d55a373ce729bc2a748ef2707a15959c2abf`가 전환 당시 snapshot과 일치했습니다. 경로·내용·symlink·UID/GID/mode를 함께 검사했습니다.
- 별도 engine의 복원 image와 물리 DB로 **network=none/no public ports**에서 PG primary/최종 WAL 이상 **`12/C95E78C8`**, actual cold 네 auth table 수 **RNDLOG 3 / CEO Loan 20 / ZiiN 0 / FundKeeper 2**, native DB identities, MySQL 실제 Root TCP 인증과 **mysql/sys 포함 1,818개 table/view**를 확인했습니다. 실제 운영 파일/DB는 복원 대상으로 사용하지 않았습니다.
- 완료 후 두 cold 컨테이너와 exact PID/argv의 소유 containerd/dockerd만 종료했습니다. 실제 운영 앱/DB **7개 컨테이너의 시작 시각은 유지**했습니다. 독립 복원 자료·결과·암호문·receipt는 보관합니다.

| 실제 복구 묶음 | 역할 |
|---|---|
| `checkpoint-base-20260917T073034Z-9d57214d.tar.gz.gpg` | 검증된 immutable 물리 기준본 |
| `checkpoint-base-20260917T081601Z-458be6dc.tar.gz.gpg` | 60,434-byte basis supplement; 기존 기준본 원본 보존 |
| `checkpoint-delta-20260917T133104Z-5e12fac6.tar.gz.gpg` | 이번 실제 final cold 변경분; 이전 FULL delta로 대체하지 않음 |
| `runtime-images-20260917T063001Z.tar.gpg` + `runtime-mysql-amd64-20260917T072200Z.tar.gpg` | 기존 11 frozen runtime과 필요한 native MySQL config blob |
| `checkpoint-base-20260917T090856Z-10b8dd09.tar.gz.gpg` | 최신 RNDLOG 두 runtime companion, 독립 load/ID/RootFS/native 시작 통과 |
| `checkpoint-base-20260917T132559Z-208d6d89.tar.gz.gpg` | 최신 CEO Loan 두 runtime companion, 678,510,268 bytes, SHA `385ec74801481a367aeb211319497768b0e21df33e1639704620deb800f6903d`, 독립 load/ID/RootFS/native 시작 통과 |

보관 위치는 옛 DB `/mnt/consolidation-20260916/offsite`, 복구 keyring은 `/mnt/consolidation-20260916/recovery-keyring`입니다. GPG integrity와 SHA 확인이며 서명 백업이라고 표현하지 않습니다. archive 안의 과거 infra snapshot보다 최신 main infra Git과 보관된 Source private 기준선을 사용합니다. 마지막 startup 대기 수정은 checkpoint 생성 뒤이므로 최신 infra **`8d68cb2`**와 결과 설명 **`341999d`**를 함께 보존합니다. 비밀값을 Git/문서/GBrain/로그에 넣지 않습니다.


최신 infra Git `341999d`도 `checkpoint-base-20260917T135534Z-797d1dfd.tar.gz.gpg`로 독립 보관했습니다. 132,856 bytes, SHA-256 `0400d7b53e92398d89c2813d2aacf9a1bfceb3adf2bba75c410735aa7d719b01`이며 Source 원본의 크기/해시·GPG 복호화·Git bundle 검증/fetch/HEAD 일치로 40초 대기 수정과 실제 결과 README 복원을 확인했습니다. 데이터 checkpoint 이후 수정한 설정도 복구 묶음에 포함되며 원래 cold 데이터는 다시 복사하거나 잠그지 않았습니다.

22:55 원래 일정의 CEO Loan/RNDLOG 전달 작업은 새 main에서 각각 22:55:01~03에 실행돼 native Result=success/exit 0으로 끝났습니다. 수동 시험 실행은 없었고 실제 발송 대상 수·고객 수령까지 확인한 증거로 확대하지 않습니다.

### 운영 안내 반영과 남은 별도 작업

- 조정실 관리 원본 `gbrain-cards/windows-control.md`와 네 프로젝트 AGENTS.md의 실제 주소·코드·자료·DB/Compose 상태 확인 위치를 main으로 갱신했습니다. 제품 규칙·개발 에이전트의 조정실 경계와 Git 브랜치/원격은 유지했습니다. 각 설치된 AGENTS.md 및 전역 GBrain 카드는 관리 원본과 같은 파일·같은 내용임을 확인했습니다.
- CEO Loan/RNDLOG의 `CLAUDE.md` import, FundKeeper의 기존 same-file 연결 및 Git symlink mode, ZiiN의 별도 CLAUDE 파일 없음 상태를 보존했습니다. 처음 검증에서 모든 CLAUDE가 같은 import라고 가정한 assertion은 실제 설치 구조와 맞지 않아 기각하고 실제 각 구조와 같은 기준으로 확인했습니다. installer를 불필요하게 다시 실행하지 않았습니다.
- 키트의 기존 검사 `check-skill-deps.py`는 통과했습니다. FundKeeper/testbed 도메인 결합의 기존 warning은 제품 고유 구성이며 이번 주소 갱신과 관계없이 유지합니다. 다른 진행 중 조정실 작업의 커밋/스테이징은 함께 포함하지 않습니다.
- 옛 `.venv`·Swarm·전체 stack/prune 기반 deploy.sh를 새 main에서 그대로 실행하지 않습니다. 다음 개발은 새 저장소에서 SSH로 수행하고 명시적 배포 요청 시 해당 제품의 두 Compose 정의·frozen image·독립 검증/복구 범위를 대조합니다. 공통 스킬의 정책이나 다른 프로젝트 기능을 바꾸지 않습니다.
- 공용 GBrain의 이 계획과 `project/windows-control-tower-operating-context`는 기존 원문/제목/태그를 보존해 현행 인계 결과를 앞에 기록합니다. legacy reference type 프로젝트 페이지는 capture의 현행 base schema로 덮거나 임의 retype하지 않으며 새 현행 안내를 먼저 읽게 합니다. 이 작업은 갱신 카드·프로토콜·현행 기록을 읽었고, 다른 실행 중 세션의 열람 여부는 별도로 확인하지 않았습니다.
- **별도 승인 대기:** 공개 DNS 최종 연결, 옛 서버 해지/삭제, 미사용 vdb 포맷. 현재 서비스는 옛 공개 주소 전달에 의존하므로 서버를 먼저 삭제하면 안 됩니다. Exdigm 자체 앱/서버는 이전하지 않았습니다.
- **주기 관찰의 한계:** 내일 새벽 기억 정리/백업·인증서 갱신과 다음 정상 배치의 실제 대외 결과는 예정된 실행 시 별도로 확인해야 합니다. 준비와 책임 인계·독립 복원 증거를 그 미래 실행 결과로 대신하지 않습니다. 실제 Coconut staff session의 보존 검증도 미확인으로 남깁니다.

원래 첫 오류·NEW 복구·172.469초 기록은 조정실 `work/live-handoff-20260917/cutover-result.json`, native 최종 복원 proof는 main `work/checkpoint-live-physical-restore-20260917/result-*.json`에 있습니다. 사용자 결과는 이 작업 `outputs/운영서버_통합_실행결과_20260917.md`와 JSON, 현행 복구 설명은 갱신된 야간 절차와 main README입니다.
