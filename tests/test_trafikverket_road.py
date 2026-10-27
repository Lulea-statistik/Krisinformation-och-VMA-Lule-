#!/usr/bin/env python3
import unittest
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from scripts.trafikverket_road import build_query, read_situations, normalize, wkt_geojson

NOW = datetime(2026, 10, 27, 8, 0, tzinfo=timezone.utc)

class TestTrafikverketRoad(unittest.TestCase):
    def test_xml_auth_escaped_and_filter(self):
        root = ET.fromstring(build_query('abc"&<'))
        self.assertEqual(root.find("LOGIN").get("authenticationkey"), 'abc"&<')
        self.assertEqual(root.find("QUERY").get("objecttype"), "Situation")
        self.assertEqual(root.find(".//EQ").get("value"), "25")

    def test_payload_error_not_silently_empty(self):
        with self.assertRaises(ValueError):
            read_situations({"RESPONSE": {"RESULT": [{"ERROR": {"MESSAGE": "bad key"}}]}})
        with self.assertRaises(ValueError):
            read_situations({"RESPONSE": {"RESULT": []}})

    def test_wgs84_wkt_order(self):
        self.assertEqual(wkt_geojson("POINT (22.14 65.58)"),
                         {"type": "Point", "coordinates": [22.14, 65.58]})
        self.assertEqual(wkt_geojson("LINESTRING (22 65, 23 65)")["type"], "LineString")
        self.assertIsNone(wkt_geojson("POINT (740000 7298000)"))

    def test_active_county_filter_and_geo(self):
        items = [{
            "Id": "s1", "ModifiedTime": "2026-10-27T07:00:00Z",
            "Deviation": [
                {"Id": "d1", "CountyNo": 25, "Header": "Exempel: Vägarbete",
                 "MessageTypeValue": "Vägarbete", "RoadNumber": "E 4",
                 "StartTime": "2026-10-27T00:00:00Z",
                 "EndTime": "2026-10-27T12:00:00Z",
                 "Geometry": {"Point": {"WGS84": "POINT (22.14 65.58)"}}},
                {"Id": "d2", "CountyNo": 14, "Header": "Annan kommun"},
                {"Id": "d3", "CountyNo": 25, "Header": "För gammal",
                 "EndTime": "2026-10-26T00:00:00Z"},
            ]
        }]
        normalized = normalize(items, now=NOW)
        self.assertEqual(len(normalized["records"]), 1)
        self.assertEqual(normalized["records"][0]["geometry"]["coordinates"], [22.14, 65.58])
        self.assertEqual(normalized["geometry_crs"], "EPSG:4326")

    def test_empty_result_is_valid(self):
        self.assertEqual(normalize([], now=NOW)["records"], [])

if __name__ == "__main__":
    unittest.main()
