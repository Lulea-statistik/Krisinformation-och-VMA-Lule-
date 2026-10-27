#!/usr/bin/env python3
import unittest
from datetime import datetime, timezone
from scripts.smhi_cap import normalize, verified_geometry

EXAMPLE = [{
 "id": 123,
 "event": {"sv": "Snöfall", "code": "SNOW"},
 "warningAreas": [{
  "id": 456,
  "approximateStart": "2026-10-27T11:00:00Z",
  "approximateEnd": "2026-10-28T12:00:00Z",
  "published": "2026-10-27T08:00:00Z",
  "areaName": {"sv": "Delar av Norrbotten"},
  "eventDescription": {"sv": "Snöfall"},
  "warningLevel": {"sv": "Gul", "code": "YELLOW"},
  "descriptions": [
   {"title": {"code": "INCIDENT"}, "text": {"sv": "Stora snömängder."}},
   {"title": {"code": "AFFECT"}, "text": {"sv": "Var försiktig i trafiken."}}
  ],
  "area": {
   "crs": {"type": "name", "properties": {"name": "EPSG:4326"}},
   "type": "Feature",
   "geometry": {"type": "Polygon", "coordinates": [[[22, 65], [23, 65], [23, 66], [22, 65]]]}
  }
 }]
}]

NOW = datetime(2026, 10, 27, 9, 0, tzinfo=timezone.utc)

class TestSmhiWarnings(unittest.TestCase):
 def test_normalize_expected_geometry_and_level(self):
  data = normalize(EXAMPLE, now=NOW)
  item = data["warnings"][0]
  self.assertEqual(item["id"], "123:456")
  self.assertEqual(item["severity"], "YELLOW")
  self.assertEqual(item["severity_label"], "Gul")
  self.assertEqual(item["event"], "Snöfall")
  self.assertEqual(item["geometry"]["coordinates"][0][0], [22, 65])
  self.assertEqual(item["instruction"], "Var försiktig i trafiken.")
  self.assertTrue(item["source_crs_declared"])

 def test_empty_current_feed_valid(self):
  self.assertEqual(normalize([], now=NOW)["area_count"], 0)

 def test_expired_warning_removed(self):
  now = datetime(2026, 10, 29, tzinfo=timezone.utc)
  self.assertEqual(normalize(EXAMPLE, now=now)["warnings"], [])

 def test_bad_format_rejected(self):
  with self.assertRaises(ValueError):
   normalize({"bad": "object"}, now=NOW)

 def test_wrong_crs_rejected(self):
  bad = {"type": "Feature", "crs": {"properties": {"name": "EPSG:3006"}},
         "geometry": EXAMPLE[0]["warningAreas"][0]["area"]["geometry"]}
  with self.assertRaises(ValueError):
   verified_geometry(bad)

if __name__ == "__main__":
 unittest.main()
