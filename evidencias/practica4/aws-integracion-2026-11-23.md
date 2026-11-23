# Integración AWS — 23 de noviembre de 2026

Registro de operaciones comprobadas, no informe final ni evidencia física. Las respuestas sanitizadas están en [aws-integracion-2026-11-23.json](aws-integracion-2026-11-23.json). Los datos de ensayo fueron sintéticos y se eliminaron al terminar.

## Identidad y condición gratuita

- CLI 2.39.6 autenticado mediante `aws login`; STS confirmó cuenta `679937333206` y rol `AccountFullAccessRole`. La cuenta `861215318765` no se modificó.
- Plan `FREE`, estado `ACTIVE`, créditos restantes `119.94 USD`, vencimiento `2027-05-07T21:32:10.160000Z`. Comprobado antes de crear, antes de habilitar la regla y al finalizar.
- `get-free-tier-usage` devolvió `[]`, sin página siguiente. No equivale a consumo cero. No se consultó Cost Explorer ni se cambió el plan. El saldo mostrado puede reflejar consumo con demora.
- Referencias de condiciones: [planes AWS](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/free-tier-plans.html) e [IoT Core elegible para créditos](https://aws.amazon.com/iot-core/pricing/).

## Configuración comprobada

| Recurso | Resultado |
|---|---|
| Región | `us-east-2` |
| Pila `ambientador-p4` | `UPDATE_COMPLETE` |
| Regla `ambientador_p4_history` | Habilitada; SQL coincide con `infra/history-rule.sql` |
| Lambda `ambientador-p4-storage` | Python 3.13, handler `index.lambda_handler`, 128 MB, 10 s; actualización correcta |
| Histórico | `ambientador-p4-HistoryTable-YBDZ42IAGZOK`, ACTIVE, 1 RCU / 5 WCU, TTL `expiresAt` ENABLED |
| Lambda `Alexa` | Código actualizado, SHA-256 coincide con ZIP local; Python 3.13 y handler conservados |
| Entorno de Alexa | Verificados los cuatro campos requeridos y coincidencia del endpoint ATS, sin imprimir valores |
| Disparador de Alexa | Permiso existente restringido a la skill mediante EventSourceToken, conservado |
| Vinculaciones | `AmbientadorVinculaciones` ACTIVE y PAY_PER_REQUEST; filas existentes no modificadas |
| Thing `thing` | Certificado ACTIVE, política limitada a clientId y tópicos de su Shadow |
| Logs | Histórico: siete días por plantilla; Alexa: retención existente de 14 días |

El código y configuración anteriores de Alexa se conservaron únicamente en `.local/deployment/alexa-before.zip` y `alexa-before-config.json`, ignorados. La plantilla y ZIP desplegados están en ese mismo directorio; se regeneran con `scripts/prepare_deployment.py`. No se modificaron certificados, WiFi ni `secrets.h`.

## Pruebas realizadas

| Comprobación | Resultado |
|---|---|
| Python | 43 tests, OK |
| Ruff | Sin incidencias |
| Firmware PlatformIO | SUCCESS; RAM 47 140 bytes, Flash 940 461 bytes; no cargado |
| Plantilla | cfn-lint sin incidencias y validate-template de AWS correcto |
| Lambda histórica, muestra válida | `stored`; fila confirmada mediante lectura consistente |
| Repetición del mismo ID | `duplicate` |
| Tipo inválido `presence=1` | `discarded`, motivo `presence` |
| Lambda Alexa, usuario sintético sin vínculo | Launch y ConsultarNivelIntent respondieron indicando cómo vincular |
| Shadow → regla → Lambda → DynamoDB | Éxito con Shadow sintético separado; lectura consistente positiva a 1.455 s desde el inicio de la petición, un ensayo |
| Limpieza | Eliminados Shadow y filas sintéticas; sin órdenes al actuador real |

La prueba completa usó la API del Shadow, no MQTT del ESP32. La latencia incluye solicitud y lectura de comprobación; no es latencia de voz, una media ni una garantía. Las invocaciones directas a Lambda no prueban el simulador ni la configuración remota del modelo de voz.

## Pendiente para funcionamiento físico completo

1. Confirmar montaje y puerto USB, cargar firmware y observar `schemaVersion=4` con timestamps nuevos en `thing`. En la lectura previa, el Shadow tenía versión 7677 y `sampledAt=1794353697`, sin `schemaVersion`; no demuestra que la placa esté conectada ahora.
2. Importar `alexa/interaction-model.es-ES.json`, compilar y probar en Alexa Developer Console. No se dispone de acceso autenticado a esa consola ni de ASK CLI configurado en esta sesión. AWS CLI no sustituye esa autenticación.
3. Ejecutar M01–M06 de [pruebas](../../docs/practica4/pruebas.md), incluyendo nivel bajo, modo/intervalo, dos usuarios, desconexión y métricas reales. No marcar estas pruebas como aprobadas a partir de datos sintéticos.

Para detener la ingesta, actualizar la pila con `EnableRule=false` siguiendo [configuración](../../docs/practica4/configuracion.md). Esto no detiene mensajes MQTT/Shadow ni elimina capacidad provisionada: desconectar la placa de AWS al terminar los ensayos. La tabla tiene política de retención al eliminar la pila; no eliminar la pila suponiendo que elimina todos los recursos.
