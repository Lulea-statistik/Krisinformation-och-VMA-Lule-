#!/usr/bin/env python3
"""Read-only SR VMA production pilot. Stores aggregate diagnostics only.

No message text, identifiers, instructions, or geographical code values are persisted.
This does not establish eligibility to republish or archive CAP alerts.
"""
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

SOURCE = "https://vmaapi.sr.se/api/v3/alerts"
OUTPUT = Path("data/sr_vma_pilot.json")

def main():
    now = datetime.now(timezone.utc)
    with urlopen(Request(SOURCE, headers={"Accept": "application/json",
                 "User-Agent": "Lulea-VMA-pilot/1.0"}), timeout=35) as response:
        data = json.load(response)
    if not isinstance(data, dict) or not isinstance(data.get("alerts"), list):
        raise ValueError("Unexpected production payload (required: alerts array)")
    records = data["alerts"]
    diagnostics = Counter()
    municipality_matches = 0
    needs_review = 0
    for alert in records:
        if not isinstance(alert, dict):
            needs_review += 1
            continue
        status = str(alert.get("status") or "")
        msg_type = str(alert.get("msgType") or "")
        diagnostics["status_" + (status if status in ("Actual", "Test", "Exercise", "System", "Draft") else "unknown")] += 1
        diagnostics["type_" + (msg_type if msg_type in ("Alert", "Update", "Cancel", "Ack", "Error") else "unknown")] += 1
        if status != "Actual":
            continue
        found_local = False
        for info in alert.get("info") or []:
            if not isinstance(info, dict):
                continue
            for area in info.get("area") or []:
                if not isinstance(area, dict):
                    continue
                for geo in area.get("geocode") or []:
                    if not isinstance(geo, dict):
                        continue
                    if str(geo.get("valueName") or "").strip().casefold() == "kommun":
                        if str(geo.get("value") or "").strip() == "2580":
                            found_local = True
        if found_local:
            municipality_matches += 1
        else:
            needs_review += 1
    result = {
      "checked_at_utc": now.isoformat(),
      "source": SOURCE,
      "mode": "read_only_aggregate_pilot",
      "public_alert_feed_enabled": False,
      "retains_alert_content": False,
      "retains_alert_identifiers": False,
      "retains_location_codes": False,
      "coverage_note": "Current production snapshot only, not historical completeness.",
      "municipality_code_assumption": "Kommun value 2580 is assumed to mean Lulea; code-system definition still requires confirmation.",
      "production_count": len(records),
      "actual_records_with_kommun_2580": municipality_matches,
      "other_actual_records_needing_geographic_review": needs_review,
      "status_and_type_counts": dict(sorted(diagnostics.items()))
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
