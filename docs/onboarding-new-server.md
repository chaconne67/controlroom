# Controlroom 장비 준비

Windows Git Bash·macOS Terminal·Linux Bash에서 Git을 준비하고 저장소 읽기 권한과 필요한 서버 SSH 접근을 확인합니다.

```bash
git clone https://github.com/chaconne67/controlroom.git ~/controlroom
bash ~/controlroom/install.sh windows-control
```

설치 후 터미널을 새로 엽니다. Windows는 Git for Windows와 PowerShell을 사용합니다. 비공개 설정이면 인증된 Git clone을 사용하며, 인증 없는 raw 다운로드를 최초 진입점으로 사용하지 않습니다.

```bash
controlroom pull
controlroom push "변경 설명"
```

이미 설치한 장비에서는 같은 설치기를 다시 실행해 지침·스킬·프로젝트 문서를 재연결합니다. 이전 `kitpull`·`kitpush`는 호환 명령입니다. 기존 프로젝트 경로 등록을 우선하며 사용자 문서 폴더를 자동으로 덮어쓰지 않습니다.

지침·도구·기획 원본은 controlroom 한 저장소에서 관리합니다. 프로젝트 폴더의 docs는 저장소의 projects/<프로젝트>/docs에 연결합니다. 원격 제품 코드의 커밋·배포는 해당 프로젝트에서 수행합니다. 새 기기의 앱 로그인과 OS 전용 기능은 해당 장비에서 준비합니다.

기기를 옮길 때 현재 작업 계획의 재개 정보를 갱신하고 검토한 변경을 push합니다. 다음 장비에서는 pull 후 그 계획과 실제 코드 저장소 상태를 대조합니다.
