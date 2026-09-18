---
name: exdigm-deploy
description: Use when the user asks to deploy Exdigm to production or change its production DB infrastructure or Hermes fleet.
---

# Exdigm Deploy

## Core Rule

배포 정본은 GBrain `project/exdigm-deploy-workflow`다. 현재 코드·서버와 다르면 코드와 서버를 확인한 뒤 GBrain을 갱신한다.

배포는 검증된 Git 커밋 하나를 `origin/main`, 운영 체크아웃, 앱·작업자에 차례로 반영하는 단일 경로다. 파일 복사, 운영 폴더 직접 수정, 강제 push, 수동 Docker 보정으로 우회하지 않는다.

## Runtime Layout

| 역할 | 위치 |
|---|---|
| 중앙 조정실 | `/home/chaconne/projects/exdigm` |
| SSH | `chaconne@49.247.202.197` |
| 디버깅 worktree | `/home/chaconne/exdigm-debug` |
| 운영 체크아웃 | `/home/chaconne/exdigm` |
| 배포 브랜치 | `main` |

디버깅 worktree는 detached HEAD를 유지한다. 운영 체크아웃은 clean `main`을 유지하며 운영 작업자가 이 경로의 스크립트를 직접 실행한다.

## Commands

일반 운영 배포:

```bash
ssh chaconne@49.247.202.197 \
  'cd /home/chaconne/exdigm-debug && scripts/deploy/deploy.sh prod'
```

운영 DB 인프라를 명시적으로 변경할 때만:

```bash
ssh chaconne@49.247.202.197 \
  'cd /home/chaconne/exdigm-debug && scripts/deploy/deploy.sh db-prod'
```

Hermes 제품 런타임을 명시적으로 변경할 때만:

```bash
ssh chaconne@49.247.202.197 \
  'cd /home/chaconne/exdigm-debug && scripts/deploy/deploy_hermes.sh prod "$(git rev-parse HEAD)"'
```

일반 배포는 Hermes와 DB 인프라를 변경하지 않는다.

## Preflight

1. 중앙 GBrain의 `project/exdigm-operating-context`와 `project/exdigm-deploy-workflow`를 읽는다.
2. 디버깅 worktree가 detached HEAD이고 clean인지 확인한다.
3. 배포할 변경이 모두 커밋됐는지 확인한다.
4. 운영 체크아웃이 `main`이고 clean인지 확인한다.
5. 코드·테스트·화면 검증이 완료됐는지 확인한다.

배포 스크립트는 디버깅 HEAD를 `origin/main`에 fast-forward push하고, 운영 체크아웃을 정확히 그 커밋까지 fast-forward한 뒤 기존 `current` 적용 경로를 실행한다. 같은 운영 호스트에서 실행될 때는 외부 SSH로 자기 자신에게 재접속하지 않는다.

## Verification

```bash
ssh chaconne@49.247.202.197 \
  'cd /home/chaconne/exdigm && git status --short --branch && docker service ls --filter name=Exdigm && scripts/deploy/deploy_workers.sh status'

curl -fsSI --max-time 10 https://office.exdigm.com/
```

- 운영 체크아웃 HEAD, `origin/main`, 배포 대상 커밋이 같아야 한다.
- 앱·nginx·SSE·notification dispatcher가 각 `1/1`이어야 한다.
- 운영 작업자는 read-write 모드여야 한다.
- UI 변경은 운영 화면을 직접 확인한다.

## Stop Conditions

- 디버깅 worktree 또는 운영 체크아웃이 dirty다.
- `origin/main` push가 fast-forward로 거절된다.
- 운영 체크아웃의 `git pull --ff-only`가 실패한다.
- root 소유 production inventory와 현재 호스트가 일치하지 않는다.
- 배포 스크립트의 이미지 빌드·Swarm 반영·작업자 적용이 실패한다.

실패하면 같은 스크립트의 결함을 고쳐 다시 실행한다. 운영 폴더 수동 수정이나 별도 배포 경로를 만들지 않는다.
