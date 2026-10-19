import unittest
from datetime import datetime,timezone
from scripts.vma_register import build_register

NOW=datetime(2026,10,19,12,tzinfo=timezone.utc)
def cap(i,kind="Alert",code="2580",expires="2026-10-19T13:00:00Z",status="Actual",incident="synthetic-1",sent="2026-10-19T11:00:00Z"):
    return {"identifier":i,"incidents":incident,"msgType":kind,"status":status,"sent":sent,
        "info":[{"area":[{"geocode":[{"valueName":"Kommun","value":code}]}],"expires":expires}]}
class RegisterTest(unittest.TestCase):
    def test_active_is_never_confirmed(self):
        self.assertEqual(build_register([cap("1")],NOW)[0]["state"],"potentially_active_not_verified")
    def test_expired(self):
        self.assertEqual(build_register([cap("1",expires="2026-10-19T10:00:00Z")],NOW)[0]["state"],"expired")
    def test_unknown_expiry(self):
        self.assertEqual(build_register([cap("1",expires=None)],NOW)[0]["state"],"unverified_expiration")
    def test_cancel_and_multiarea(self):
        one=cap("1",code="2580")
        two=cap("2",kind="Cancel",code="2582",sent="2026-10-19T11:30:00Z")
        x=build_register([one,two],NOW)[0]
        self.assertEqual(x["state"],"cancelled")
        self.assertEqual([m["code"] for m in x["municipalities"]],["2580","2582"])
        self.assertEqual(x["message_count"],2)
    def test_filter_test(self):
        self.assertEqual(build_register([cap("1",status="Test")],NOW)[0]["state"],"excluded_non_actual")
    def test_update_count(self):
        self.assertEqual(build_register([cap("1"),cap("2",kind="Update")],NOW)[0]["update_count"],1)
if __name__=="__main__":unittest.main()
