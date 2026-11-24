# Montaje y configuración

## Hardware

Conservar ESP32 DOIT DEVKIT V1, PIR HC-SR501 en GPIO27 y servo SG90 en GPIO18. Añadir sensor XKC-Y23A-NPN en GPIO26 y RGB de cátodo común en GPIO21 (R), GPIO22 (G), GPIO23 (B). Pines propuestos disponibles según el firmware heredado; comprobar el montaje real antes de energizar.

| Elemento | Conexión |
|---|---|
| ESP32 | USB; GND común con la fuente de sensores y servo |
| SG90 | Señal GPIO18; alimentación regulada 5 V independiente de 3V3, con corriente suficiente para el mecanismo |
| HC-SR501 | VCC 5 V, GND común, OUT GPIO27; verificar salida compatible con 3.3 V |
| XKC-Y23A-NPN | VCC 5 V y GND según identificación del ejemplar; salida NPN de colector abierto directamente al GPIO26, configurado como `INPUT_PULLUP`; sin resistencia externa de señal |
| RGB | Cátodo común a GND; cada ánodo a su GPIO mediante su propia resistencia de 330 Ω |

No unir 5 V externos con 5 V USB sin un circuito de alimentación adecuado. No conectar una señal de 5 V al GPIO. Medir primero el nodo de salida del sensor: LOW al detectar líquido y HIGH al no detectarlo es la polaridad configurada; si el ejemplar está invertido, ajustar `kLiquidDetected` en `LevelIndicator.cpp` y repetir la prueba. Si hay un pull-up interno a 5 V, adaptar el nivel eléctrico antes de conectar.

