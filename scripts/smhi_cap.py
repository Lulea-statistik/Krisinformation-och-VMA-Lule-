#!/usr/bin/env python3
"""Fetch current SMHI impact-based warnings with geometry from the official JSON API.

CAP remains an alternative format, but the CAP RSS feed is too large for efficient
half-hourly collection. The JSON warning endpoint is explicitly documented by SMHI
for the current warnings and includes EPSG:4326 GeoJSON polygons.
A failed download/parse never replaces the previous public snapshot.
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

SOURCE = "https://opendata-download-warnings.smhi.se/ibww/api/version/1/warning.json"
OFFICIAL = "https://www.smhi.se/vader/varningar-och-meddelanden"
OUTPUT = Path("data/smhi_cap_warnings.json")
MAX_BYTES = 24 * 1024 * 1024


def fetch_warnings():
    request = Request(SOURCE, headers={
        "User-Agent": "Lulea-statistik-SMHI-warnings/2.0 (public-information-project)",
        "Accept": "application/json"
    })
    with urlopen(request, timeout=40) as response:
        declared = response.headers.get("Content-Length")
        if declared and int(declared) > MAX_BYTES:
            raise ValueError("SMHI warning JSON exceeds safety size limit")
        payload = response.read(MAX_BYTES + 1)
    if len(payload) > MAX_BYTES:
        raise ValueError("SMHI warning JSON exceeds safety size limit")
    print(f"Fetched SMHI warning JSON: {len(payload)} bytes", flush=True)
    return json.loads(payload)


def parse_time(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)
    except (TypeError, ValueError):
        raise ValueError(f"Unexpected SMHI warning timestamp: {s!r}")


def localized(value):
    if isinstance(value, dict):
        return str(value.get("sv") or value.get("en") or "")
    return str(value or "")


def verified_geometry(feature):
    if not isinstance(feature, dict):
        return None
    geometry = feature.get("geometry")
    if not isinstance(geometry, dict) or geometry.get("type") not in ("Polygon", "MultiPolygon"):
        return None
    crs = ((feature.get("crs") or {}).get("properties") or {}).get("name")
    if crs is not None and crs.upper() not in ("EPSG:4326", "URN:OGC:DEF:CRS:OGC:1.3:CRS84"):
        raise ValueError(f"Unsupported source CRS: {crs!r}")
    # The SMHI JSON API represents these areas in WGS84 GeoJSON lon/lat order.
    # Reject clearly invalid coordinates rather than reprojecting based on guessed CRS.
    def verify(coords, depth=0):
        if depth > 10:
            raise ValueError("Unexpected nested geometry")
        if isinstance(coords, list) and len(coords) >= 2 and all(
            isinstance(x, (int, float)) and not isinstance(x, bool) for x in coords[:2]
        ):
            lon, lat = coords[:2]
            if not (-180 <= lon <= 180 and -90 <= lat <= 90):
                raise ValueError("Invalid longitude/latitude in SMHI polygon")
            return 1
        if not isinstance(coords, list):
            raise ValueError("Invalid SMHI polygon coordinates")
        return sum(verify(child, depth + 1) for child in coords)
    n = verify(geometry.get("coordinates"))
    if n < 4:
        raise ValueError("SMHI polygon contains too few positions")
    return geometry


def descriptions(fields, code):
    return "\n\n".join(
        localized(d.get("text")) for d in fields
        if isinstance(d, dict) and (d.get("title") or {}).get("code") == code
        and localized(d.get("text"))
    )


def normalize(payload, now=None):
    if not isinstance(payload, list):
        raise ValueError("SMHI warning.json must be a JSON array")
    now = now or datetime.now(timezone.utc)
    entries = []
    for warning in payload:
        if not isinstance(warning, dict) or "id" not in warning:
            raise ValueError("Invalid SMHI warning record")
        event = localized(warning.get("event"))
        areas = warning.get("warningAreas")
        if not isinstance(areas, list):
            raise ValueError("Missing warningAreas in SMHI response")
        for area in areas:
            if not isinstance(area, dict) or "id" not in area:
                raise ValueError("Invalid SMHI warning area")
            expiry = parse_time(area.get("approximateEnd"))
            if expiry is not None and expiry <= now:
                continue
            info = area.get("descriptions") or []
            if not isinstance(info, list):
                raise ValueError("Unexpected SMHI description data")
            level = area.get("warningLevel") or {}
            name = localized(area.get("areaName"))
            feature = area.get("area")
            entry = {
                "id": str(warning["id"]) + ":" + str(area["id"]),
                "identifier": str(warning["id"]),
                "cap_url": OFFICIAL,
                "sent": area.get("published") or "",
                "event": event,
                "headline": localized(area.get("eventDescription")) or event,
                "description": descriptions(info, "INCIDENT") or "\n\n".join(
                    localized(d.get("text")) for d in info
                    if isinstance(d, dict) and localized(d.get("text"))
                ),
                "instruction": descriptions(info, "AFFECT"),
                "severity": (level.get("code") or "").upper(),
                "severity_label": localized(level),
                "urgency": "",
                "certainty": "",
                "effective": area.get("approximateStart") or "",
                "onset": area.get("approximateStart") or "",
                "expires": area.get("approximateEnd") or "",
                "area_name": name,
                "geometry": verified_geometry(feature),
                "crs": "EPSG:4326",
                "source_crs_declared": bool(isinstance(feature, dict) and feature.get("crs")),
            }
            entries.append(entry)
    entries.sort(key=lambda e: (e["onset"], e["id"]))
    return {
        "status": "ok",
        "checked_at_utc": now.isoformat().replace("+00:00", "Z"),
        "source": SOURCE,
        "method": "SMHI current warnings JSON (not CAP RSS)",
        "crs": "EPSG:4326",
        "area_count": len(entries),
        "warnings": entries
    }


def main():
    result = normalize(fetch_warnings())
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUTPUT.with_suffix(".tmp")
    tmp.write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    os.replace(tmp, OUTPUT)
    print(f"SMHI current warnings: {len(result['warnings'])} areas at {result['checked_at_utc']}", flush=True)


if __name__ == "__main__":
    main()
