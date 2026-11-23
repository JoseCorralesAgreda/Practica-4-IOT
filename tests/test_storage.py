"""Pruebas sin AWS: validación, idempotencia, aislamiento y fallos transitorios."""

import copy
import unittest
from unittest.mock import Mock

from botocore.exceptions import ClientError

from backend.storage_function import store_record

NOW = 1800000001000


def valid_event():
    return {
        "thingName": "ambientador-dos",
        "receivedAtMs": NOW - 100,
        "reported": {
            "schemaVersion": 4,
            "messageId": "p4-" + "a" * 24 + "-1",
            "observedAtMs": NOW - 1000,
            "publishedAtMs": NOW - 500,
            "sampledAt": (NOW - 1000) // 1000,
            "presence": True,
            "pirReady": True,
            "automatic": True,
            "levelReady": True,
            "lowLevel": True,
            "ledColor": "orange",
            "servoState": "idle",
            "servoAngle": 0,
            "cyclesSinceBoot": 3,
            "uptimeSeconds": 100,
            "droppedRecords": 0,
            "cooldownSeconds": 300,
            "recordKind": "reading",
            "event": None,
        },
    }


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.table = Mock()
        self.event = valid_event()

    def test_valid_reading_enriches_without_mutating_input(self):
        original = copy.deepcopy(self.event)
        self.assertEqual(store_record(self.event, self.table, NOW)["status"], "stored")
        item = self.table.put_item.call_args.kwargs["Item"]
        self.assertEqual(item["thingName"], "ambientador-dos")
        self.assertEqual(item["storageLatencyMs"], 500)
        self.assertEqual(item["expiresAt"], NOW // 1000 + 604800)
        self.assertNotIn("event", item)
        self.assertEqual(self.event, original)

    def test_bad_types_ranges_and_inconsistent_states_are_discarded(self):
        for field, value in (
            ("schemaVersion", True),
            ("presence", 1),
            ("lowLevel", "false"),
            ("cooldownSeconds", 4),
            ("cooldownSeconds", 86401),
            ("servoAngle", True),
            ("servoAngle", 180),
            ("servoState", []),
            ("ledColor", "green"),
            ("messageId", "bad"),
            ("observedAtMs", 10),
            ("publishedAtMs", NOW + 99999),
            ("cyclesSinceBoot", -1),
            ("sampledAt", 0),
            ("recordKind", "bogus"),
            ("recordKind", "event"),
        ):
            with self.subTest(field=field, value=value):
                event = copy.deepcopy(self.event)
                event["reported"][field] = value
                self.assertEqual(store_record(event, self.table, NOW)["status"], "discarded")
        self.table.put_item.assert_not_called()

    def test_malformed_envelopes_never_write(self):
        for event in (
            None,
            [],
            {},
            {"thingName": "x/y"},
            {"thingName": "valid", "receivedAtMs": True},
        ):
            self.assertEqual(store_record(event, self.table, NOW)["status"], "discarded")
        self.table.put_item.assert_not_called()

    def test_servo_event_retains_voice_origin(self):
        self.event["reported"].update(
            recordKind="event",
            event={
                "actuator": "servo",
                "from": "returning",
                "to": "idle",
                "origin": "voz",
            },
        )
        self.assertEqual(store_record(self.event, self.table, NOW)["status"], "stored")
        self.assertEqual(self.table.put_item.call_args.kwargs["Item"]["event"]["origin"], "voz")

    def test_led_event_cannot_claim_voice_origin(self):
        self.event["reported"].update(
            recordKind="event",
            event={
                "actuator": "rgb",
                "from": "green",
                "to": "orange",
                "origin": "voz",
            },
        )
        self.assertEqual(store_record(self.event, self.table, NOW)["status"], "discarded")
        self.event["reported"]["event"]["origin"] = "edge"
        self.assertEqual(store_record(self.event, self.table, NOW)["status"], "stored")

    def test_duplicate_is_successful_no_second_record(self):
        self.table.put_item.side_effect = ClientError(
            {"Error": {"Code": "ConditionalCheckFailedException"}}, "PutItem"
        )
        self.assertEqual(store_record(self.event, self.table, NOW), {"status": "duplicate"})
        self.assertIn(
            "attribute_not_exists", self.table.put_item.call_args.kwargs["ConditionExpression"]
        )

    def test_transient_database_errors_are_retried_by_lambda(self):
        self.table.put_item.side_effect = ClientError(
            {"Error": {"Code": "ProvisionedThroughputExceededException"}}, "PutItem"
        )
        with self.assertRaises(ClientError):
            store_record(self.event, self.table, NOW)

    def test_unknown_clock_is_explicit_and_key_stays_stable(self):
        self.event["reported"].update(observedAtMs=0, sampledAt=0)
        store_record(self.event, self.table, NOW)
        first = self.table.put_item.call_args.kwargs["Item"]
        store_record(self.event, self.table, NOW + 1000)
        second = self.table.put_item.call_args.kwargs["Item"]
        self.assertEqual(first["recordKey"], second["recordKey"])
        self.assertFalse(first["clockKnown"])

    def test_same_message_on_two_things_has_separate_partition(self):
        store_record(self.event, self.table, NOW)
        first = self.table.put_item.call_args.kwargs["Item"]
        self.event["thingName"] = "thing"
        store_record(self.event, self.table, NOW)
        second = self.table.put_item.call_args.kwargs["Item"]
        self.assertNotEqual(first["thingName"], second["thingName"])


if __name__ == "__main__":
    unittest.main()
