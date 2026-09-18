"""40건 텍스트의 영문/국문 분포 + field code 노이즈 검출."""
import json
import re
from pathlib import Path

ROOT = Path("/home/chaconne/exdigm-debug")
spec = json.loads((ROOT / "snapshots/step_b2_text.json").read_text(encoding="utf-8"))

KOREAN = re.compile(r"[가-힣]")
LATIN = re.compile(r"[A-Za-z]")
FIELD_CODES = re.compile(
    r"INCLUDEPICTURE|MERGEFIELD|HYPERLINK|FORMTEXT|FORMCHECKBOX|"
    r"PAGEREF|TOC \\|FILENAME|MERGEFORMAT|HTMLCONTROL|EMBED",
    re.IGNORECASE,
)
HEX_BLOB = re.compile(r"\b[0-9A-Fa-f]{20,}\b")


def lang_ratio(text: str) -> tuple[float, float]:
    if not text:
        return 0.0, 0.0
    total = len(text)
    ko = len(KOREAN.findall(text))
    en = len(LATIN.findall(text))
    return ko / total, en / total


def detect_lang_blocks(text: str) -> dict:
    """Roughly split text into Korean-dominant vs Latin-dominant blocks.

    A block is a contiguous run of lines where the dominant script is the same.
    Returns counts and approximate sizes per language.
    """
    lines = [ln for ln in text.split("\n") if ln.strip()]
    blocks = []
    current_lang = None
    current_lines = []
    for ln in lines:
        ko = len(KOREAN.findall(ln))
        en = len(LATIN.findall(ln))
        if ko + en == 0:
            lang = "other"
        else:
            lang = "ko" if ko >= en else "en"
        if lang != current_lang and current_lines:
            blocks.append((current_lang, current_lines))
            current_lines = []
        current_lang = lang
        current_lines.append(ln)
    if current_lines:
        blocks.append((current_lang, current_lines))
    return {
        "block_count": len(blocks),
        "ko_blocks": sum(1 for b, _ in blocks if b == "ko"),
        "en_blocks": sum(1 for b, _ in blocks if b == "en"),
        "ko_chars": sum(len("\n".join(ls)) for b, ls in blocks if b == "ko"),
        "en_chars": sum(len("\n".join(ls)) for b, ls in blocks if b == "en"),
    }


print(f"{'category':<14} {'file':<35} {'len':>6} {'ko%':>5} {'en%':>5} "
      f"{'KOblk':>5} {'ENblk':>5} {'field':>5} {'hex':>4}")
print("-" * 110)

bilingual_count = 0
field_count = 0
hex_count = 0

for r in spec["results"]:
    if not r["ok"] or not r["text_path"]:
        continue
    text = Path(r["text_path"]).read_text(encoding="utf-8")
    pre_len = r["preprocessed_length"]
    ko_pct, en_pct = lang_ratio(text)
    blocks = detect_lang_blocks(text)
    field_hits = len(FIELD_CODES.findall(text))
    hex_hits = len(HEX_BLOB.findall(text))

    is_bilingual = blocks["ko_blocks"] >= 2 and blocks["en_blocks"] >= 2 \
                   and blocks["ko_chars"] >= 200 and blocks["en_chars"] >= 200
    if is_bilingual:
        bilingual_count += 1
    if field_hits:
        field_count += 1
    if hex_hits:
        hex_count += 1

    flag = ""
    if is_bilingual:
        flag += "⚠BILING "
    if field_hits:
        flag += "⚠FIELD "
    if hex_hits:
        flag += "⚠HEX "

    print(f"{r['category']:<14} {r['file_name'][:33]:<35} {pre_len:>6d} "
          f"{ko_pct*100:>4.0f}% {en_pct*100:>4.0f}% "
          f"{blocks['ko_blocks']:>5d} {blocks['en_blocks']:>5d} "
          f"{field_hits:>5d} {hex_hits:>4d}  {flag}")

print()
print("=== Summary (40건 중) ===")
print(f"  영문/국문 둘 다 200자+ 블록 보유 (잠재 중복 후보): {bilingual_count}")
print(f"  docx field code 노출: {field_count}")
print(f"  긴 hex blob 노출: {hex_count}")
