# Guía de estudio de la Práctica 4

Este material explica la implementación y prepara la información del futuro informe. No presenta pruebas físicas pendientes como resultados. La consigna es [Práctica_4.md](../../Práctica_4.md); las reglas de colaboración están en [AGENTS.md](../../AGENTS.md).

## Caso de uso y ampliación

Un ambiente interior se aromatiza mediante pulsaciones mecánicas del atomizador. El PIR indica cambios de movimiento, el SG90 pulsa el mecanismo y el usuario también puede ordenar una dosis con Alexa. El nuevo sensor detecta si hay líquido a la altura de montaje; el RGB permite reconocer localmente que es necesario reponer fragancia.

Se usan dos sensores porque responden preguntas distintas: cuándo hay movimiento y cuándo falta líquido. El servo ejecuta la acción útil y el RGB comunica el nivel sin abrir una aplicación. No se agrega un ultrasónico ni se interpreta una salida binaria como porcentaje. La arquitectura conserva Shadow y vinculación multiusuario, y amplía su esquema con versión 4.

El XKC-Y23A-NPN confirmado reemplaza la referencia inicial al XKC-Y25. Requiere pared no metálica y validación con la fragancia real. Si el consumible es una lata metálica, debe adaptarse el depósito/mecanismo a un recipiente compatible antes de afirmar que el prototipo mide su nivel. No modificar ni perforar un aerosol presurizado. No se han verificado el recipiente ni la calibración en esta sesión.

## Reglas implementadas

| Regla | Dónde y por qué | Convivencia con voz |
|---|---|---|
| Un nuevo flanco PIR activa un ciclo si `automatic=true`, el motor está libre y pasó `cooldownSeconds` desde el inicio de la última dosis | Edge: datos locales, respuesta inmediata y operación sin Internet | La voz puede dosificar en cualquier modo con motor libre; cada dosis reinicia la espera automática |
| Nivel estable durante 500 ms: rojo si falta líquido, verde si hay líquido | Edge: aviso local independiente de red; evita cambios por fluctuaciones breves | No hay comando de color; el LED siempre deriva del sensor. El nivel bajo no bloquea ninguna dosis |
| Presionar 700 ms y retornar 700 ms | Edge: secuencia mecánica sin `delay` por fase | Nunca se superponen ciclos; apagar automático deja terminar el actual |
| Validar y almacenar lecturas/eventos | Lambda de almacenamiento: responsabilidad persistente, permisos `PutItem` | No controla actuadores ni escribe `desired` |

No se necesita una regla de negocio en la nube: ninguna decisión depende del histórico ni de otros objetos. RF13 permite Edge, nube o ambos. Crear una segunda Lambda de control añadiría mensajes, permisos y conflictos sin resolver una necesidad de este caso.

El arbitraje es por orden de procesamiento: un flanco local puede iniciar antes de recibir un comando de voz. Si el dispositivo está ocupado, el comando nuevo queda en `desired` y se consulta al terminar. La skill rechaza normalmente una nueva solicitud cuando el Shadow ya informa un ciclo o un identificador pendiente. Shadow admite **una orden pendiente**, no una cola general de comandos.

## Recorrido del código

| Archivo | Responsabilidad y lectura recomendada |
|---|---|
| [main.cpp](../../firmware/src/main.cpp) | Instancia el objeto; delega `setup` y `loop` |
| [Ambientador.h](../../firmware/include/Ambientador.h), [Ambientador.cpp](../../firmware/src/Ambientador.cpp) | Coordina PIR, secuencia servo, configuración NVS y comunicación Shadow. Estudiar `tick`, `applyDesired`, `updateSensor`, `updateServo`, `capture` |
| [LevelIndicator.cpp](../../firmware/src/LevelIndicator.cpp) | Lee GPIO26 con `INPUT_PULLUP` interno, sin resistencia externa de señal; estabiliza por tiempo y aplica PWM RGB. `update` devuelve true solo al cambiar el estado filtrado |
| [TelemetryQueue.cpp](../../firmware/src/TelemetryQueue.cpp) | Conserva hasta 32 snapshots, asigna `messageId`, reintenta y retira únicamente el mensaje cuyo `clientToken` fue aceptado |
| [lambda_function.py](../../backend/lambda_function.py) | Backend Alexa heredado y ampliado. `handle` resuelve usuario; `command` usa control optimista de versión; consultas leen `reported` |
| [storage_function.py](../../backend/storage_function.py) | Funciones puras de validación, copia de campos permitidos y escritura idempotente. Handler mínimo con cliente reutilizado |
| [prepare_deployment.py](../../scripts/prepare_deployment.py) | Inserta el código de almacenamiento y SQL en la plantilla CloudFormation; empaqueta solo el archivo Python de Alexa |
| [analyze_evidence.py](../../scripts/analyze_evidence.py) | Calcula integridad, latencia y ciclos por origen a partir de archivos exportados, sin red |
| [observe_storage.py](../../scripts/observe_storage.py) | Mide una cota superior de latencia con consultas consistentes acotadas; solo usar tras verificar cupo AWS |