La [ficha del fabricante](https://www.xkc-sensor.com/detail/1433.html) identifica la variante NPN, detección a través de recipientes no metálicos y respuesta nominal de 500 ms. El montaje propuesto usa 5 V para la alimentación del sensor y el pull-up interno del ESP32 hacia 3.3 V, habilitado por `pinMode(kLevelPin, INPUT_PULLUP)`. No montar la resistencia externa de 10 kΩ ni un puente de OUT a 3V3. Las tres resistencias de 330 Ω del RGB sí se mantienen. No asumir colores de cables; comprobar el diagrama entregado con el ejemplar para identificar VCC, GND y salida.

Espressif documenta un pull-up interno de aproximadamente 45 kΩ ([GPIO Arduino-ESP32](https://docs.espressif.com/projects/arduino-esp32/en/latest/api/gpio.html)). Es una polarización de entrada, no un adaptador de 5 V a 3.3 V. Su activación ocurre en `begin()`; no asumir señal definida durante reset. Usar cable de señal corto y comprobar estabilidad con el servo funcionando. Con sensor desconectado, HIGH se interpreta como nivel bajo después del filtro de 500 ms: no se diagnostica desconexión. La estabilidad con este montaje sigue pendiente de M01/M03/M05.

Fijar el sensor externamente a la altura mínima deseada en un recipiente no metálico; probar con la fragancia real. Este umbral es **físico**, no un número de porcentaje que pueda cambiarse por voz. El parámetro de negocio configurable por voz es el intervalo de dosificación. Ensayar vacío/lleno y ajustar sensibilidad según el manual. No puede medir a través de la lata metálica de un aerosol.

El PWM usa rojo 255, verde 0 y azul 0 para nivel bajo; rojo 0, verde 255 y azul 0 para nivel suficiente. Durante el arranque queda apagado hasta estabilizar la primera lectura.

## Entorno local y carga

Ejecutar los comandos de [README](../../README.md). No reemplazar `secrets.h` si ya existe. La plantilla heredada contiene las constantes WiFi, endpoint, Thing y certificados; ninguna credencial nueva se necesita para el sensor.

Para cargar, una vez verificado el montaje y el puerto de la placa:

```powershell
./.venv/Scripts/python.exe -m platformio device list
./.venv/Scripts/python.exe -m platformio run -d firmware -t upload
./.venv/Scripts/python.exe -m platformio device monitor -d firmware
```

Estas acciones no se han ejecutado: la sesión solo compiló. El monitor registra IDs, fases y GPIO; no imprime secretos. Los binarios incluyen credenciales y deben permanecer fuera de Git.

## AWS: preparación y condición previa

El 23 de noviembre de 2026 se confirmó por STS la cuenta `679937333206` y se verificaron en `us-east-2` la función `Alexa`, la tabla `AmbientadorVinculaciones` y el Thing `thing`. La sesión local se obtuvo con `aws login`; en el entorno del asistente las consultas requieren ejecución elevada para acceder a esa sesión. No copiar sus credenciales al repositorio. Para usar esta sesión desde boto3, instalar las dependencias de desarrollo, incluido `botocore[crt]`.

La pila `ambientador-p4` está desplegada y la regla `ambientador_p4_history` está habilitada. Su función es `ambientador-p4-storage` y la tabla es `ambientador-p4-HistoryTable-YBDZ42IAGZOK`. La Lambda `Alexa` se actualizó conservando configuración, rol y disparador restringido a la skill; el ZIP anterior y su configuración quedaron en `.local/deployment/`, ignorado por Git. No se alteraron los vínculos existentes, el certificado ni `secrets.h`.

Se comprobó el recorrido Shadow → regla → Lambda → DynamoDB con un Shadow sintético separado, eliminado al terminar junto con su fila. Esto no demuestra conexión MQTT de la placa: el Shadow de `thing` consultado todavía tenía el esquema anterior, sin `schemaVersion`. Cargar el firmware requiere confirmar montaje y placa; importar el modelo es-ES requiere acceso a Alexa Developer Console. Ver [registro de integración](../../evidencias/practica4/aws-integracion-2026-11-23.md).

Con sesión AWS válida, comprobar identidad, estado del plan y consumo:

```powershell
aws sts get-caller-identity --query Account --output text
aws freetier get-account-plan-state --region us-east-1
aws freetier get-free-tier-usage --region us-east-1
aws lambda get-function-configuration --function-name Alexa --region us-east-2 --query '{Runtime:Runtime,Handler:Handler,Role:Role,State:State}'
aws dynamodb describe-table --table-name AmbientadorVinculaciones --region us-east-2 --query 'Table.{Status:TableStatus,Billing:BillingModeSummary,Capacity:ProvisionedThroughput}'
```

No imprimir todas las variables de entorno de Lambda. Si no puede comprobarse una oferta activa y margen suficiente, no desplegar ni habilitar tráfico; ver [costos](costos-seguridad.md). Comprobar también otras tablas/regiones y recursos compartidos que consumen el cupo.

## Despliegue reproducible cuando se haya verificado la gratuidad

`prepare_deployment.py` genera `.local/deployment/practica4-stack.json` con el código real de `storage_function.py` insertado inline y `.local/deployment/alexa.zip` que contiene solo `lambda_function.py`. No requiere S3, imágenes Docker ni certificados. Regenerar después de cada cambio.

```powershell
./.venv/Scripts/python.exe scripts/prepare_deployment.py
aws cloudformation validate-template --template-body file://.local/deployment/practica4-stack.json --region us-east-2
aws cloudformation deploy --template-file .local/deployment/practica4-stack.json --stack-name ambientador-p4 --capabilities CAPABILITY_IAM --parameter-overrides EnableRule=false --region us-east-2
aws cloudformation describe-stacks --stack-name ambientador-p4 --region us-east-2 --query 'Stacks[0].Outputs'
```

La creación ya provisiona capacidad de DynamoDB aunque la regla esté desactivada: verificar el margen gratuito **antes de crear**. La plantilla conserva la tabla si se elimina la pila para evitar pérdida accidental; una tabla retenida continúa provisionando capacidad. Identificarla y decidir explícitamente su retirada al terminar la práctica.

La nueva Lambda utiliza Python 3.13, memoria 128 MB, timeout 10 s, logs con retención siete días y reintentos asíncronos limitados a dos, durante una hora como máximo. `HISTORY_TABLE` se configura automáticamente. No tiene acceso al Shadow. La Lambda `Alexa` conserva su retención existente de 14 días. [Runtimes admitidos por AWS](https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtimes.html).

Para actualizar Alexa, conservar la configuración actual, el disparador restringido a su skill y las variables `IOT_REGION`, `IOT_DATA_ENDPOINT`, `BINDINGS_TABLE`, `ALEXA_SKILL_ID`. Obtener su `RevisionId` y usarlo para evitar sobrescribir un cambio concurrente. Revisar que su runtime esté soportado y el handler sea `lambda_function.lambda_handler`:

```powershell
$alexaRevision = aws lambda get-function-configuration --function-name Alexa --region us-east-2 --query RevisionId --output text
aws lambda update-function-code --function-name Alexa --zip-file fileb://.local/deployment/alexa.zip --revision-id $alexaRevision --region us-east-2 --query '{State:State,LastUpdateStatus:LastUpdateStatus}'
aws lambda wait function-updated --function-name Alexa --region us-east-2
```

Después de validar almacenamiento con una muestra y confirmar nuevamente consumo/eligibilidad, habilitar la regla actualizando la pila con el mismo comando `deploy` y `EnableRule=true`. No usar ambas versiones del firmware en el mismo Thing simultáneamente. La política IoT existente sigue sirviendo; la Lambda Alexa tampoco necesita permiso de histórico. Los roles y tablas se exportan en `infra/`; la plantilla nueva no reemplaza los recursos existentes.

## Alexa Developer Console

En la skill existente, locale es-ES, importar [interaction-model.es-ES.json](../../alexa/interaction-model.es-ES.json) en JSON Editor, guardar y compilar el modelo. Mantener nombre de invocación y endpoint Lambda autorizado. En Test activar Development y ejecutar las frases de [contratos](contratos.md). La importación y el simulador no se realizaron en esta sesión.

## Obtener evidencia con Query

Guardar en `.local/query-values.json` valores como los siguientes, sustituyendo Thing y extremos Unix en milisegundos por los de la ventana real:

```json
{":thing":{"S":"thing"},":start":{"S":"1800000000000#"},":end":{"S":"1800000900000#~"}}
```

```powershell
aws dynamodb query --table-name NOMBRE_TABLA_DE_LA_PILA --key-condition-expression 'thingName = :thing AND recordKey BETWEEN :start AND :end' --expression-attribute-values file://.local/query-values.json --consistent-read --region us-east-2 --output json > .local/history.json
./.venv/Scripts/python.exe scripts/analyze_evidence.py .local/history.json --serial .local/serial.txt
```

El CLI pagina automáticamente salvo que se cambien sus opciones. No confundir una página limitada con el resultado completo. Un filtro TTL debe aplicarse para reportes de uso; para auditoría de una ventana reciente conservar todas las filas relevantes. Sanitizar capturas y exportaciones antes de incorporarlas a `evidencias/practica4/`.

## Intervalo de depuración y actualización de color

El intervalo automático inicial y de recuperación ante un valor inválido es 5 s, medido entre inicios de dosis con `millis()`; no se añade una espera bloqueante. Requiere un nuevo flanco PIR, modo automático y motor libre. La voz conserva su prioridad y puede saltar ese intervalo. El calentamiento PIR sigue siendo 60 s.

La configuración válida persistida en NVS y `desired.cooldownSeconds` conservan prioridad. En una placa ya configurada, solicitar «cambia el intervalo a cinco segundos» y consultar hasta confirmar `reported.cooldownSeconds=5`. No borrar NVS para cambiarlo.

El contrato vigente usa `red` para nivel bajo. Actualizar conjuntamente firmware y Lambdas Alexa/almacenamiento antes de la prueba integrada: la versión anterior del almacenamiento no admite `red`. Los registros históricos se conservan con su color original. Los cambios locales no actualizan la placa ni AWS; verificar elegibilidad y consumo gratuitos antes de desplegar.
