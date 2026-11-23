# Contratos de datos y Alexa

## Shadow clásico

`$aws/things/{thingName}/shadow`: el ESP32 publica `/update`, consulta `/get` y se suscribe a `/get/accepted`, `/get/rejected`, `/update/delta`, `/update/accepted` y `/update/rejected`. MQTT usa TLS en 8883 con certificado por dispositivo. Se conserva la política IoT de la Práctica 3: no se necesita un tópico nuevo.

| Campo | Tipo y dominio | Dirección / significado |
|---|---|---|
| `automatic` | boolean | desired/reported; false manual, true automático; valor inicial false, luego recuperado de NVS |
| `cooldownSeconds` | entero 5–86400 | desired/reported; inicial 300; mínimo entre inicios automáticos desde la última dosis, incluso si fue por voz |
| `activationId` | string 1–128 al solicitar, vacío antes de primera orden | desired/reported; identificador Alexa procesado, guardado antes de mover |
| `presence`, `pirReady` | boolean | reported; PIR observado y estabilización completada |
| `lowLevel`, `levelReady` | boolean | reported; salida filtrada interpretada y primera lectura disponible |
| `ledColor` | `off`, `green`, `orange` | reported; apagado solo antes de primera lectura; después deriva del nivel |
| `servoState` | `idle`, `pressing`, `returning` | reported; fase ordenada, no posición medida |
| `servoAngle` | entero 0 o 180 | reported; 180 durante pressing, 0 en otras fases |
| `cyclesSinceBoot` | entero unsigned 32 bits | reported; ciclos terminados desde este arranque |
| `uptimeSeconds` | entero unsigned | reported; derivado de millis; se reinicia al encender y al desbordar millis |
| `sampledAt` | entero Unix segundos, 0 sin reloj | reported; momento de captura, frescura Alexa máxima 180 s |
| `schemaVersion` | entero 4 | reported; permite separar la Práctica 4 |
| `messageId` | `p4-` + 24 hex + `-` + contador positivo | reported; aleatorio por arranque + secuencia, también `clientToken` de la publicación |
| `observedAtMs` | entero Unix milisegundos, 0 sin reloj | reported; instante de captura, estable en reintentos |
| `publishedAtMs` | entero Unix milisegundos | reported; primer intento de publicación; no se cambia en reintentos |
| `droppedRecords` | entero unsigned | reported; descartes por cola llena desde este arranque |
| `recordKind` | `reading`, `event` | reported; muestra o transición |
| `event` | objeto o null | reported; `actuator` servo/rgb, `from`, `to`, `origin` voz/edge. Null en lecturas elimina el evento anterior del Shadow |

La Lambda copia únicamente campos conocidos al histórico. `activationId` se usa para control, pero no se guarda en el histórico; basta el origen. [Ejemplo completo](../../infra/shadow-p4.example.json). `delta` contiene solo diferencias de `desired`; campos no admitidos se ignoran. Intervalos inválidos no se aplican ni se confirman: un operador debe corregir ese `desired`. El backend impide enviarlos por voz.

La versión de AWS (`version`) sirve para control de concurrencia y no sustituye `schemaVersion`. Alexa vuelve a consultar ante conflictos y reintenta hasta tres veces. Firmware no ejecuta comandos duplicados aunque se reentreguen al sincronizar. Las muestras históricas en cola pueden causar diferencias temporales hasta drenar; Alexa responde según la fecha de la muestra, nunca según la fecha de recepción del Shadow.

## Regla IoT y responsabilidades

SQL canónico en [history-rule.sql](../../infra/history-rule.sql):

```sql
SELECT state.reported AS reported, topic(3) AS thingName, timestamp() AS receivedAtMs
FROM '$aws/things/+/shadow/update/accepted'
WHERE state.reported.schemaVersion = 4
AND clientToken = state.reported.messageId
```

Versión SQL `2016-03-23`; acción `Lambda` hacia la función de almacenamiento. El Thing se obtiene del tópico autorizado, no del cuerpo enviado. El token evita registrar un `desired` de Alexa como si fuera telemetría. El wildcard permite más Things; la política de cada certificado debe limitar publicación a su propio nombre. No existe una segunda regla de control en nube porque las decisiones están en Edge.

| Función | Disparador | Accesos |
|---|---|---|
| Backend Alexa existente (`lambda_function.lambda_handler`) | Alexa Skills Kit, restringido a ID de skill | Get/Put/DeleteItem de vinculaciones; DescribeThing y Get/UpdateThingShadow de Things autorizados; logs |
| Almacenamiento (`index.lambda_handler` en CloudFormation inline) | Solo ARN de la regla y cuenta configurados | PutItem del histórico; escritura en su grupo de logs |

