# Hermes 기본 모델 3.8 Flash 갱신

## 목적과 승인 범위

- 주인님의 2026-09-15 요청: `3.8 플래시로 업데이트`.
- 직원 Hermes의 기본 모델을 `gemini-3.7-flash`에서 `gemini-3.8-flash`로 변경하고 공식 Hermes 배포로 운영에 반영한다.
- 변경 대상: 기본 설정 생성, Gemini 중계의 모델별 요청량 제한, 직접 검증, 운영 스킬과 GBrain 정본.
- 후보자 검색 등 다른 기능의 모델과 회사 데이터는 유지한다.
- 직원 기억, 작업 파일, 직원 생성 스킬, 연결 키와 과거 메시지를 보존한다.
- 공식 fleet 재생성은 에이전트 재시작과 활성 단기 세션 종료를 포함한다.

## 기준선과 최소 구현

- 서버: `chaconne@49.247.202.197`.
- 코드 수정: `/home/chaconne/exdigm-debug`, detached HEAD.
- 운영 코드: `/home/chaconne/exdigm`, clean main.
- 기준 커밋: `fc739a914ef61c79fb9d1c2d964cb001c559b35a`; debug, 운영, origin/main, 실제 GitHub main 일치.
- 직원 fleet 6개 모두 active/healthy. 직전 Hermes 배포는 `e25c6aff26e7030f2fe5279de34cbfc0dc62dcce`.
- 조정실의 기존 수정 `operational-error-alerts-20260914.md`는 이번 작업에서 수정·커밋하지 않는다.
- 최소 구현 게이트: 2단계에서 멈춤. 기존 기본 모델 상수, 설정 생성, 중계 예산과 공식 배포를 재사용한다. 새 제품 함수·서비스·의존성은 추가하지 않는다.
- 3.7 Flash도 기존 예산을 유지한다. 새 기본 모델에 기존 내부 예산 2,700,000토큰/60초를 연결한다. 이는 내부 제한이며 새 모델의 Google 계정별 실제 quota를 확인했다는 뜻은 아니다.

## 공식 경로와 검증

- 설정 생성 → 직원 프로비저닝 → 공식 Hermes의 Gemini 요청 → 공통 중계의 countTokens·예산 예약 → Google generateContent/streamGenerateContent.
- `HERMES_INTEGRATION_ENABLED=true scripts/debug_workspace.sh test`로 직접 영향을 받는 9개 검사 파일을 실행한다.
- 수정 전 127개 통과. 기능을 끈 개발 기본값에서는 연결 검사 27개가 실패했으며, 같은 공식 명령에 기능을 켜면 모두 통과했다. 검사와 기대값은 유지한다.
- Google 공식 모델 문서와 현재 운영 키의 모델 조회에서 `models/gemini-3.8-flash`, generateContent/countTokens 지원을 확인했다.
- 수정 후 동일 기준선과 새 모델의 유효 요청·과다 요청 거절·streaming/재시도 연결을 검증한다.
- `code-review-loop`, Django 검사, 코드 목차 갱신과 기존 고정 보호 검사를 수행한다.
- 검증된 커밋을 공식 prod 경로로 저장·반영하고 `scripts/deploy/deploy_hermes.sh prod <commit>`으로 같은 커밋의 Hermes를 반영한다.
- fleet 설정 6개, webhook health, 실제 Gemini 응답, 장기 파일과 과거 메시지 보존을 확인한다.

## 재개 정보

