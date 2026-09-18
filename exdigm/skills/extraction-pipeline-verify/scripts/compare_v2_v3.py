"""전처리 v2 (field code만) → v3 (적극 압축) 효과 비교."""
import json
from pathlib import Path

ROOT = Path("/home/chaconne/exdigm-debug")
v2 = json.loads((ROOT / "snapshots/step_b2_text_v2.json").read_text())
v3 = json.loads((ROOT / "snapshots/step_b2_text_v3.json").read_text())
v3_by_id = {r["file_id"]: r for r in v3["results"]}

print(f"{'category':<13} {'file':<35} {'v2_len':>7} {'v3_len':>7} {'delta':>8} {'pct':>6}")
print("-" * 100)

total_v2 = 0
total_v3 = 0

# 가장 큰 절감 순으로 정렬
rows = []
for r2 in v2["results"]:
    r3 = v3_by_id.get(r2["file_id"])
    if not r2["ok"] or not r3 or not r3["ok"]:
        continue
    delta = r3["preprocessed_length"] - r2["preprocessed_length"]
    total_v2 += r2["preprocessed_length"]
    total_v3 += r3["preprocessed_length"]
    pct = (delta / r2["preprocessed_length"] * 100) if r2["preprocessed_length"] else 0
    rows.append((delta, r2, r3, pct))

# delta 작은 순 (= 큰 음수 = 큰 절감 먼저)
rows.sort(key=lambda x: x[0])

for delta, r2, r3, pct in rows:
    marker = ""
    if delta < -1000:
        marker = " ⭐ 큰 절감"
    elif delta == 0:
        marker = " (변화 없음)"
    elif delta > 0:
        marker = " ⚠ 증가 (왜?)"
    print(f"{r2['category']:<13} {r2['file_name'][:33]:<35} "
          f"{r2['preprocessed_length']:>7} {r3['preprocessed_length']:>7} "
          f"{delta:>+8d} {pct:>+5.1f}%{marker}")

print()
print("=== 총계 ===")
print(f"  v2 총 길이: {total_v2:,}자")
print(f"  v3 총 길이: {total_v3:,}자")
print(f"  절감: {total_v2 - total_v3:,}자 ({(total_v2-total_v3)/total_v2*100:.1f}%)")
