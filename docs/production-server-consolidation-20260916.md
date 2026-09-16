# 운영서버 통합 계획 v2 — 새 호스트 준비, DNS는 마지막

작성일: 2026-09-16 (Asia/Seoul)
계획 정본: controlroom/docs/production-server-consolidation-20260916.md
목표 호스트: chaconne@49.247.192.127, hostname main
상태: 신규 서버 준비·검증 승인 · 공개 DNS 미변경 · 운영 데이터 정본과 쓰기 책임 미인계
대상: 기존 DB, Coconut/FundKeeper, RNDLOG, ZiiN, CEO Loan, GBrain 런타임·자료 게이트웨이·필요한 제품 런타임
제외: Exdigm 앱·운영서버·도메인 이전. 공용 DB를 쓰는 Exdigm 소비자의 기존 접속·업무 계약도 보호한다.

## 1. 사용자 결정과 완료 의미

- 기존 DB 호스트는 증설할 수 없으므로 새 호스트 49.247.192.127로 통합한다.
- 기존 서비스와 사용자 작업을 보존하면서 새 서버의 설치·복사·복원·시험·전환 준비를 실행하도록 승인받았다. 같은 준비 승인을 다시 요청하지 않는다.
- 지금 공개 DNS를 바꾸지 않는다. 옛 서버 해지·데이터 삭제·실제 고객 문자/메일·금융 주문·유료 작업도 실행하지 않는다.
- 마지막 단계에는 도메인의 DNS 연결만 바꾸는 것이 목표다. 그 전에 DB/파일이 최신 새 정본이 되고, 모든 쓰기·예약 작업의 책임 인계와 옛 IP의 전달 경로가 실제로 검증되어야 한다.
- 복사본으로 화면이 열리는 상태는 준비 완료가 아니다. DB/파일 최신성·단일 정본·배치·인증·갱신·복구가 확인되지 않으면 “DNS만 남음”이라고 보고하지 않는다.
- 주인님은 최종 인계를 위한 **야간 전체 접속 중단을 최대 5분**까지 허용했다. 준비 중 서비스는 계속 유지한다. 중단 시작부터 전체 서비스 재개까지 300초 안에 끝나는 전환·중단·복귀 절차를 리허설한 뒤 실제 인계에 진입한다. 이 승인은 DNS 변경이나 옛 서버 삭제 승인이 아니다.
- 개발 에이전트·지침·계획·판단은 controlroom에 둔다. 확인된 제품 AI 런타임만 운영 호스트로 옮기며 비밀값은 서버 간 보안 전송으로만 다룬다.
- 2026-09-17 추가 결정: Coconut 02:10 작업은 정상 캐시 생성만 이전한다. 기존 서버에도 없는 `update_gdrive.py` 단계는 별도 과제로 남긴다. `.env`를 Drive에 복사하는 `upload_to_gdrive.py`로 자동 대체하지 않는다.

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
| 구 rndnote 49.247.46.171 | SSH 시간 초과 | 잔여 서비스·데이터·계약 상태. 퇴역을 추정하지 않음 |

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
