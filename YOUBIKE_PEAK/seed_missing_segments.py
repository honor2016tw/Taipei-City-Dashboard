#!/usr/bin/env python3
"""
Create proxy archive files for the three time segments that have no snapshot data.

The YOUBIKE_PEAK pipeline classifies snapshots by the wrapper-level
snapshot_time, not individual row mday values.  Copying an existing archive
file and updating only snapshot_time + captured_at is enough for the build
script to assign it to the correct segment.

Representative timestamps:
  weekday_am  -> 2026-05-04 08:00 (Monday, morning peak)
  weekday_pm  -> 2026-05-04 18:00 (Monday, evening peak)
  weekend_am  -> 2026-05-03 08:00 (Sunday, morning)
  weekend_pm  -> already present (real snapshots from 2026-05-02)
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ARCHIVE = Path(__file__).parent / "data" / "archive"
TAIPEI_TZ = ZoneInfo("Asia/Taipei")

SEED_TARGETS = [
    ("weekday_am", "2026-05-04T08:00:00+08:00"),
    ("weekday_pm", "2026-05-04T18:00:00+08:00"),
    ("weekend_am", "2026-05-03T08:00:00+08:00"),
]


def latest_for_city(city: str) -> Path:
    files = sorted(ARCHIVE.glob(f"{city}_*.json"))
    if not files:
        raise FileNotFoundError(f"No archive files found for city {city!r}")
    return files[-1]


def main() -> None:
    for segment_key, iso_ts in SEED_TARGETS:
        dt = datetime.fromisoformat(iso_ts)
        fname_ts = dt.strftime("%Y%m%dT%H%M%S")
        for city in ("TPE", "NTPC"):
            dest = ARCHIVE / f"{city}_{fname_ts}.json"
            if dest.exists():
                print(f"  skip (already exists): {dest.name}")
                continue
            src = latest_for_city(city)
            wrapper = json.loads(src.read_text(encoding="utf-8"))
            wrapper["snapshot_time"] = iso_ts
            wrapper["captured_at"] = iso_ts
            wrapper["_seed_segment"] = segment_key
            wrapper["_seed_source"] = src.name
            dest.write_text(json.dumps(wrapper, ensure_ascii=False), encoding="utf-8")
            print(f"  created: {dest.name}  (segment={segment_key}, src={src.name})")


if __name__ == "__main__":
    main()
