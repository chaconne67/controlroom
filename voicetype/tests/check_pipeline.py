"""Feed WAV files (16 kHz mono 16-bit) through the real transcribe() and Polisher at real-time pace.

Usage: uv run python tests/check_pipeline.py file1.wav [file2.wav ...]
Prints recognized text, corrected text, and seconds from "key release" (end of audio) to each result.
"""

import asyncio
import sys
import time
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import voicetype  # noqa: E402


async def realtime_chunks(path, marks):
    with wave.open(str(path)) as w:
        assert (w.getframerate(), w.getnchannels(), w.getsampwidth()) == (voicetype.SAMPLE_RATE, 1, 2), path
        step = voicetype.SAMPLE_RATE // 10
        while frames := w.readframes(step):
            yield frames
            await asyncio.sleep(0.1)
    marks["released"] = time.perf_counter()


async def main(paths):
    s = voicetype.load_settings()
    polisher = voicetype.Polisher(s)
    for path in paths:
        marks = {}
        raw = await voicetype.transcribe(realtime_chunks(path, marks), s["soniox_api_key"], s["terms"])
        stt = time.perf_counter() - marks["released"]
        text = await asyncio.to_thread(polisher.polish, raw, "WindowsTerminal.exe") if raw else raw
        total = time.perf_counter() - marks["released"]
        print(f"{Path(path).name}: stt {stt:.2f}s, total {total:.2f}s\n  raw : {raw}\n  text: {text}")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:]))
