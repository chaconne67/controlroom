"""전처리 v1 vs v2 차이 (field code 정규식 효과 측정)."""
import json
import re
from pathlib import Path

ROOT = Path("/home/chaconne/exdigm-debug")
v1 = json.loads((ROOT / "snapshots/step_b2_text.json").read_text())
v2 = json.loads((ROOT / "snapshots/step_b2_text_v2.json").read_text())

FIELD_CODES = re.compile(
    r"INCLUDEPICTURE|MERGEFIELD|HYPERLINK|FORMTEXT|FORMCHECKBOX|"
    r"PAGEREF|FILENAME|MERGEFORMAT|HTMLCONTROL|EMBED|SECTIONPAGES",
    re.IGNORECASE,
)

v2_by_id = {r["file_id"]: r for r in v2["results"]}

print(f"{'category':<14} {'file':<35} {'v1_len':>7} {'v2_len':>7} {'delta':>7} {'note'}")
print("-" * 100)

total_delta = 0
field_was = 0
field_now = 0

for r1 in v1["results"]:
    r2 = v2_by_id.get(r1["file_id"])
    if not r2 or not r1["ok"] or not r2["ok"]:
        continue
    v1_len = r1["preprocessed_length"]
    v2_len = r2["preprocessed_length"]
    delta = v2_len - v1_len
    total_delta += delta

    # field code presence (need to read text)
    text_path = r2.get("text_path")
    field_after = 0
    if text_path and Path(text_path).exists():
        text = Path(text_path).read_text(encoding="utf-8")
        field_after = len(FIELD_CODES.findall(text))

    note = ""
    if delta != 0:
        note = f"{'+' if delta > 0 else ''}{delta}자"
    if field_after:
        note += f"  ⚠ field 잔존 {field_after}건"
        field_now += 1

    if delta != 0 or field_after:
        print(f"{r1['category']:<14} {r1['file_name'][:33]:<35} "
              f"{v1_len:>7} {v2_len:>7} {delta:>+7d}  {note}")

# field code originally present
v1_audit = json.loads((ROOT / "snapshots/step_b2_text.json").read_text())
for r in v1_audit["results"]:
    text_path = r.get("text_path")
    if not text_path or not Path(text_path).exists():
        continue

print()
print("=== Summary ===")
print(f"  총 길이 변화 (v2 - v1): {total_delta:+d}자")
print(f"  field code 잔존 파일: {field_now} / 40")
print("  (이전 audit에서 field code 노출 파일은 3건이었음)")
