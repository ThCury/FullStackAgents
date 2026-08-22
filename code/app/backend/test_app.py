import unittest

import app


class RivexxTest(unittest.TestCase):
    def test_create_nonconformity_requires_audit_fields(self):
        with self.assertRaises(ValueError):
            app.create_nonconformity({"description": "x"})

    def test_create_nonconformity_saves_record(self):
        item = app.create_nonconformity({
            "description": "Defeito dimensional",
            "lot_code": "lote-4521",
            "responsible": "Teste",
            "shift": "b",
            "equipment": "inj-04",
            "line": "4",
        })
        self.assertEqual(item["lot_code"], "LOTE-4521")
        self.assertEqual(item["equipment"], "INJ-04")

    def test_root_cause_has_five_whys_and_action_plan(self):
        result = app.analyze_root_cause("NC-1001")
        self.assertEqual(len(result["five_whys"]), 5)
        self.assertEqual(len(result["action_plan"]), 3)
        self.assertIn("INJ-04", result["suggested_causes"][0]["cause"])

    def test_trace_lot_returns_chain(self):
        lot = app.trace_lot("lote-4521")
        self.assertEqual(lot["supplier"], "Polimix Resinas")
        self.assertEqual(lot["equipment"], "INJ-04")
        self.assertIn("Carla Mendes", lot["operators"])
        self.assertIn("LOTE-4519", lot["correlated_lots"])

    def test_squad_observability_returns_logs(self):
        result = app.run_squad_observability("Briefing Rivexx.")
        self.assertEqual(result["status"], "done")
        self.assertEqual(result["summary"]["stories"], 3)
        self.assertEqual(result["summary"]["approved"], 3)
        self.assertGreaterEqual(len(result["communication_log"]), 6)
        self.assertEqual(result["communication_log"][0]["from_agent"], "Analyst Agent")

    def test_squad_observability_requires_briefing(self):
        with self.assertRaises(ValueError):
            app.run_squad_observability("")


if __name__ == "__main__":
    unittest.main()
