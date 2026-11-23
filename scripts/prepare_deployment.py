"""Genera artefactos locales reproducibles; no accede a AWS ni incluye secretos."""

import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]


def main():
    destination = ROOT / ".local" / "deployment"
    destination.mkdir(parents=True, exist_ok=True)
    template = json.loads(
        (ROOT / "infra/practica4-stack.template.json").read_text(encoding="utf-8")
    )
    template["Resources"]["StorageFunction"]["Properties"]["Code"] = {
        "ZipFile": (ROOT / "backend/storage_function.py").read_text(encoding="utf-8")
    }
    template["Resources"]["HistoryRule"]["Properties"]["TopicRulePayload"]["Sql"] = (
        ROOT / "infra/history-rule.sql"
    ).read_text(encoding="utf-8")
    output = destination / "practica4-stack.json"
    output.write_text(json.dumps(template, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if output.stat().st_size > 51200:
        raise ValueError("La plantilla excede el límite de carga directa CloudFormation")
    with ZipFile(destination / "alexa.zip", "w", ZIP_DEFLATED) as archive:
        archive.write(ROOT / "backend/lambda_function.py", "lambda_function.py")
    print("Preparados .local/deployment/practica4-stack.json y alexa.zip (sin despliegue).")


if __name__ == "__main__":
    main()
