"""Observa el próximo registro con Query consistente; requiere AWS gratuito verificado.

Ejecutar antes de provocar un evento. Máximo 20 consultas de 10 filas, sin Scan.
Usar reloj sincronizado y cola vacía para una prueba de latencia estable.
"""

import argparse
import json
import time

import boto3
from boto3.dynamodb.conditions import Key


def observe(table, thing, attempts=20, interval=0.5):
    started_ms = int(time.time() * 1000)
    for attempt in range(attempts):
        result = table.query(
            KeyConditionExpression=Key("thingName").eq(thing)
            & Key("recordKey").gte(f"{started_ms:013d}#"),
            ConsistentRead=True,
            Limit=10,
        )
        visible_ms = int(time.time() * 1000)
        items = result.get("Items", [])
        if items:
            item = items[0]
            published_ms = int(item["publishedAtMs"])
            latency = visible_ms - published_ms
            # El observador debe arrancar antes de la primera publicación.
            valid = started_ms <= published_ms <= visible_ms
            return {
                "status": "visible",
                "queries": attempt + 1,
                "messageId": item["messageId"],
                "publishedAtMs": published_ms,
                "visibleAtMs": visible_ms,
                "latencyUpperBoundMs": latency,
                "measurementValid": valid,
                "withinFiveSeconds": valid and latency <= 5000,
            }
        if attempt + 1 < attempts:
            time.sleep(interval)
    return {"status": "not_observed", "queries": attempts, "measurementValid": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--table", required=True)
    parser.add_argument("--thing", required=True)
    parser.add_argument("--region", default="us-east-2")
    args = parser.parse_args()
    table = boto3.resource("dynamodb", region_name=args.region).Table(args.table)
    print(json.dumps(observe(table, args.thing), indent=2))


if __name__ == "__main__":
    main()
