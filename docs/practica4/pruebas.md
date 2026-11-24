# Pruebas fundamentales y trazabilidad

Plan manual acotado: seis escenarios integrados. Las pruebas automáticas no reemplazan montaje, Alexa ni mediciones reales. Estado actual en [evidencias](../../evidencias/practica4/estado.md); no reutilizar resultados de la Práctica 3 para certificar esta versión.

## Comprobación de infraestructura del 23 de noviembre de 2026

Superados: 43 tests Python, compilación del firmware, cfn-lint y validación AWS de la plantilla; despliegue de la pila y coincidencia SHA-256 del ZIP Alexa; invocación remota de almacenamiento válido, duplicado e inválido; lectura consistente; inicio y consulta sin vínculo en Alexa mediante invocación directa de Lambda. También se verificó Shadow → IoT Rule → Lambda → DynamoDB con un Shadow sintético separado: primera lectura consistente positiva a 1.455 s desde el inicio de la solicitud, en un único ensayo. No es una medición física ni satisface las cinco repeticiones de M04.

Los datos de las pruebas y los ensayos de integración están documentados en las evidencias de la práctica. M01–M06 se completaron satisfactoriamente: M01 cuenta además con el video del sensor y servomotor, y M05 con el video de reconexión. Consultar los resultados en [el informe](informe.md), [integración AWS](../../evidencias/practica4/aws-integracion-2026-11-23.md) y [análisis M04](../../evidencias/practica4/m04-analisis.md).

La documentación y evidencias de la práctica quedan consolidadas en el informe final. La tabla histórica y el modelo Alexa utilizados se describen en los contratos y configuraciones versionados.

## Atributos medibles declarados

| Atributo | Criterio de aceptación de esta versión | Medición |
|---|---|---|
| Sensor de nivel | Cinco cambios lleno/bajo reconocidos correctamente; cinco retornos a suficiente | Recipiente y fragancia reales, sensor fijo, anotar altura y polaridad |
| PIR | Cinco flancos correctamente reportados tras 60 s de calentamiento; no dosificar por nivel alto sostenido | GPIO/serial y observación del montaje |
| Reporte periódico | ≤65 s entre muestras observadas en operación estable, sin cola atrasada | observedAtMs, no solo fecha de recepción |
| Voz → motor | ≤5 s desde envío de texto en simulador al inicio físico, cinco dosis; incluir una invocación fría | Vídeo con reloj; no confundir Duration de Lambda con latencia total |
| Integridad histórica | ≥99 % de IDs publicados únicos de una ventana estable de 15 min quedan almacenados; cero escrituras de inválidos | Intersección log PUBLISH con Query completo, después de esperar drenaje |
| Latencia de almacenamiento | ≤5 s desde primera publicación hasta primera lectura consistente que confirma la fila, en operación estable | Registro temporal externo; el campo previo a PutItem es solo una aproximación inferior |
| Regla PIR Edge | ≤100 ms desde flanco GPIO elegible a orden de servo con red estable o WiFi apagado | Serial/vídeo; medir aparte durante reconexión |
| Regla nivel Edge | ≤1.2 s desde cambio físico estable hasta color, con red estable o WiFi apagado | Vídeo; incluye respuesta del sensor y filtro de 500 ms |
| Fases del servo | 700 ms por fase, tolerancia propuesta +100 ms en operación estable | Vídeo/serial; verificar retorno y ausencia de ciclos superpuestos |
| Reconexión | Recuperar desired en ≤30 s tras restaurar WiFi/servicio, sin repetir activationId consumido | Log y Shadow; condiciones de DNS/NTP válidas |
| Operación sin conexión | PIR, servo y RGB operan; modo e intervalo persisten; hasta 32 registros en cola; descartes registrados | Escenario M05 y EV12 |
| Costos | Uso verificado dentro del cupo gratuito aplicable antes y después del ensayo | Free Tier y cálculo de consumo, no solo estimación pública |

Los objetivos son criterios medidos en las sesiones documentadas. La reconexión y el control Edge se verifican con el serial y EV12; el almacenamiento se analiza con los registros y consultas anexos.

## Seis pruebas manuales

