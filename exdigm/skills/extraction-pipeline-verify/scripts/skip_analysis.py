"""SKIP 38건의 실제 원인 분류."""
import os

import django
from datetime import datetime
from collections import Counter

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "main.settings")
django.setup()

from django.utils import timezone
from data_extraction.models import ResumeExtractionState

# 리얼타임 시작 시점
since_dt = timezone.make_aware(datetime.fromisoformat("2026-04-25T15:45:36"))
# 배치 시작 직전까지
until_dt = timezone.make_aware(datetime.fromisoformat("2026-04-25T17:46:11"))

states = list(
    ResumeExtractionState.objects.filter(
        updated_at__gte=since_dt,
        updated_at__lt=until_dt,
    )
    .select_related("resume__candidate")
    .order_by("updated_at")
)

print(f"=== Realtime 처리 ResumeExtractionState: {len(states)}건 ===\n")

# Status 분류
status_counts = Counter(s.status for s in states)
print("Status 분포:")
for status, count in sorted(status_counts.items(), key=lambda x: -x[1]):
    print(f"  {status:20} {count:>4}")

print()

# SKIP 추정: status가 STRUCTURED 가 아닌 모든 케이스
non_structured = [s for s in states if s.status != "structured"]
print(f"=== Non-STRUCTURED ({len(non_structured)}건) 상세 ===\n")

# last_error 패턴
error_patterns = Counter()
for s in non_structured:
    err = (s.last_error or "")[:120]
    error_patterns[err] += 1

print("last_error 패턴 (상위 15):")
for err, count in error_patterns.most_common(15):
    print(f"  [{count:>3}] {err!r}")

print()

# quality_routing 분포
routing_counts = Counter()
for s in non_structured:
    md = s.metadata or {}
    qr = md.get("quality_routing", {})
    next_action = qr.get("next_action", "<none>")
    reason_class = qr.get("reason_class", "<none>")
    routing_counts[(reason_class, next_action)] += 1

print("Non-STRUCTURED quality_routing 분포:")
for (rc, na), count in sorted(routing_counts.items(), key=lambda x: -x[1]):
    print(f"  [{count:>3}] reason_class={rc}, next_action={na}")

print()

# attempt_count 분포 (시도 횟수)
attempt_dist = Counter(s.attempt_count for s in states)
print("attempt_count 분포 (전체):")
for attempts, count in sorted(attempt_dist.items()):
    print(f"  attempts={attempts}: {count}")
