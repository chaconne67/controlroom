---
name: fundkeeper-deploy
description: Use when deploying FundKeeper/Coconut or checking its Docker Swarm deployment, production health, logs, or recovery state.
---

# FundKeeper 배포

배포는 코드·정적 파일·이미지·GitHub·전체 Docker Swarm에 외부 효과를 만든다. 주인님이 현재 변경의 배포를 명시적으로 요청한 경우에만 실행한다.

## 정본

| 항목 | 값 |
|---|---|
| SSH | `chaconne@49.247.38.186` |
| 저장소 | `/home/chaconne/fundkeeper` |
| 기준 브랜치 | `master` |
| 배포 진입점 | `sudo /home/docker/deploy.sh` |
| 스택 파일 | `/home/docker/docker-stack.yml` |
| 스택 이름 | `Coconut` |
| 서비스 | `Coconut_coconut`, `Coconut_nginx` |
| 헬스체크 | `https://coconut.ai.kr/health/` → `ok` |
| 로그 | `/var/log/docker_deploy.log` |

## 배포 전 하드 게이트

1. `git status --short --branch`로 브랜치와 모든 추적·미추적 파일을 확인한다.
2. `master`가 아니면 중단한다.
3. 요청과 무관한 변경이나 미추적 파일이 하나라도 있으면 중단한다.
4. 배포할 커밋과 `origin/master`의 관계를 확인한다.
5. Django 검사와 변경별 검증이 통과했는지 확인한다.
6. `sudo -n true`로 비대화형 sudo 사용 가능 여부만 확인한다. 이 단계에서 배포 스크립트를 실행하지 않는다.

이 게이트가 필요한 이유는 배포 스크립트가 `git add --all`로 미추적 파일까지 자동 커밋·push하기 때문이다. 파일을 임의로 삭제하거나 숨겨서 게이트를 통과시키지 않는다.

## 실제 배포 경로

`sudo /home/docker/deploy.sh`는 다음 단일 경로를 실행한다.

1. 현재 저장소 전체를 자동 stage·commit·push한다. Git 명령이 실패해도 스크립트는 배포를 계속할 수 있다.
2. Tailwind CSS와 Django 정적 파일을 생성한다.
3. 저장소를 `/home/docker/fundkeeper/fundkeeper`로 복사한다.
4. Nginx와 Coconut 이미지를 새 태그로 빌드한다.
5. 현재 Docker Swarm의 모든 스택을 제거한다.
6. 15초 대기 후 `Coconut` 스택을 배포한다.

스크립트는 Coconut만 선택 삭제하지 않는다. 다른 스택이 있으면 함께 제거되므로 배포 전에 `docker stack ls` 결과를 확인하고, 다른 스택이 있으면 중단해 주인님께 영향 범위를 알린다.

`.env`는 Docker 빌드 컨텍스트의 `.dockerignore`에서 제외되고, 실행 시 호스트 파일이 볼륨으로 마운트된다. 비밀값을 출력하거나 Git에 추가하지 않는다.

## 배포 후 검증

1. `docker stack services Coconut`에서 두 서비스가 모두 `1/1`인지 확인한다.
2. `curl -fsS https://coconut.ai.kr/health/`의 본문이 `ok`인지 확인한다.
3. 변경된 실제 운영 화면이나 기능을 확인한다.
4. `git status --short --branch`와 GitHub의 `origin/master` 반영을 확인한다.
5. 실패하면 `/var/log/docker_deploy.log`와 서비스 상태를 보존해 보고한다.

자동 롤백 경로는 없다. 실패 원인을 확인하지 않고 배포 명령을 반복하거나 별도 우회 스택을 만들지 않는다.
