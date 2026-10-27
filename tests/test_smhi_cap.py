#!/usr/bin/env python3
import unittest
from datetime import datetime, timezone
from xml.etree import ElementTree as ET
from scripts.smhi_cap import cap_polygons, parse_cap, collect

CAP = 'urn:oasis:names:tc:emergency:cap:1.2'
def sample(t='Alert'):
 return ET.fromstring(f'''<alert xmlns="{CAP}"><identifier>test-a</identifier><status>Actual</status><msgType>{t}</msgType><sent>2026-10-27T08:00:00+00:00</sent><info><language>sv-SE</language><event>Snöfall</event><severity>Severe</severity><area><areaDesc>Testområde</areaDesc><polygon>65,22 65,23 66,23 65,22</polygon></area></info></alert>''')
class TestCAP(unittest.TestCase):
 def test_coordinate_order(self):
  a=sample().find('.//{%s}area'%CAP)
  self.assertEqual(cap_polygons(a)['coordinates'][0][0],[22.0,65.0])
 def test_alert(self):
  d=parse_cap(sample(),'https://opendata-download-warnings.smhi.se/ibww/api/version/1/cap/test')
  self.assertEqual(d['entries'][0]['event'],'Snöfall')
 def test_cancel(self):
  self.assertEqual(parse_cap(sample('Cancel'),'https://opendata-download-warnings.smhi.se/ibww/api/version/1/cap/test')['entries'],[])
if __name__=='__main__':unittest.main()
