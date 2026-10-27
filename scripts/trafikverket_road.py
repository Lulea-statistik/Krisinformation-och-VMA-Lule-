#!/usr/bin/env python3
"""Trafikverket Situation 1.5: active Norrbotten road incidents for GitHub Pages.

Trafikverket's open API requires authentication. Configure GitHub Actions secret
TRAFIKVERKET_API_KEY; never expose the key to client JavaScript or committed files.
Only explicitly WGS84 geometries (EPSG:4326) are rendered as GeoJSON.
"""
import json
import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

API = "https://api.trafikinfo.trafikverket.se/v2/data.json"
PUBLIC = "https://www.trafikverket.se/trafikinformation/vag/"
OUTPUT = Path("data/trafikverket_road.json")
MAX_BYTES = 15 * 1024 * 1024
LIMIT = 2500


def now_utc():
    return datetime.now(timezone.utc)


def timestamp(value):
    if not value or not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def build_query(key):
    # Build XML with standard library, escaping authenticationkey safely.
    root = ET.Element("REQUEST")
    ET.SubElement(root, "LOGIN", authenticationkey=key)
    query = ET.SubElement(root, "QUERY", objecttype="Situation", schemaversion="1.5",
                          limit=str(LIMIT))
    filt = ET.SubElement(query, "FILTER")
    match = ET.SubElement(filt, "ELEMENTMATCH")
    ET.SubElement(match, "EQ", name="Deviation.CountyNo", value="25")
    for field in ("Id", "ModifiedTime", "PublicationTime", "Deviation"):
        ET.SubElement(query, "INCLUDE").text = field
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def fetch(key):
    request = Request(API, data=build_query(key), method="POST", headers={
        "Content-Type": "text/xml; charset=utf-8",
        "Accept": "application/json",
        "User-Agent": "Lulea-statistik-road-info/1.0"
    })
    with urlopen(request, timeout=45) as res:
        declared = res.headers.get("Content-Length")
        if declared and int(declared) > MAX_BYTES:
            raise ValueError("Trafikverket response too large")
        payload = res.read(MAX_BYTES + 1)
    if len(payload) > MAX_BYTES:
        raise ValueError("Trafikverket response too large")
    return json.loads(payload)


def read_situations(payload):
    response = payload.get("RESPONSE") if isinstance(payload, dict) else None
    results = response.get("RESULT") if isinstance(response, dict) else None
    if not isinstance(results, list) or not results:
        raise ValueError("Unexpected Trafikverket RESPONSE.RESULT structure")
    all_items = []
    for result in results:
        if not isinstance(result, dict):
            raise ValueError("Unexpected Trafikverket result")
        if "ERROR" in result:
            raise ValueError("Trafikverket returned an API/schema error")
        items = result.get("Situation", [])
        if isinstance(items, dict):
            items = [items]
        if not isinstance(items, list):
            raise ValueError("Unexpected Situation payload")
        all_items.extend(items)
    if len(all_items) >= LIMIT:
        raise ValueError("Trafikverket query hit limit; incomplete snapshot not published")
    return all_items


def wkt_geojson(wkt):
    """Convert WGS84 WKT POINT or LINESTRING; omit unsupported geometry types."""
    if not isinstance(wkt, str):
        return None
    match = re.fullmatch(r"\s*(POINT|LINESTRING)\s*\(([^()]*)\)\s*", wkt, re.I)
    if not match:
        return None
    kind, coords = match.groups()
    points = []
    for item in coords.split(","):
        nums = item.strip().split()
        if len(nums) != 2:
            return None
        try:
            lon, lat = map(float, nums)
        except ValueError:
            return None
        if not (-180 <= lon <= 180 and -90 <= lat <= 90):
            return None
        points.append([lon, lat])
    if kind.upper() == "POINT" and len(points) == 1:
        return {"type": "Point", "coordinates": points[0]}
    if kind.upper() == "LINESTRING" and len(points) >= 2:
        return {"type": "LineString", "coordinates": points}
    return None


def geometry_of(deviation):
    g = deviation.get("Geometry")
    if not isinstance(g, dict):
        return None
    # Never infer source coordinates from SWEREF99TM; only WGS84 field is used.
    for kind in ("Line", "Point"):
        part = g.get(kind)
        if isinstance(part, dict):
            parsed = wkt_geojson(part.get("WGS84"))
            if parsed:
                return parsed
    return wkt_geojson(g.get("WGS84"))


def normalize(items, now=None):
    now = now or now_utc()
    records = []
    for sit in items:
        if not isinstance(sit, dict) or not sit.get("Id"):
            continue
        deviations = sit.get("Deviation", [])
        if isinstance(deviations, dict):
            deviations = [deviations]
        if not isinstance(deviations, list):
            continue
        for index, d in enumerate(deviations):
            if not isinstance(d, dict):
                continue
            counties = d.get("Counties") or []
            if isinstance(counties, (str, int)):
                counties = [counties]
            county = d.get("CountyNo")
            # The API is already queried for county 25. Guard against unrelated
            # deviations within the same Situation (may cover multiple counties).
            if str(county) != "25" and not (isinstance(counties, list) and any(str(x) == "25" for x in counties)):
                continue
            end = timestamp(d.get("EndTime"))
            if end and end <= now:
                continue
            start = timestamp(d.get("StartTime"))
            road = str(d.get("RoadNumber") or d.get("RoadNumberNumeric") or "").strip()
            records.append({
                "id": str(sit["Id"]) + ":" + str(d.get("Id") or index),
                "title": str(d.get("Header") or d.get("MessageTypeValue") or "Trafikstörning"),
                "message": str(d.get("Message") or ""),
                "category": str(d.get("MessageTypeValue") or d.get("MessageType") or "Övrigt"),
                "severity": str(d.get("SeverityText") or ""),
                "severity_code": d.get("SeverityCode"),
                "road": road,
                "location": str(d.get("LocationDescriptor") or ""),
                "restriction": str(d.get("TrafficRestrictionType") or ""),
                "start": d.get("StartTime") or "",
                "end": d.get("EndTime") or "",
                "updated": sit.get("ModifiedTime") or sit.get("PublicationTime") or "",
                "planned": bool(start and start > now),
                "geometry": geometry_of(d),
                "source_url": PUBLIC,
            })
    records.sort(key=lambda x: (x["updated"], x["id"]), reverse=True)
    return {
        "status": "ok",
        "checked_at_utc": now.isoformat().replace("+00:00", "Z"),
        "source": "Trafikverket Open API, Situation 1.5",
        "source_url": PUBLIC,
        "geographic_scope": "Norrbottens län (länskod 25)",
        "geometry_crs": "EPSG:4326",
        "records": records
    }


def save(payload):
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temp = OUTPUT.with_suffix(".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    os.replace(temp, OUTPUT)


def main():
    key = os.environ.get("TRAFIKVERKET_API_KEY", "").strip()
    if not key:
        save({
            "status": "missing_api_key",
            "checked_at_utc": now_utc().isoformat().replace("+00:00", "Z"),
            "source": "Trafikverket Open API, Situation 1.5",
            "source_url": PUBLIC,
            "records": []
        })
        print("Trafikverket integration awaiting TRAFIKVERKET_API_KEY GitHub Actions secret.")
        return
    records = read_situations(fetch(key))
    result = normalize(records)
    save(result)
    print("Published Norrbotten road deviations:", len(result["records"]))


if __name__ == "__main__":
    main()