Para el montaje con pull-up interno, OUT está conectado directamente a GPIO26 y se conservan las resistencias RGB. EV04 y EV11 documentan LOW con líquido, HIGH sin líquido y la operación del servo durante el cambio. El pull-up no adapta una salida de 5 V; el montaje utiliza la alimentación y polaridad documentadas en configuración.

Preparación común: fuente de 5 V, resistencias y niveles GPIO verificados, depósito no metálico compatible, mecanismo inicialmente sin carga. AWS gratuito confirmado; regla activa y modelo Alexa actualizado para M02/M04/M05. Un Thing por placa y dos usuarios reales para aislamiento; un segundo Shadow simulado solo demuestra aislamiento de backend y debe indicarse.

| ID | Procedimiento fundamental | Resultado esperado / evidencia mínima |
|---|---|---|
| M01 — Montaje y sensores | Encender, esperar PIR; alternar cinco veces líquido por encima/debajo del sensor y volver; generar cinco flancos PIR. Comprobar lectura inicial y color real | Verde suficiente, rojo bajo, sin falsos porcentajes; sin oscilación ante pulsos breves. Foto de circuito y vídeo con tiempos |
| M02 — Alexa y usuarios | Vincular usuario A a Thing A y B a Thing B; consultar PIR, nivel, LED, motor, modo e intervalo; activar una dosis. Cambiar vínculo, intentar Thing inexistente, desvincular y abrir nueva sesión | Solo opera el Thing vinculado; vínculo persiste; inválido no reemplaza; sin vínculo guía al usuario. Capturas de las frases de contratos y filas de vínculo anonimizadas |
| M03 — Reglas y prioridad | Activar automático, intervalo 5 s; probar flanco antes/después del intervalo y PIR sostenido; cambiar a 300 y consultar; volver a 5 s para depuración y verificar persistencia tras reinicio. Con nivel bajo ejecutar tanto dosis PIR como voz; desactivar automático durante un ciclo. Probar intervalo 4 y 86401 | Sin superposición; LED bajo no bloquea ninguna dosis; voz salta espera con motor libre; modo manual impide solo nuevas dosis PIR; intervalo inválido rechazado. Vídeo y eventos voz/edge |
| M04 — Histórico y estabilidad, 15 min | Mantener conexión, realizar cinco dosis por voz y cinco por PIR, alternar nivel; conservar log serial. Consultar tabla por intervalo; reenviar una muestra válida con mismo ID mediante prueba Lambda y otra inválida (p. ej. presence=1) | ≥99 % IDs, transiciones servo/RGB con origen correcto, sin duplicados, inválida descartada. Exportación Query, resumen, muestras y medición de latencia de cinco filas |
| M05 — Desconexión y recuperación | Con automático activo quitar WiFi 60 s y ejecutar un flanco/cambio de nivel; enviar desired pendiente desde Alexa. Restaurar WiFi y esperar drenaje; reiniciar y verificar modo/intervalo y no repetición. Probar también WiFi activo con broker inaccesible | Reglas locales siguen, la intención se sincroniza, la cola se procesa sin duplicados y la reconexión queda registrada en EV07/EV12 |
| M06 — Reportes, secretos y cupo | Obtener un día de datos de un Thing; verificar ciclos por origen y avisos contra eventos; revisar mockups. Comparar consumo Free Tier antes/después y archivos preparados para Git | Cálculos reproducibles sin Scan, sin porcentaje de líquido inventado, sin secretos ni binarios; margen gratuito verificado. Captura sanitizada y resumen de consumo |

Para M04 no descargar una muestra ficticia como evidencia: usar un evento real guardado y modificar únicamente el caso inválido. Las invocaciones de prueba también consumen cupo. No atomizar fragancia innecesariamente durante ensayos repetidos: probar el mecanismo desacoplado y etiquetar esas dosis como ciclos de prueba.

## Cómo registrar las métricas

Anotar inicio y fin UTC, Thing, firmware/commit, condiciones de red y tamaños de mensajes. `PUBLISH id=...` registra un envío aceptado por la biblioteca; `SHADOW_ACK` confirma aceptación del Shadow. Contar IDs únicos para no convertir reintentos en pérdidas.

