# Certbot 도메인 정리와 스택 복구 계획

## 목표

- Certbot 관리 대상을 현재 도메인 `coconut.ai.kr`, `www.coconut.ai.kr`로 한정한다.
- 인증서 갱신 결과와 무관하게 `Coconut` 스택을 다시 배포한다.
- 월간 예약 작업과 같은 실행 경로로 서비스 가동과 HTTPS 건강 상태를 확인한다.

## 승인 범위

- `/home/work/fundkeeper/xmodules/sh/renew_certbot.sh`
- 폐기된 Certbot 인증서 계보 `coconut.im`
- 이번 변경의 검증·리뷰·장애 기록·커밋

## 비범위

- `coconut.ai.kr` 인증서와 개인키
- Docker 스택 정의, 애플리케이션 기능, 데이터베이스
- 월간 예약 시각과 다른 운영 작업

## 현재 최종 경로

1. root crontab이 매월 1일 02시에 `renew_certbot.sh`를 실행한다.
2. 스크립트가 기존 스택을 제거하고 80번 포트를 확보한다.
3. Certbot이 관리 중인 인증서 계보를 갱신한다.
4. 갱신이 성공한 경우에만 `/home/docker/deploy.sh`를 실행한다.
5. 배포 스크립트가 이미지를 빌드하고 `Coconut` 스택을 생성한다.

## 변경

1. `coconut.im` Certbot 인증서 계보를 공식 삭제 명령으로 제거한다.
2. 갱신 성공과 실패는 각각 기록하되 두 경우 모두 기존 배포 단계로 합류시킨다.
3. 별도 복구 스크립트나 우회 경로는 추가하지 않는다.

## 검증

1. `bash -n xmodules/sh/renew_certbot.sh`
2. `certbot certificates`에서 `coconut.ai.kr` 계보만 남았는지 확인
3. `sudo -n /bin/bash /home/work/fundkeeper/xmodules/sh/renew_certbot.sh`로 root 예약 경로 직접 실행
4. `Coconut_coconut`과 `Coconut_nginx`가 각각 1/1인지 확인
5. 앱 컨테이너가 `healthy`이고 재시작이 없는지 확인
6. `https://coconut.ai.kr/health/`가 반복해서 HTTP 200인지 확인
7. 로컬 diff를 `code-review-loop`로 검토하고 승인 finding이 없을 때 종료

## 복구

- 코드 문제가 확인되면 이번 스크립트 변경만 되돌린다.
- 폐기된 `coconut.im` 계보는 로컬에서 삭제되며, 다시 필요해지면 해당 도메인의 DNS 통제권을 확보한 뒤 새 인증서로 재발급해야 한다.
