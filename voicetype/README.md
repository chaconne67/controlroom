# Thock Voice Typing

CapsLock으로 어느 입력창에서나 말을 받아 적는 Windows 프로그램입니다. (폴더·파일 이름은 이전 이름 `voicetype`을 유지합니다.)

## 쓰는 법

- **누르고 말하기**: CapsLock을 누른 채 말하고 떼면, 교정된 글이 커서 위치에 들어갑니다.
- **켜 두고 말하기**: CapsLock을 짧게 한 번 누르면 녹음이 켜집니다. 다 말한 뒤 한 번 더 누르면 끝납니다.
- **대문자 고정**: Shift+CapsLock
- 작업 표시줄 바로 위 가운데에 작은 막대가 늘 떠 있습니다.
  - 마우스를 올리면 알약으로 커지고, 위에 톱니바퀴가 뜹니다. 톱니바퀴를 누르면 설정 창이 열립니다.
  - 오른쪽 클릭: 설정 / 위치 초기화 / Thock 종료
  - 끌어서 옮길 수 있고, 옮긴 위치를 기억합니다.
  - 눌러도 쓰던 입력창의 초점을 빼앗지 않습니다.
- 받아쓰는 동안 알약 모양이 바뀝니다.
  - 흰 막대 파형이 흐름: 듣는 중. 목소리 크기를 따라 움직입니다.
  - 왼쪽에 빨간 점: 켜 두고 말하기 방식이라 다시 누를 때까지 계속 듣습니다.
  - 흐린 막대가 물결침: 글로 바꾸고 다듬는 중
  - 빨간 알약: 실패함. 받아 적은 글이 있으면 기록 파일에 남아 있습니다.
- **오타 노트**: 붙여 넣은 글에서 틀린 단어를 직접 고치면 기억합니다.
  - 같은 고침이 두 번 나오면 다음 받아쓰기부터 인식·교정에 반영합니다.
  - 세 번이면(두 글자 이상 단어) 붙여 넣기 전에 자동으로 바꿉니다.
  - 설정 창의 "오타 노트"에서 보고 지우거나 직접 추가합니다. 직접 추가한 것은 바로 자동 교체됩니다.
  - 붙여 넣은 입력칸만, 다음 받아쓰기를 시작하거나 글을 보내거나 90초가 지날 때까지 읽습니다. 저장하는 것은 "틀린 표기 → 바른 표기" 쌍뿐입니다.
  - 입력칸 글을 읽을 수 없는 앱(원격 데스크톱 등)에서는 자동으로 기억하지 못하니 직접 추가합니다.
- 관리자 권한으로 실행한 창에서는 동작하지 않습니다(Windows 보안 규칙).

## 동작 순서

CapsLock → 마이크 → Soniox 실시간 인식(`stt-rt-v5`) → Gemini 교정(`gemini-3.1-flash-lite`) → 클립보드로 붙여넣기 → 원래 클립보드 복구

## 설정 파일 (`~/.voicetype/`, Git에 넣지 않음)

| 파일 | 내용 |
|---|---|
| `secrets.toml` | `soniox_api_key`, `gemini_api_key`. 설정 창에서 붙여 넣으면 저장됨 |
| `settings.json` | 단축키, 교정 켜기/끄기, 용어 사전, 표시 위치, 오타 기억 켜기/끄기. 설정 창에서 바꿈 |
| `typo_notes.json` | 오타 노트: 틀린 표기 → 바른 표기, 고친 횟수 |
| `history.jsonl` | 받아 적은 글, 교정된 글, 걸린 시간. 음성은 저장하지 않음 |
| `voicetype.log` | 오류 기록 |

설정 창에서 저장하면 다시 시작하지 않아도 바로 적용됩니다. 키가 없으면 켤 때 설정 창이 자동으로 열립니다.

## 설치·시작·중지

```powershell
cd ~/controlroom/voicetype; uv sync
```

- 로그인 시 자동 시작: 시작프로그램 폴더의 `VoiceType.lnk`
  - 대상: `.venv\Scripts\pythonw.exe voicetype.py`
- 지금 시작: 위 바로가기를 실행합니다. Claude 데스크톱 셸에서 띄우면 격리 환경에서 실행되므로, 바로가기나 탐색기로 실행합니다.
- 중지: 작은 막대 오른쪽 클릭 → "Thock 종료", 또는

```powershell
Get-CimInstance Win32_Process -Filter "Name='pythonw.exe'" | Where-Object CommandLine -match 'voicetype\.py' | ForEach-Object { Stop-Process -Id $_.ProcessId }
```

## 점검

```powershell
uv run python tests/check_pipeline.py 시험.wav
```

- 16 kHz·모노·16비트 WAV를 실제 말하는 속도로 인식·교정 함수에 넣습니다.
- 키를 뗀 순간부터 결과가 나오기까지 걸린 시간을 출력합니다.

```powershell
uv run python -m unittest tests.test_fixes
```

- 붙여 넣은 뒤 어떤 수정을 "단어 고침"으로 볼지 시험합니다.

## WhisperTyping으로 되돌리기

1. VoiceType을 중지하고 시작프로그램의 `VoiceType.lnk`를 지웁니다.
2. WhisperTyping을 실행한 뒤 앱 설정에서 자동 시작을 다시 켭니다(설정 파일의 `RunOnStartup`).
3. 전환 전 설정 백업: `~/backups/whispertyping/settings.before-voicetype-20260926.json`