### Conceptos importantes para defender el proyecto

`desired` es una intención, `reported` es lo que el controlador aplicó. El ángulo del servo es una orden eléctrica, no una medición de su posición. `activationId` evita repetir una misma solicitud al reconectar. Se persiste antes de mover; un corte entre persistencia y movimiento puede perder una dosis, por lo que no se afirma ejecución exactamente una vez.

Modo e intervalo se escriben en NVS solo cuando cambian y la escritura es exitosa. Al arrancar se recuperan, incluso sin red. El primer flanco después de estabilizar el PIR puede dosificar: el historial del intervalo no se conserva a través de un reinicio. El PIR requiere 60 s de estabilización; su nivel inicial no se considera un flanco nuevo.

Los intervalos usan resta unsigned de `millis()` para tolerar su desbordamiento. Un valor entre 5 y 86400 s cabe en milisegundos de 32 bits. El LED usa canales PWM 12–14 y el servo se asigna primero; así no se cambia el temporizador de 50 Hz del servo con los 5 kHz del RGB.

Python rechaza booleanos donde se esperan enteros (`bool` hereda de `int`). La Lambda no almacena campos arbitrarios ni cuerpos de Alexa. En errores transitorios de DynamoDB propaga la excepción para que Lambda reintente; inválidos y duplicados terminan normalmente. Los eventos conservan el origen de todo el ciclo: `voz` o `edge`.

## Red, integridad y límites

Se captura una muestra cada 60 s y, si cambia un estado, como máximo una muestra adicional cada 2 s. Cada cambio servo/RGB produce un evento independiente. Se publica un registro por vez, con intervalo mínimo de 250 ms entre publicaciones nuevas. Sin ACK se reintenta cada 5 s usando el mismo identificador.

Cada snapshot contiene sensores y actuadores; un evento añade transición y origen. La regla IoT solo toma publicaciones con esquema 4 y token igual al identificador. Los comandos Alexa no generan falsas lecturas. Una condición `attribute_not_exists(recordKey)` evita filas duplicadas por reentrega.

La aceptación del Shadow no confirma la escritura en DynamoDB. Hay reintentos de Lambda, pero una interrupción prolongada de AWS puede perder datos y debe aparecer en la métrica de integridad. No hay una garantía absoluta de entrega ni una DLQ adicional. Al llenarse la cola se descarta el nuevo registro y aumenta `droppedRecords`; al reiniciar se pierde toda la cola. En reconexión se drenan snapshots históricos y después se publica el estado reciente; mientras tanto Alexa puede advertir datos antiguos.

La red utiliza las bibliotecas síncronas heredadas. Se evitan conexiones TLS y procesamiento MQTT durante un ciclo mecánico, pero una reconexión cuando el motor está en reposo todavía puede retrasar la lectura de sensores. El ensayo de fallos de red debe medir ese caso; no es un controlador de tiempo real estricto.

El arranque mantiene RGB apagado hasta la primera lectura filtrada. Verde significa nivel suficiente, **no certifica salud de WiFi, servo o AWS**. Un cable NPN desconectado puede parecer nivel bajo; no existe diagnóstico eléctrico independiente. La estabilidad temporal no reemplaza la calibración de montaje.

## Para preparar posteriormente el informe

Caso/requerimientos: esta guía y la matriz de pruebas. Análisis/diseño: diagramas, contratos y mockups. Desarrollo: enlaces al código y configuración. Pruebas/resultados: completar únicamente con evidencias nuevas. Conclusiones/recomendaciones: comparar métricas con objetivos, explicar pérdidas o errores y discutir el límite del sensor y el procesamiento Edge. Anexos: fotos reales, exportaciones anonimizadas y trazas del prototipo.

Mantener las ocho secciones de §4.2 al escribir el informe final, conservar el informe anterior y respetar la autoría de commits de cada integrante.