No hace falta un rol IAM adicional para esta acción Lambda de IoT: la política basada en recurso de Lambda permite `iot.amazonaws.com` con `SourceArn` y `SourceAccount`. La función no tiene permiso para modificar el Shadow. [Plantilla exportable](../../infra/practica4-stack.template.json).

## DynamoDB diseñado desde consultas

Vinculaciones conserva su tabla existente: PK `userId` string; `thingName` y `fechaVinculacion` string. Lectura consistente por usuario. La pertenencia a un Thing se limita a la lista IAM autorizada de la práctica; conocer su nombre no constituye un mecanismo de prueba de propiedad. Para un producto real se requeriría un código de emparejamiento.

Histórico usa una nueva tabla Standard provisionada, **1 RCU y 5 WCU**, sin autoscaling, GSI, LSI, streams, réplicas ni backups bajo demanda. PK `thingName` string; SK `recordKey` string = timestamp de observación rellenado a 13 dígitos + `#` + messageId. Registros con reloj desconocido comienzan con `0000000000000#` y se consultan aparte.

Cada fila contiene los campos de reported indicados, excepto activationId, además de `messageId`, `receivedAtMs`, `storedAtMs`, `storageLatencyMs` (números), `clockKnown` (boolean) y `expiresAt` (Unix segundos). `storedAtMs` se calcula al preparar PutItem; `storageLatencyMs` mide hasta ese punto, no hasta confirmación de la escritura. La validación de latencia real requiere una lectura consistente externa. `event` es un map en eventos. TTL: siete días desde preparación de almacenamiento; su eliminación es asíncrona, así que una consulta de reportes debe excluir expirados. La clave es estable aunque se reintente la invocación. La condición de escritura impide reemplazar la primera fila.

| Patrón | Query y cálculo | Decisión / mockup |
|---|---|---|
| Datos de un Thing entre dos instantes | PK exacta y SK BETWEEN `inicioMs#` y `finMs#~`; paginar con LastEvaluatedKey | Cronología de nivel y eventos |
| Última observación conocida del Thing | PK exacta, SK mayor a `0000000000000#~`, ScanIndexForward=false, revisar TTL y antigüedad | Reposición; mostrar sin datos si es antigua |
| Dosis finalizadas del día por origen | Query del intervalo; filtrar `event.actuator=servo`, `event.to=idle`; agrupar origin | Ajustar intervalo y revisar uso manual |
| Cambios a nivel bajo | Query del intervalo; `event.actuator=rgb`, `event.to=orange`; separar transición desde off (arranque) | Detectar necesidad de reposición |
| Auditoría de pruebas | Query del intervalo; comparar IDs y latencia con log serial de la misma ventana | Integridad y retrasos |
| Eventos capturados antes de sincronizar reloj | PK exacta y begins_with(SK, `0000000000000#`) | Auditoría aparte, sin fecha inventada |

Estos filtros se aplican sobre los registros consultados; no reducen las RCU consumidas. No se usa `Scan`. El volumen académico y la ventana corta justifican evitar índices adicionales. Si crece el histórico, evaluar un índice por tipo/día según nuevas consultas y costo.

## Skill es-ES

Invocación: **ambientador inteligente**. [Modelo JSON importable](../../alexa/interaction-model.es-ES.json).

| Intent | Slot | Frase de prueba |
|---|---|---|
| VincularIntent | thingName / THING_NAME | vincula mi ambientador con thing |
| DesvincularIntent | — | desvincula mi ambientador |
| ActivarIntent | — | activa el ambientador |
| ActivarAutomaticoIntent | — | activa el modo automático |
| DesactivarAutomaticoIntent | — | desactiva el modo automático |
| ConsultarSensorIntent | — | hay movimiento |
| ConsultarMotorIntent | — | cuál es el estado del motor |
| ConsultarAutomaticoIntent | — | cuál es el modo actual |
| ConsultarNivelIntent | — | cuál es el nivel de fragancia |
| ConsultarLedIntent | — | de qué color está el led |
| ConsultarIntervaloIntent | — | cuál es el intervalo |
| CambiarIntervaloIntent | segundos / AMAZON.NUMBER | cambia el intervalo a trescientos segundos |
| AMAZON.Help/Stop/Cancel/FallbackIntent | — | ayuda / salir / cancelar / frase no reconocida |

La consulta de nivel explica que es detección puntual y no porcentaje; el color no se cambia por voz porque debe representar el nivel. Modo e intervalo sí son configurables. Para registrar un nuevo Thing, ampliar los permisos IAM y los valores/sinónimos THING_NAME sin fijar el backend a un único usuario.

Referencia del protocolo: [flujo de Device Shadow, AWS](https://docs.aws.amazon.com/iot/latest/developerguide/device-shadow-data-flow.html).
