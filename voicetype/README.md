# VoiceType

CapsLock으로 어느 입력창에서나 한국어를 받아 적는 Windows 프로그램입니다.

## 쓰는 법

- **누르고 말하기**: CapsLock을 누른 채 말하고 떼면, 교정된 글이 커서 위치에 들어갑니다.
- **켜 두고 말하기**: CapsLock을 짧게 한 번 누르면 녹음이 켜집니다. 다 말한 뒤 한 번 더 누르면 끝납니다.
- **대문자 고정**: Shift+CapsLock
- 화면 아래 가운데에 상태가 잠깐 뜹니다.
  - 주황 "듣는 중": 녹음하고 있음
  - 남색 "정리 중": 글로 바꾸고 다듬는 중
  - 빨강 "오류": 실패함. 받아 적은 글이 있으면 기록 파일에 남아 있음
- 관리자 권한으로 실행한 창에서는 동작하지 않습니다(Windows 보안 규칙).

## 동작 순서

CapsLock → 마이크 → Soniox 실시간 인식(`stt-rt-v5`) → Gemini 교정(`gemini-3.1-flash-lite`) → 클립보드로 붙여넣기 → 원래 클립보드 복구

## 설정 파일 (`~/.voicetype/`, Git에 넣지 않음)

| 파일 | 내용 |
|---|---|
| `secrets.toml` | `soniox_api_key`, `gemini_api_key` (필수) |
| `config.toml` | 선택. `hotkey = "capslock"` 또는 `"scrolllock"`, `polish = false`(교정 끄기), `terms = ["추가 용어"]` |
| `history.jsonl` | 받아 적은 글, 교정된 글, 걸린 시간. 음성은 저장하지 않음 |
| `voicetype.log` | 오류 기록 |

설정을 바꾼 뒤에는 다시 시작해야 적용됩니다.

## 설치·시작·중지

```powershell
cd ~/controlroom/voicetype; uv sync
```

- 로그인 시 자동 시작: 시작프로그램 폴더의 `VoiceType.lnk`
  - 대상: `.venv\Scripts\pythonw.exe voicetype.py`
- 지금 시작: 위 바로가기를 실행합니다. Claude 데스크톱 셸에서 띄우면 격리 환경에서 실행되므로, 바로가기나 탐색기로 실행합니다.
- 중지:

```powershell
Get-CimInstance Win32_Process -Filter "Name='pythonw.exe'" | Where-Object CommandLine -match 'voicetype\.py' | ForEach-Object { Stop-Process -Id $_.ProcessId }
```

## 점검

```powershell
uv run python tests/check_pipeline.py 시험.wav
```

- 16 kHz·모노·16비트 WAV를 실제 말하는 속도로 인식·교정 함수에 넣습니다.
- 키를 뗀 순간부터 결과가 나오기까지 걸린 시간을 출력합니다.

## WhisperTyping으로 되돌리기

1. VoiceType을 중지하고 시작프로그램의 `VoiceType.lnk`를 지웁니다.
2. WhisperTyping을 실행한 뒤 앱 설정에서 자동 시작을 다시 켭니다(설정 파일의 `RunOnStartup`).
3. 전환 전 설정 백업: `~/backups/whispertyping/settings.before-voicetype-20260926.json`