- 상태: 공식 운영·Hermes 배포와 실제 경로 검증 완료.
- 검증 커밋: `9d046ead42f20ac87a195171c7d6534cf91af5ea` (4개 파일).
- 동시 작업의 미완성 수정이 들어와 이 커밋의 임시 detached worktree `runtime/hermes-model-release-20260915`에서 같은 공식 검사를 실행했다. 기존 개발 폴더의 사용자 변경은 보존했다.
- 분리한 실제 커밋에서 관련 검사 131개와 고정 보호 검사 194개 통과, 보호 파일 18개 유지, Django 검사 통과.
- 코드 리뷰: 이 커밋의 4개 파일과 직접 소비자에서 승인된 finding 없음, 열린 계약 질문 없음.
- 스킬 검토: 새 기본 모델과 공식 검사 경로를 갱신했다. 폐기된 직원 브라우저 접근을 가리키던 메타데이터 문구도 현재 업무 API 접근으로 고쳤다. 구조 검증 통과.
- 보존 기준선: 직원 6개의 장기 파일 3,278개 SHA-256·권한과 환경값 fingerprint, 과거 메시지 수를 `.debug/hermes-model-20260915-baseline.json`에 기록했다. 비밀값 본문은 저장하지 않았다.
- 배포 전 운영 중계는 새 모델 시험 요청을 `gemini_model_not_managed`로 거절했다. 위 커밋의 새 모델 등록을 공식 배포한 뒤 같은 중계 경로에서 3.8 기본값과 실제 응답을 검증했다.
- 남은 작업: 이 요청 범위에서 없음. 조정실의 갱신 문서·스킬은 별도 커밋으로 저장한다.
- 실제 배포와 결과는 아래에 갱신한다.

## 운영 반영과 실제 경로 검증

- 공식 `scripts/deploy/deploy.sh prod`는 2026-09-15 01:34:03 KST에 `prod ok 9d046ead`, exit 0으로 완료됐다. 공식 `scripts/deploy/deploy_hermes.sh prod 9d046ead42f20ac87a195171c7d6534cf91af5ea`도 직원 6개 recreate, fleet healthy, telegram-manager ok와 exit 0으로 완료됐다.
- 실제 GitHub main, 운영 main, Hermes 배포 표식과 공통 MCP source commit이 모두 `9d046ead42f20ac87a195171c7d6534cf91af5ea`다.
- 현재 기본값은 직원 6개 모두 공급자 `gemini`, 모델 `gemini-3.8-flash`다. 각 profile의 webhook health가 `status=ok`, `platform=webhook`이고 모두 active다.
- 현재 중계는 3.7과 3.8 모두 내부 예산 2,700,000토큰/60초를 적용한다. 실제 3.8 요청의 예산 예약과 대기 0건을 확인했다.
- 모델을 명령으로 지정하지 않은 공식 Hermes CLI 세션 `20260914_163608_4c8811`에서 실제 사용 모델 `gemini-3.8-flash`, API 호출 3회, `skill_view`·`mcp__exdigm__code_query` 호출 2회, 실제 `state=found`, 최종 `MODEL_TOOL_OK` 응답을 확인했다. 업무 데이터 변경이나 직원에게 시험 메시지 발송은 실행하지 않았다.
- 직원 6개의 장기 파일 3,278개 SHA-256·권한, 과거 메시지 1,887개 fingerprint, 기존 환경값 fingerprint가 모두 동일하다. 100,000토큰 압축 상한과 매일 오전 4시 초기화도 유지했다.
- 운영 웹·DB·SSE·알림·Nginx 5개 서비스는 모두 1/1이다. 작업자·지원 프로세스 11개는 active, jobs 0, drain off다. 운영 HTTPS 200을 확인했다.
- GBrain `default:project/exdigm-hermes-agents`, `default:project/hermes/config`를 갱신하고 전체 Markdown 본문을 다시 읽어 저장본과 일치함을 확인했다. 이전 모델 갱신·배포 이력은 날짜가 있는 과거 기록으로 보존했다.
- 최종 스킬 검토에서 남은 문구·구조 문제 없이 `quick_validate.py`를 통과했다. 프로젝트의 설치된 skill junction이 이 controlroom 정본을 가리킨다.
- 임시 release worktree와 검사에 사용한 임시 연결을 제거했다. 공식 prod 로그는 `.debug/hermes-model-20260915-prod.log`, 보존 검증은 `.debug/hermes-model-20260915-verification.json`에 mode 0600으로 남겼다.
- 동시에 진행한 다른 작업의 개발 커밋 `8c2ea773`은 원래 debug worktree에 보존했다. 그 커밋은 이번 모델 배포에 포함하지 않았으며 운영에는 위 검증 커밋만 반영했다.
- Google 3.8의 정확한 계정별 quota는 미확인이다. 이번 변경은 기존 내부 제한을 유지하며 새 모델을 연결했고, 모델 조회와 실제 도구 대화의 성공 범위까지 확인했다.
