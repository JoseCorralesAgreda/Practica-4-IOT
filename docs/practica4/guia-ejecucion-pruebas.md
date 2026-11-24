# Guía de ejecución de pruebas — Práctica 4

Esta guía indica cómo ejecutar y documentar las pruebas del ambientador inteligente. Complementa el [plan de pruebas](pruebas.md). Las pruebas M01–M06 están documentadas satisfactoriamente en el informe final; las fotografías, exportaciones y los videos EV11–EV12 forman parte de las evidencias del repositorio. Los archivos sensibles se mantienen fuera de la documentación pública.

## 1. Preparación común

1. Revisar [configuración](configuracion.md) y el [circuito](circuito.svg) antes de energizar.
2. Confirmar GND común entre ESP32, PIR, SG90, XKC y RGB. Alimentar el servo con fuente regulada de 5 V; no usar GPIO ni 3V3 para él y no unir de forma directa los positivos USB/5 V externo.
3. Antes de conectar GPIO26, medir el OUT del XKC. Solo conectar si su salida es compatible con 3,3 V; el `INPUT_PULLUP` no adapta 5 V. Usar recipiente no metálico compatible; no perforar aerosol presurizado.
4. Mantener las resistencias de 330 Ω para cada ánodo RGB. El XKC usa el pull-up interno del ESP32, sin resistencia externa de señal.
5. Verificar que AWS siga dentro de la oferta aplicable y con margen suficiente. La regla habilitada y la placa conectada pueden generar consumo; una alerta no garantiza gasto cero.
6. Crear una carpeta de sesión, por ejemplo `evidencias/practica4/ejecucion-AAAA-MM-DD/`, con subcarpetas `logs`, `capturas`, `fotos`, `videos` y `mediciones`. No subir binarios ni archivos con secretos.
7. Anotar en una bitácora: fecha/hora UTC, commit, Thing anonimizado, versión de firmware, condiciones de WiFi, fuente usada y responsable de la prueba.

### Cargar y observar el firmware

No sobrescriba `firmware/include/secrets.h`. Tras confirmar montaje y puerto:

```powershell
./.venv/Scripts/python.exe -m platformio device list
./.venv/Scripts/python.exe -m platformio run -d firmware -t upload
./.venv/Scripts/python.exe -m platformio device monitor -d firmware
```

Conservar el monitor serial como archivo de evidencia. Debe aparecer el arranque, la estabilización PIR y, después de conectarse, `PUBLISH id=...` y `SHADOW_ACK id=...`. El firmware publica `schemaVersion=4`; confirme en el Shadow que las marcas de tiempo son nuevas antes de comenzar pruebas.

## 2. Estados permitidos

| Estado | Cuándo usarlo |
| --- | --- |
| APROBADO | Se cumplieron todos los criterios y existe evidencia verificable. |
| FALLIDO | Se ejecutó y algún criterio no se cumplió. |
| PARCIAL | Solo se ejecutó una parte del escenario o faltó una medición requerida. |
| BLOQUEADO | Un impedimento concreto evitó la prueba; indicar cuál. |
| NO EJECUTADO | Aún no se inició. |

Una captura aislada, una invocación directa de Lambda o una compilación no sustituyen una prueba integrada de hardware/Alexa.

## 3. M01 — Montaje, nivel y PIR

**Objetivo:** validar conexiones, estado RGB, filtro de nivel y detección PIR.

1. Con el mecanismo desacoplado, encender la placa y esperar 60 s de calentamiento del PIR.
2. Registrar foto del montaje, fuente y conexiones antes de manipular líquido.
3. Colocar líquido a la altura del sensor y esperar al menos 1,2 s. Registrar color y serial.
4. Retirar el líquido de esa altura, esperar 1,2 s y registrar que RGB sea rojo. Repetir cinco veces en cada sentido.
5. Con el sensor en condición estable, provocar cinco flancos PIR separados; registrar `GPIO27`, `pirReady` y `presence`.
6. Aplicar pulsos de nivel menores de 500 ms, si puede hacerlo sin riesgo, y verificar que no haya oscilación del RGB.

**Aprobar si:** cinco cambios bajo/suficiente y cinco retornos son correctos, rojo/verde son observables, no se publican porcentajes ficticios y el PIR se estabiliza. Guardar `EV-M01-foto`, `EV-M01-video` y `EV-M01-serial`.

## 4. M02 — Alexa y aislamiento de usuarios

**Objetivo:** comprobar la skill, vínculo persistente y separación usuario/Thing.

1. Importar `alexa/interaction-model.es-ES.json` en la consola Alexa, guardar y compilar. Activar el modo Development.
2. Con usuario A, vincular Thing A. Si se dispone de segundo usuario/Thing, vincular B→B.
3. Ejecutar consultas de PIR, nivel, LED, motor, modo e intervalo.
4. Solicitar una dosis, esperando la confirmación física posterior en la placa; Alexa solo confirma envío de la orden.
5. Cambiar vínculo, probar nombre inexistente, desvincular y abrir una nueva sesión.
6. Verificar que una solicitud de A no modifica Thing B. Si solo hay un dispositivo/usuario, registrar el escenario como PARCIAL, no como aislamiento validado.

**Evidencia:** capturas del simulador sin identificadores sensibles, Shadow antes/después y filas de vínculo anonimizadas. Guardar `EV-M02-*`.

