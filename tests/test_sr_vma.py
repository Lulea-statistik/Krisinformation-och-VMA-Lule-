"""Syntetiska testfall för VMA-kommunfilter. Inga verkliga larm används."""
import importlib.util
import unittest
from pathlib import Path

module_path = Path(__file__).resolve().parents[1] / "scripts" / "sr_vma_pilot.py"
spec = importlib.util.spec_from_file_location("sr_vma_pilot", module_path)
pilot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pilot)

def alert(code, status="Actual", kind="Alert", areas=None):
    return {"status":status, "msgType":kind, "info":[{"area": areas if areas is not None else [
        {"geocode":[{"valueName":"Kommun","value":code}]}]}]}

class FilterTests(unittest.TestCase):
    def test_lulea(self):
        self.assertTrue(pilot.is_lulea_actual_alert(alert("2580")))
    def test_other_municipality(self):
        self.assertFalse(pilot.is_lulea_actual_alert(alert("2582")))
    def test_exercise_and_test(self):
        for status in ("Exercise","Test"):
            self.assertFalse(pilot.is_lulea_actual_alert(alert("2580",status=status)))
    def test_cancel_not_active(self):
        self.assertFalse(pilot.is_lulea_actual_alert(alert("2580",kind="Cancel")))
    def test_missing_and_null_fields(self):
        self.assertFalse(pilot.is_lulea_actual_alert({"status":"Actual","msgType":"Alert","info":None}))
    def test_no_national_assumption(self):
        self.assertFalse(pilot.is_lulea_actual_alert(alert("",areas=[{"geocode":[{"valueName":"Sverige","value":"Sverige"}]}])))
    def test_mixed_areas(self):
        self.assertTrue(pilot.is_lulea_actual_alert(alert("",areas=[
            {"geocode":[{"valueName":"Kommun","value":"2582"}]},
            {"geocode":[{"valueName":"Kommun","value":"2580"}]}])))
if __name__=="__main__":
    unittest.main()