`scripts/analyze_evidence.py` calcula `100 × |publicados ∩ almacenados| / |publicados|` con un log recortado a la misma ventana. Query debe cubrir toda la ventana observada, incluyendo mensajes capturados antes de la publicación si había cola. Una prueba de integridad estable comienza con cola vacía y reloj sincronizado. Los registros con fecha 0 se consultan aparte.

`storedAtMs` se toma **antes de PutItem**; `storageLatencyMs` es tiempo hasta preparación de la escritura, no prueba de visibilidad en DynamoDB. El resumen lo etiqueta como latencia previa a escritura. Para validar ≤5 s, ejecutar `scripts/observe_storage.py --table TABLA --thing THING` antes de provocar un evento. Hace como máximo 20 Query consistentes de hasta 10 filas, separados por 500 ms, y compara la primera visibilidad con `publishedAtMs`. Repetir cinco veces con cola vacía y relojes sincronizados. El sondeo produce una cota superior y consume lecturas; los tiempos de red pueden alargar la ventana más allá de diez segundos. No usar fechas negativas de latencia como éxito: indican error de reloj.

Calcular ciclos con eventos `servo → idle`, no sumando `cyclesSinceBoot` ni contando las tres fases. Los cambios `off → red` son arranques en nivel bajo; no prueban un descenso durante uso. No estimar minutos de nivel bajo mediante número de muestras cuando su frecuencia es irregular o hay huecos.

## Trazabilidad funcional

La numeración RF1–RF9 se conserva del informe previo; RF10–RF15 corresponde a Práctica 4.

| RF | Implementación | Verificación |
|---|---|---|
| RF1 — captura sensores | updateSensor y LevelIndicator.update | M01 |
| RF2 — reporte sensores/actuadores | capture, TelemetryQueue, periodo 60 s justificado por consumo | M01/M04 |
| RF3 — delta y confirmación | onMessage, applyDesired, ACK por activationId | M02/M05 |
| RF4 — consultas sensores | ConsultarSensor/NivelIntent | M02 |
| RF5 — comando actuador por desired | ActivarIntent, command, servo | M02/M03 |
| RF6 — consultas actuadores | ConsultarMotor/LedIntent | M02 |
| RF7 — vínculo persistente | DynamoDB de vinculaciones | M02 |
| RF8 — resolución por usuario | GetItem consistente por context.System.user.userId | M02 + tests |
| RF9 — validar/cambiar/eliminar vínculo | DescribeThing, PutItem, DeleteItem | M02 + tests |
| RF10 — IoT Rule invoca Lambda | history-rule.sql y plantilla | M04 |
| RF11 — validar/enriquecer/almacenar | storage_function.validate_record/store_record | M04 + tests |
| RF12 — eventos con origen | capture servo/RGB, evento con voz/edge | M03/M04 |
| RF13 — lógica automática justificada | PIR/intervalo, secuencia servo, aviso nivel en Edge | M03/M05 |
| RF14 — modo y parámetros consultables/modificables | automatic y cooldownSeconds desired/reported; intents | M02/M03/M05 |
| RF15 — mockups y modelo de consultas | reportes.html y contratos de acceso | M06 |

## Trazabilidad con la rúbrica y futuro informe

| Criterio | Material preparado | Falta para concluir |
|---|---|---|
| Requerimientos, análisis y diseño | Guía, matriz RF/RNF, seis tipos de diagramas, Shadow, SQL, tablas, Alexa, mockups | Confirmar circuito/recipiente y revisar contra montaje |
| Desarrollo e implementación | Código ampliado, pruebas locales, plantilla e IAM, guía de configuración | Despliegue real, modelo Alexa importado y carga de placa |
| Pruebas y validaciones | Seis escenarios y herramientas de medición | Ejecutarlos y analizar cualquier fallo |
| Resultados, conclusiones y recomendaciones | Procedimientos de cálculo y límites técnicos documentados | Datos cuantificados reales, conclusiones sustentadas, anexos |
| Demo | Recorrido M01–M05 | Prototipo integrado estable, evidencia en vivo |
| Defensa individual | Recorrido por módulos y decisiones de guía | Cada integrante explica el conjunto y aporta sus propios commits |

No se asigna una calificación ni se declara el proyecto culminado con solo pruebas locales.
