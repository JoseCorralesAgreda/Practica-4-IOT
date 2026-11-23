"""Validación e histórico del Shadow. Handler: storage_function.lambda_handler.

Solo recibe la regla IoT autorizada. No controla actuadores ni accede a vínculos.
Los reintentos conservan la clave y no crean nuevos registros.
"""

import os
import re
import time

import boto3
from botocore.exceptions import ClientError

THING_PATTERN = re.compile(r"[A-Za-z0-9:_-]{1,128}")
MESSAGE_PATTERN = re.compile(r"p4-[a-f0-9]{24}-[1-9][0-9]{0,9}")
SERVO_STATES = {"idle", "pressing", "returning"}
COLORS = {"off", "green", "orange"}
_table = None


def integer(value, minimum, maximum):
    """bool hereda de int en Python: rechazarlo explícitamente."""
    return type(value) is int and minimum <= value <= maximum


def validate_record(event, stored_at_ms):
    """Devuelve una copia permitida del mensaje; ValueError implica descarte."""
    if not isinstance(event, dict):
        raise ValueError("envelope")
    thing = event.get("thingName")
    received = event.get("receivedAtMs")
    reported = event.get("reported")
    if not isinstance(thing, str) or not THING_PATTERN.fullmatch(thing):
        raise ValueError("thingName")
    if not integer(received, 1700000000000, stored_at_ms + 10000):
        raise ValueError("receivedAtMs")
    if not isinstance(reported, dict):
        raise ValueError("reported")
    message = reported.get("messageId")
    if not isinstance(message, str) or not MESSAGE_PATTERN.fullmatch(message):
        raise ValueError("messageId")
    if type(reported.get("schemaVersion")) is not int or reported["schemaVersion"] != 4:
        raise ValueError("schemaVersion")
    for field in ("presence", "pirReady", "automatic", "levelReady", "lowLevel"):
        if type(reported.get(field)) is not bool:
            raise ValueError(field)
    ranges = {
        "cooldownSeconds": (5, 86400),
        "cyclesSinceBoot": (0, 4294967295),
        "uptimeSeconds": (0, 4294967295),
        "droppedRecords": (0, 4294967295),
        "observedAtMs": (0, received + 10000),
        "publishedAtMs": (1700000000000, received + 10000),
        "sampledAt": (0, (received + 10000) // 1000),
    }
    for field, bounds in ranges.items():
        if not integer(reported.get(field), *bounds):
            raise ValueError(field)
    observed = reported["observedAtMs"]
    if observed != 0 and observed < 1700000000000:
        raise ValueError("observedAtMs")
    if abs(reported["sampledAt"] * 1000 - observed) > 2000:
        raise ValueError("sampledAt inconsistent")
    if observed > reported["publishedAtMs"] + 10000:
        raise ValueError("observation after publication")
    servo = reported.get("servoState")
    color = reported.get("ledColor")
    if not isinstance(servo, str) or servo not in SERVO_STATES:
        raise ValueError("servoState")
    if not isinstance(color, str) or color not in COLORS:
        raise ValueError("ledColor")
    expected_color = (
        "off" if not reported["levelReady"] else ("orange" if reported["lowLevel"] else "green")
    )
    if color != expected_color:
        raise ValueError("ledColor inconsistent")
    angle = reported.get("servoAngle")
    if type(angle) is not int or angle != (180 if servo == "pressing" else 0):
        raise ValueError("servoAngle")
    kind = reported.get("recordKind")
    if kind not in ("reading", "event"):
        raise ValueError("recordKind")
    transition = reported.get("event")
    if kind == "event":
        if not isinstance(transition, dict):
            raise ValueError("event")
        actuator = transition.get("actuator")
        valid_transitions = {
            "servo": {("idle", "pressing"), ("pressing", "returning"), ("returning", "idle")},
            "rgb": {("off", "green"), ("off", "orange"), ("green", "orange"), ("orange", "green")},
        }
        if not isinstance(actuator, str) or actuator not in valid_transitions:
            raise ValueError("actuator")
        source, target = transition.get("from"), transition.get("to")
        if not isinstance(source, str) or not isinstance(target, str):
            raise ValueError("transition types")
        if (source, target) not in valid_transitions[actuator]:
            raise ValueError("transition")
        if target != (servo if actuator == "servo" else color):
            raise ValueError("transition inconsistent")
        if transition.get("origin") not in ("voz", "edge"):
            raise ValueError("origin")
        if actuator == "rgb" and transition["origin"] != "edge":
            raise ValueError("rgb origin")
    elif transition is not None:
        raise ValueError("unexpected event")
    fields = (
        *ranges,
        "presence",
        "pirReady",
        "automatic",
        "levelReady",
        "lowLevel",
        "servoState",
        "servoAngle",
        "ledColor",
        "recordKind",
        "schemaVersion",
    )
    item = {key: reported[key] for key in fields}
    item.update(
        {
            "thingName": thing,
            "recordKey": f"{observed:013d}#{message}",
            "messageId": message,
            "receivedAtMs": received,
            "storedAtMs": stored_at_ms,
            "clockKnown": observed != 0,
            # Tiempo previo a PutItem: no confirma todavía la visibilidad de la fila.
            # Incluye reintentos y depende de la precisión del reloj ESP32.
            "storageLatencyMs": stored_at_ms - reported["publishedAtMs"],
            "expiresAt": stored_at_ms // 1000 + 7 * 86400,
        }
    )
    if transition:
        item["event"] = {key: transition[key] for key in ("actuator", "from", "to", "origin")}
    return item


def store_record(event, table, now_ms=None):
    """Descarta inválidos/duplicados; propaga fallos AWS para activar reintentos."""
    now_ms = int(time.time() * 1000) if now_ms is None else now_ms
    try:
        item = validate_record(event, now_ms)
    except ValueError as error:
        return {"status": "discarded", "reason": str(error)}
    try:
        table.put_item(Item=item, ConditionExpression="attribute_not_exists(recordKey)")
    except ClientError as error:
        if error.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return {"status": "duplicate"}
        raise
    return {"status": "stored", "messageId": item["messageId"]}


def lambda_handler(event, context):
    """Inicializa boto3 solo en ejecución; utiliza las credenciales del rol IAM."""
    global _table
    if _table is None:
        _table = boto3.resource("dynamodb").Table(os.environ["HISTORY_TABLE"])
    return store_record(event, _table)
