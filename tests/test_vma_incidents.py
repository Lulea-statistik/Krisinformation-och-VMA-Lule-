import unittest
from scripts.vma_incidents import incident_key,group_messages,classify_group

class IncidentTests(unittest.TestCase):
    def test_incident_id_groups_updates(self):
        records=[{"identifier":"a","incidents":"event-one","msgType":"Alert","status":"Actual","sent":"2026-01-01T10:00:00Z"},
                 {"identifier":"b","incidents":"event-one","msgType":"Update","status":"Actual","sent":"2026-01-01T11:00:00Z"},
                 {"identifier":"c","incidents":"event-one","msgType":"Cancel","status":"Actual","sent":"2026-01-01T12:00:00Z"}]
        grouped=group_messages(records)
        self.assertEqual(len(grouped),1)
        self.assertEqual(classify_group(next(iter(grouped.values()))),"cancelled")
    def test_no_merging_by_time(self):
        self.assertEqual(len(group_messages([{"identifier":"a"},{"identifier":"b"}])),2)
    def test_test_not_actual(self):
        self.assertEqual(classify_group([{"identifier":"x","status":"Test","msgType":"Alert"}]),"not_actual")
    def test_no_id(self):
        self.assertIsNone(incident_key({}))
    def test_missing_explicit_link_stays_separate(self):
        self.assertEqual(len(group_messages([{"incidents":"one","identifier":"x"},{"incidents":"two","identifier":"y"}])),2)
if __name__=="__main__": unittest.main()
