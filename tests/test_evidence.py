"""Evita conclusiones falsas al resumir evidencia de varios intentos/usuarios."""

import unittest
from unittest.mock import Mock, patch

from scripts.analyze_evidence import summarize
from scripts.observe_storage import observe


def row(identifier, thing="thing", origin="edge"):
    return {
        "thingName": thing,
        "messageId": identifier,
        "storageLatencyMs": 200,
        "clockKnown": True,
        "lowLevel": True,
        "levelReady": True,
        "droppedRecords": 0,
        "event": {"actuator": "servo", "to": "idle", "origin": origin},
    }


class EvidenceTests(unittest.TestCase):
    def test_integrity_uses_intersection_not_all_rows_in_export(self):
        result = summarize([row("a"), row("outside")], {"a", "missing"})
        self.assertEqual(result["integrityPercent"], 50)
        self.assertEqual(result["missingIds"], ["missing"])
        self.assertEqual(result["completedCyclesByOrigin"], {"edge": 1})

    def test_multiple_things_are_rejected(self):
        with self.assertRaises(ValueError):
            summarize([row("a"), row("b", thing="other")])

    def test_empty_window_has_no_invented_success_rate(self):
        result = summarize([], set())
        self.assertIsNone(result["integrityPercent"])
        self.assertIsNone(result["maximumPreWriteLatencyMs"])

    def test_only_completed_cycles_count_and_keep_origin(self):
        pressing = row("p")
        pressing["event"]["to"] = "pressing"
        result = summarize([pressing, row("a"), row("b", origin="voz")])
        self.assertEqual(result["completedCyclesByOrigin"], {"edge": 1, "voz": 1})

    def test_clock_errors_are_visible(self):
        record = row("a")
        record.update(storageLatencyMs=-100, clockKnown=False, droppedRecords=3)
        result = summarize([record])
        self.assertEqual(result["negativeLatencies"], 1)
        self.assertEqual(result["unknownClockRecords"], 1)
        self.assertEqual(result["maximumDroppedCounter"], 3)

    @patch("scripts.observe_storage.time.sleep")
    @patch("scripts.observe_storage.time.time", side_effect=[100, 101, 102])
    def test_visibility_latency_uses_observation_after_query(self, clock, sleep):
        table = Mock()
        table.query.side_effect = [
            {"Items": []},
            {"Items": [{"messageId": "a", "publishedAtMs": 100500}]},
        ]
        result = observe(table, "thing", attempts=2)
        self.assertEqual(result["latencyUpperBoundMs"], 1500)
        self.assertTrue(result["withinFiveSeconds"])
        self.assertTrue(table.query.call_args.kwargs["ConsistentRead"])

    @patch("scripts.observe_storage.time.time", side_effect=[100, 101])
    def test_visibility_rejects_future_publication_clock(self, clock):
        table = Mock()
        table.query.return_value = {"Items": [{"messageId": "a", "publishedAtMs": 102000}]}
        self.assertFalse(observe(table, "thing")["measurementValid"])

    @patch("scripts.observe_storage.time.sleep")
    @patch("scripts.observe_storage.time.time", return_value=100)
    def test_visibility_polling_is_bounded(self, clock, sleep):
        table = Mock()
        table.query.return_value = {"Items": []}
        self.assertEqual(observe(table, "thing", attempts=2)["status"], "not_observed")
        self.assertEqual(table.query.call_count, 2)


if __name__ == "__main__":
    unittest.main()
