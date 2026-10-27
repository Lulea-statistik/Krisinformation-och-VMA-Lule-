#!/usr/bin/env python3
"""Collect current SMHI CAP warnings without inventing geographic precision.

Source: https://opendata-download-warnings.smhi.se/ibww/api/version/1/cap.xml
CAP 1.2 polygons use WGS84 (EPSG:4326) lat,lon; GeoJSON uses lon,lat.
A failed collection must never overwrite the last successful snapshot.
"""
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

FEED = "https://opendata-download-warnings.smhi.se/ibww/api/version/1/cap.xml"
CAP_PREFIX = "/ibww/api/version/1/"
HOST = "opendata-download-warnings.smhi.se"
OUTPUT = Path("data/smhi_cap_warnings.json")
NS = {"cap": "urn:oasis:names:tc:emergency:cap:1.2"}


def utc_now():
    return datetime.now(timezone.utc)


def fetch_xml(url):
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != HOST:
        raise ValueError("CAP URL is not from the authorized SMHI host")
    if url != FEED and not parsed.path.startswith(CAP_PREFIX):
        raise ValueError("Unrecognized SMHI CAP URL")
    request = Request(url, headers={
        "User-Agent": "Lulea-statistik-SMHI-CAP/1.0 (public-information-project)",
        "Accept": "application/xml, text/xml, application/rss+xml"
    })
    # RSS can exceed 3 MB when numerous alerts and their metadata are present.
    # Keep distinct, generous upper bounds to avoid memory exhaustion.
    limit = 64 * 1024 * 1024 if url == FEED else 16 * 1024 * 1024
    with urlopen(request, timeout=35) as response:
        declared = response.headers.get("Content-Length")
        if declared and int(declared) > limit:
            raise ValueError(f"SMHI CAP document too large: {declared} bytes (limit {limit})")
        payload = response.read(limit + 1)
    if len(payload) > limit:
        raise ValueError(f"SMHI CAP document too large: >{limit} bytes")
    print(f"Fetched SMHI CAP XML: {len(payload)} bytes from {url}", flush=True)
    return ET.fromstring(payload)


def txt(node, path):
    value = node.findtext(path, default="", namespaces=NS)
    return (value or "").strip()


def parse_time(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def cap_polygons(area):
    """Convert CAP WGS84 latitude,longitude pairs to RFC 7946 lon,lat."""
    rings = []
    for node in area.findall("cap:polygon", NS):
        ring = []
        for pair in (node.text or "").split():
            parts = pair.split(",")
            if len(parts) != 2:
                ring = []
                break
            try:
                lat, lon = float(parts[0]), float(parts[1])
            except ValueError:
                ring = []
                break
            if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                ring = []
                break
            ring.append([lon, lat])
        if len(ring) >= 3:
            if ring[0] != ring[-1]:
                ring.append(ring[0])
            if len(ring) >= 4:
                rings.append(ring)
    if not rings:
        return None
    if len(rings) == 1:
        return {"type": "Polygon", "coordinates": [rings[0]]}
    return {"type": "MultiPolygon", "coordinates": [[ring] for ring in rings]}


def parse_cap(root, url):
    if root.tag != "{urn:oasis:names:tc:emergency:cap:1.2}alert":
        raise ValueError("Expected CAP 1.2 alert")
    message_type = txt(root, "cap:msgType")
    status = txt(root, "cap:status")
    identifier = txt(root, "cap:identifier")
    if not identifier:
        raise ValueError("Missing CAP identifier")
    references = re.findall(r"\S+?,([^,\s]+),\S+", txt(root, "cap:references"))
    sent = txt(root, "cap:sent")
    entries = []
    if status.lower() == "actual" and message_type.lower() in ("alert", "update"):
        infos = root.findall("cap:info", NS)
        swedish = [n for n in infos if txt(n, "cap:language").lower().startswith("sv")]
        chosen = swedish if swedish else infos[:1]
        for info_idx, info in enumerate(chosen):
            severity = txt(info, "cap:severity")
            for area_idx, area in enumerate(info.findall("cap:area", NS)):
                entries.append({
                    "id": identifier + ":" + str(info_idx) + ":" + str(area_idx),
                    "identifier": identifier,
                    "cap_url": url,
                    "sent": sent,
                    "event": txt(info, "cap:event"),
                    "headline": txt(info, "cap:headline"),
                    "description": txt(info, "cap:description"),
                    "instruction": txt(info, "cap:instruction"),
                    "severity": severity,
                    "urgency": txt(info, "cap:urgency"),
                    "certainty": txt(info, "cap:certainty"),
                    "effective": txt(info, "cap:effective"),
                    "onset": txt(info, "cap:onset"),
                    "expires": txt(info, "cap:expires"),
                    "area_name": txt(area, "cap:areaDesc"),
                    "geometry": cap_polygons(area),
                })
    return {"identifier": identifier, "references": references, "type": message_type, "status": status, "entries": entries}


def collect(feed, previous, downloader=fetch_xml, now=None):
    now = now or utc_now()
    if feed.tag == "{urn:oasis:names:tc:emergency:cap:1.2}alert":
        raise ValueError("CAP endpoint returned a single alert rather than a feed")
    channel = feed.find("channel") if feed.tag == "rss" else None
    urls = []
    seen = set()
    items = channel.findall("item") if channel is not None else feed.findall("{http://www.w3.org/2005/Atom}entry")
    if channel is None and not items:
        raise ValueError("Unknown SMHI CAP feed format")
    for item in items:
        link = (item.findtext("link") or "").strip()
        if not link:
            atom_link = item.find("{http://www.w3.org/2005/Atom}link")
            link = atom_link.get("href", "") if atom_link is not None else ""
        if not link or link in seen:
            continue
        parsed = urlparse(link)
        if parsed.scheme != "https" or parsed.hostname != HOST or not parsed.path.startswith(CAP_PREFIX):
            raise ValueError("Unexpected CAP URL in feed")
        seen.add(link)
        urls.append(link)
    # If a CAP item cannot be loaded, do not publish a potentially incomplete snapshot.
    if len(urls) > 250:
        raise ValueError("Unexpected number of CAP links")
    messages = {}
    for url in urls:
        messages[url] = parse_cap(downloader(url), url)
    # CAP Update and Cancel references invalidate preceding messages.
    invalidated = {
        ref
        for message in messages.values()
        for ref in message.get("references", [])
    }
    entries = []
    for message in messages.values():
        if message.get("identifier") in invalidated:
            continue
        for entry in message.get("entries", []):
            expiry = parse_time(entry.get("expires"))
            if expiry is not None and expiry <= now:
                continue
            entries.append(entry)
    entries.sort(key=lambda e: (e.get("onset") or "", e.get("id") or ""))
    return {
        "status": "ok",
        "checked_at_utc": now.isoformat().replace("+00:00", "Z"),
        "source": FEED,
        "crs": "EPSG:4326",
        "area_count": len(entries),
        "warnings": entries,
        "messages": messages,
    }


def main():
    old = {}
    if OUTPUT.exists():
        try:
            old = json.loads(OUTPUT.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            pass
    result = collect(fetch_xml(FEED), old)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    # Keep CAP cache small by retaining only messages referenced by the current RSS feed.
    temp = OUTPUT.with_suffix(".tmp")
    temp.write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    os.replace(temp, OUTPUT)
    print("SMHI CAP snapshot:", result["area_count"], "warning areas; timestamp:", result["checked_at_utc"])


if __name__ == "__main__":
    main()