## 5. M03 — Automático, prioridad y persistencia

**Objetivo:** probar reglas Edge y convivencia con voz.

1. Activar automático y establecer intervalo de 5 s para la prueba; esperar que `reported` lo confirme.
2. Provocar un flanco PIR antes y después del intervalo. Mantener PIR alto: no debe producir ciclos adicionales sin un nuevo flanco.
3. Solicitar cambio a 300 s, consultar, restaurar a 5 s y reiniciar la placa. Confirmar persistencia de modo e intervalo.
4. Con LED rojo por nivel bajo, provocar una dosis por PIR y una por voz. Ambas deben permitirse si el motor está libre.
5. Desactivar automático durante un ciclo: el ciclo iniciado termina, pero no se inicia otro por PIR.
6. Probar intervalos 4 y 86401; deben rechazarse por la skill/controlador.

**Evidencia:** video con reloj, serial y eventos almacenados con `origin=edge`/`origin=voz`. Medir cada fase del servo; objetivo 700 ms por fase con +100 ms de tolerancia.

## 6. M04 — Histórico, integridad y latencia

**Objetivo:** verificar almacenamiento real durante 15 min conectados.

1. Asegurar cola vacía, reloj sincronizado y WiFi estable. Iniciar captura serial.
2. Durante 15 min realizar cinco dosis por voz, cinco por PIR y alternar el nivel. Evitar atomizar innecesariamente: se puede desacoplar el mecanismo y etiquetar ciclos de prueba.
3. Ejecutar `observe_storage.py` antes de cinco eventos separados para medir visibilidad. La herramienta consulta como máximo 20 veces, cada 500 ms.
4. Exportar el rango completo de DynamoDB con `Query` consistente; no usar `Scan` ni una página incompleta.
5. Ejecutar `analyze_evidence.py` con el serial y JSON exportado.
6. Para negativo, reenviar únicamente mediante prueba Lambda una muestra válida con mismo ID y otra inválida (`presence=1`). No usar estas muestras ficticias como evidencia del funcionamiento físico.

```powershell
./.venv/Scripts/python.exe scripts/observe_storage.py --table NOMBRE_TABLA --thing THING
aws dynamodb query --table-name NOMBRE_TABLA --key-condition-expression 'thingName = :thing AND recordKey BETWEEN :start AND :end' --expression-attribute-values file://.local/query-values.json --consistent-read --region us-east-2 --output json > .local/history.json
./.venv/Scripts/python.exe scripts/analyze_evidence.py .local/history.json --serial .local/serial.txt
```

**Cálculo de integridad:** `100 × |IDs únicos publicados ∩ IDs almacenados| / |IDs únicos publicados|`. Para latencia guardar los cinco valores individuales, mínimo, máximo, media, mediana, desviación y p95. `storedAtMs` es anterior a `PutItem`; la primera lectura consistente es la evidencia de visibilidad.

## 7. M05 — Desconexión y recuperación

**Objetivo:** demostrar qué sigue funcionando sin red y qué se recupera después.

1. Con automático activo, retirar WiFi durante 60 s sin apagar la placa.
2. Generar un flanco PIR y un cambio de nivel. Verificar servo/RGB y guardar serial.
3. Enviar una orden `desired` pendiente desde Alexa, si la conectividad externa aún permite hacerlo.
4. Restaurar WiFi y medir hasta que se recupere `desired`, se drene cola y aparezcan ACK.
5. Reiniciar la placa y comprobar modo/intervalo persistidos y que no se repita un `activationId` ya consumido.
6. Repetir con WiFi activo pero broker inaccesible; registrar el máximo retraso del loop por reconexión TLS.

**Aprobar si:** reglas locales siguen operando, `desired` se recupera en ≤30 s, no se repite activación y pérdidas de RAM tras reinicio se declaran. La cola limitada no confirma que DynamoDB haya guardado todo.

## 8. M06 — Reportes, secretos y costo

**Objetivo:** cerrar evidencia de uso responsable y reportes.

1. Obtener un día o ventana declarada de datos reales de un Thing.
2. Revisar mockups: ciclos por origen y avisos deben derivar de registros, no de valores inventados.
3. Ejecutar revisión de Git para evitar secretos, certificados, `.pio`, ZIP y `.local` rastreados.
4. Consultar plan/cupo antes y después de la sesión y guardar salida sanitizada.
5. Si no puede demostrarse oferta/margen aplicable, detener tráfico y registrar M06 como BLOQUEADO.

## 9. Plantilla de registro

Copiar esta tabla por cada prueba en el informe o en un archivo de evidencias:

| Campo | Registro |
| --- | --- |
| ID y título | M0X — ... |
| Fecha/hora UTC y responsable | |
| Commit / firmware / Thing anonimizado | |
| Precondiciones y red | |
| Datos y pasos ejecutados | |
| Resultado esperado | |
| Resultado obtenido, valores individuales y unidades | |
| Evidencia interna | `EV-M0X-...` |
| Estado | APROBADO / FALLIDO / PARCIAL / BLOQUEADO / NO EJECUTADO |
| Incidencias y siguiente acción | |

Al terminar, actualizar [informe.md](informe.md), [pruebas.md](pruebas.md) y el índice de evidencias; no reescribir resultados históricos de P3 ni cambiar un estado a APROBADO sin su artefacto verificable.
