"""Resume una exportación Query de DynamoDB y opcionalmente un log serial.

No usa red, credenciales ni Scan. Acepta Items tipados del CLI o una lista JSON.
"""

import argparse
import json
import re
from collections import Counter
from pathlib import Path

from boto3.dynamodb.types import TypeDeserializer


def load_items(path):
    document = json.loads(path.read_text(encoding="utf-8-sig"))
    items = document.get("Items", []) if isinstance(document, dict) else document
    decoder = TypeDeserializer()
    return [
        {key: decoder.deserialize(value) for key, value in item.items()}
        if isinstance(item.get("thingName"), dict)
        else item
        for item in items
    ]


def summarize(items, published=None):
    """La exportación debe cubrir exactamente la ventana y el Thing del log."""
    things = {item["thingName"] for item in items}
    if len(things) > 1:
        raise ValueError("Analizar un Thing por vez para no mezclar ventanas")
    ids = {item["messageId"] for item in items}
    selected = [item for item in items if published is None or item["messageId"] in published]
    latencies = [int(item["storageLatencyMs"]) for item in selected]
    known = [item for item in selected if item.get("clockKnown")]
    completed = Counter(
        item["event"]["origin"]
        for item in selected
        if item.get("event", {}).get("actuator") == "servo" and item["event"]["to"] == "idle"
    )
    result = {
        "records": len(selected),
        "completedCyclesByOrigin": dict(completed),
        "lowLevelObservations": sum(item["lowLevel"] for item in known if item["levelReady"]),
        "unknownClockRecords": sum(not item.get("clockKnown", False) for item in selected),
        "maximumPreWriteLatencyMs": max(latencies, default=None),
        "negativeLatencies": sum(value < 0 for value in latencies),
        "maximumDroppedCounter": max((int(item["droppedRecords"]) for item in selected), default=0),
    }
    if published is not None:
        result.update(
            {
                "publishedUnique": len(published),
                "storedUnique": len(published & ids),
                "integrityPercent": round(100 * len(published & ids) / len(published), 2)
                if published
                else None,
                "missingIds": sorted(published - ids),
            }
        )
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("history", type=Path)
    parser.add_argument("--serial", type=Path)
    args = parser.parse_args()
    published = None
    if args.serial:
        published = set(
            re.findall(
                r"PUBLISH id=(p4-[a-f0-9]{24}-[1-9][0-9]*)",
                args.serial.read_text(encoding="utf-8-sig"),
            )
        )
    print(json.dumps(summarize(load_items(args.history), published), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
