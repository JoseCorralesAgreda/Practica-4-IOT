"""Estimación determinista, sin llamadas AWS; no garantiza gratuidad de la cuenta."""

import argparse
import json


def estimate(
    days=30,
    hours_per_day=2,
    cycles_per_day=20,
    presence_changes=40,
    level_changes=2,
    voice_requests=20,
):
    seconds = days * hours_per_day * 3600
    # Margen: muestra adicional por cada evento de servo y cada cambio PIR/modo.
    periodic = seconds // 60
    events = days * (3 * cycles_per_day + level_changes + 1)
    extra_readings = days * (3 * cycles_per_day + presence_changes + voice_requests + 1)
    records = periodic + events + extra_readings
    voice = days * voice_requests
    # Presupuesto conservador: update + accepted + documents + delta por publicación.
    # Operaciones Shadow se facturan por bloques de 1 KB; provisionar hasta 2 bloques.
    return {
        "days": days,
        "hoursPerDay": hours_per_day,
        "records": records,
        "mqttMessageBudget": 4 * records + 6 * voice,
        "shadowOperationUnitsBudget": 2 * (records + 2 * voice),
        "ruleTriggers": records,
        "ruleActions": records,
        "lambdaInvocations": records + voice,
        "lambdaGbSecondsAt128MbAnd200Ms": round((records + voice) * 0.125 * 0.2, 2),
        "dynamoWrites": records + voice,
        "historyWriteUnitsAt2Kb": 2 * records,
        "connectionMinutes": seconds // 60,
        "historyCapacityRCU": 1,
        "historyCapacityWCU": 5,
        "historyBytesAt7DaysAnd2Kb": round(records * 2048 * 7 / days),
        "note": "Sumar recursos existentes, reintentos, lecturas paginadas y logs. Comparar con la oferta real de la cuenta.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hours-per-day", type=int, default=2, choices=range(1, 25))
    args = parser.parse_args()
    print(json.dumps(estimate(hours_per_day=args.hours_per_day), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
