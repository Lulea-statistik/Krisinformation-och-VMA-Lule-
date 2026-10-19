#!/usr/bin/env python3
"""Inspect Sveriges Radio VMA v3 API availability and response structure.

Only schema/aggregate diagnostics are saved. Alert content, IDs and locations
are NOT written to disk; archival reuse terms require separate verification.
"""
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ENDPOINTS = {
    "active_alerts": "https://vmaapi.sr.se/api/v3/alerts",
    "swagger": "https://vmaapi.sr.se/swagger/v3.0/swagger.json"
}
OUTPUT = Path("data/sr_vma_diagnostics.json")

def read_json(url):
    req = Request(url, headers={"Accept": "application/json", "User-Agent": "Lulea-VMA-method-audit/1.0"})
    with urlopen(req, timeout=30) as response:
        return json.load(response)

def main():
    data = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "Connectivity and schema checks only, not historical VMA extraction",
        "retains_alert_content": False,
        "alerts": {},
        "openapi": {}
    }
    try:
        payload = read_json(ENDPOINTS["active_alerts"])
        alerts = payload if isinstance(payload, list) else payload.get("alerts", []) if isinstance(payload, dict) else []
        data["alerts"] = {
            "ok": True,
            "response_type": type(payload).__name__,
            "top_level_keys": sorted(payload.keys()) if isinstance(payload, dict) else [],
            "alerts_field_type": type(alerts).__name__,
            "record_count_at_check": len(alerts) if isinstance(alerts, list) else None,
            "record_field_names": sorted(alerts[0].keys()) if isinstance(alerts, list) and alerts and isinstance(alerts[0], dict) else []
        }
    except Exception as exc:
        data["alerts"] = {"ok": False, "error_type": type(exc).__name__, "error": str(exc)[:160]}
    try:
        spec = read_json(ENDPOINTS["swagger"])
        data["openapi"] = {
            "ok": True,
            "version": spec.get("openapi"),
            "paths": sorted(spec.get("paths", {}).keys()),
            "schemas": sorted(spec.get("components", {}).get("schemas", {}).keys()),
            "schema_fields": {name: sorted((spec.get("components", {}).get("schemas", {}).get(name) or {}).get("properties", {}).keys()) for name in ("Alert", "Info", "Area", "MsgType", "Status")},
            "response_shapes": {path: sorted(list(operations.keys())) for path, operations in spec.get("paths", {}).items() if isinstance(operations, dict)}
        }
    except Exception as exc:
        data["openapi"] = {"ok": False, "error_type": type(exc).__name__, "error": str(exc)[:160]}
    try:
        test = read_json("https://vmaapi.sr.se/testapi/v3/examples/data")
        # Record structure only. Test messages must never enter the public alerts feed.
        examples = test.get("alerts", []) if isinstance(test, dict) else test if isinstance(test, list) else []
        info_objects = [info for alert in examples if isinstance(alert, dict) for info in alert.get("info", []) if isinstance(info, dict)]
        areas = [area for info in info_objects for area in info.get("area", []) if isinstance(area, dict)]
        geocodes = [geo for area in areas for geo in area.get("geocode", []) if isinstance(geo, dict)]
        data["test_examples"] = {
            "ok": True,
            "response_type": type(test).__name__,
            "top_level_keys": sorted(test.keys()) if isinstance(test, dict) else [],
            "example_count": len(examples),
            "alert_field_names": sorted(set(k for alert in examples if isinstance(alert, dict) for k in alert.keys())),
            "info_field_names": sorted(set(k for info in info_objects for k in info.keys())),
            "area_field_names": sorted(set(k for area in areas for k in area.keys())),
            "geocode_field_names": sorted(set(k for geo in geocodes for k in geo.keys())),
            "message_types": sorted(set(str(a.get("msgType")) for a in examples if isinstance(a, dict) and a.get("msgType"))),
            "statuses": sorted(set(str(a.get("status")) for a in examples if isinstance(a, dict) and a.get("status"))),
            "geocode_name_keys": sorted(set(str(g.get("valueName")) for g in geocodes if g.get("valueName"))),
            "stored_content": False
        }
    except Exception as exc:
        data["test_examples"] = {"ok": False, "error_type": type(exc).__name__, "error": str(exc)[:160]}
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("SR VMA connectivity:", data["alerts"].get("ok"), "OpenAPI:", data["openapi"].get("ok"))
    if not (data["alerts"].get("ok") and data["openapi"].get("ok")):
        raise SystemExit("SR VMA diagnostics incomplete; inspect saved diagnostic JSON")

if __name__ == "__main__":
    main()
