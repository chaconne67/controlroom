# Controlroom 장비 준비

조정실의 실제 루트를 `~/projects`로 통일합니다. 프로젝트 문서·지침·스킬을 직접 보관하고 공통 설치 도구는 `~/projects/.controlroom`에 둡니다. Windows의 `~`는 USERPROFILE, macOS·Linux는 HOME입니다.

Git과 Python 3.12 이상, 비공개 Controlroom/Venture GitHub 저장소의 Git 인증을 준비합니다. 새 기기의 앱 로그인·SSH 키·프로젝트 서버 접근은 해당 장비에서 준비합니다. 개발 에이전트는 조정실에서 실행하며 서버의 실제 제품 코드·데이터·배포 경로를 설치기로 옮기지 않습니다.

## Windows PowerShell

인증된 GitHub에서 `.controlroom/install.ps1`을 다운로드한 폴더에서:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 -Agent windows-control
```

## macOS·Linux Bash

`.controlroom/install.sh`을 다운로드한 폴더에서:

```bash
bash ./install.sh windows-control
```

설치 후 새 터미널에서 `controlroom verify`를 실행합니다. Windows는 Git for Windows와 PowerShell을 사용합니다. 인증 없는 raw 다운로드를 비공개 저장소의 최초 다운로드 방법으로 사용하지 않습니다.

```bash
controlroom pull
controlroom push "변경 설명"
```

기존 파일이 있어도 설치기는 최신본을 먼저 확보한 뒤 `~/backups/controlroom`에 압축 백업하고 새 내용을 적용합니다. 같은 이름의 파일도 갱신하며 관리 폴더에서 옛 파일만 남겨 두지 않습니다. 적용 실패 시 자동 복구합니다. 인증·환경·외부 고객 자료는 각 장비의 것으로 유지합니다. 옛 루트는 성공한 전환에서 정리하고 링크로 남기지 않습니다.

이미 설치한 장비에서는 `~/projects/.controlroom/install.ps1` 또는 `install.sh`을 다시 실행하거나 `controlroom pull`을 사용합니다. 별도 프로젝트 경로 등록은 사용하지 않습니다. 프로젝트는 `~/projects/<프로젝트>`이며 GitHub에도 같은 상대 구조로 저장합니다. 기기를 옮기기 전 계획의 재개 정보를 갱신하고 검토한 변경을 push합니다.
