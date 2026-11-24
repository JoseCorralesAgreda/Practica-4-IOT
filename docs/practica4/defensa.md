# Guía de defensa y demostración — Práctica 4

Complemento del [informe](informe.md). La defensa y la demo son componentes distintos del informe y cada uno vale un tercio de la calificación, según la consigna.

## Recorrido de demostración

1. Identificar ESP32, PIR, SG90, XKC y RGB en el circuito y explicar GND común y alimentación.
2. Mostrar nivel suficiente/verde y bajo/rojo. Explicar que es una detección puntual.
3. Consultar nivel, color y modo en Alexa; relacionar la respuesta con reported.
4. Cambiar el intervalo y consultar el valor aplicado. Distinguir solicitud de confirmación.
5. Activar por voz y observar el ciclo; luego demostrar un flanco PIR en automático.
6. Mostrar un ciclo con nivel bajo, que no debe bloquear las dosis.
7. Consultar DynamoDB por Thing/tiempo y explicar una lectura, una transición y su origen.
8. En el ensayo autorizado, desconectar red, producir un evento, restaurar y mostrar GET/ACK. La aplicación de desired requiere mostrar el ID o valor antes y después.

## Preguntas y respuestas técnicas

| Pregunta | Respuesta |
|---|---|
| ¿Qué amplía P3? | Sensor de nivel/RGB, histórico por IoT Rule/Lambda/DynamoDB, modo/intervalo persistentes, cola y reportes. |
| ¿Por qué dos sensores? | PIR detecta movimiento; XKC líquido a la altura física. Son variables diferentes. |
| ¿Por qué Edge? | La decisión usa información local y debe continuar durante problemas de conectividad. |
| ¿Por qué no una Lambda de control? | RF13 admite Edge; las reglas actuales no necesitan histórico ni varios objetos. La Lambda nueva almacena. |
| ¿Qué es desired? | Intención escrita por Alexa; no es evidencia de movimiento físico. |
| ¿Qué es reported? | Lecturas y estados aplicados por firmware; el ángulo es una orden, no posición medida. |
| ¿Por qué activationId? | Dos pulsaciones distintas necesitan IDs distintos. Persistir el último evita repetir una orden después de reiniciar. |
| ¿Cómo se controla la repetición? | `activationId` persistente y validación de estado impiden repetir una orden ya procesada. |
| ¿Qué evita dos filas por reintento? | Clave estable Thing/recordKey y PutItem con condición de no existencia. |
| ¿Cómo se verifica DynamoDB? | Con la combinación de ACK, regla IoT, Lambda, claves y consulta histórica registrada en EV01, EV02 y EV06. |
| ¿Qué contiene recordKey? | Timestamp de observación de 13 dígitos y messageId; permite Query ordenado por intervalo. |
| ¿Por qué sin índices extra? | Los dos reportes necesitan un Thing y ventana temporal; esa consulta usa las claves primarias. |
| ¿Qué pasa si la cola se llena? | Se conserva la cabeza en espera y se descarta el nuevo registro; aumenta droppedRecords. |
| ¿Qué pasa al reiniciar? | NVS conserva modo/intervalo/última orden; la cola RAM y el historial de cooldown no se conservan. |
| ¿Cómo se cuentan dosis? | Eventos servo con to=idle. No sumar cyclesSinceBoot ni contar cada fase. |
| ¿Qué prueban los 135 ACK? | Aceptación de los 135 IDs publicados por el Shadow dentro del log, complementada por los registros históricos de EV06. |
| ¿Cómo se interpretan los 34 registros? | Como la muestra histórica utilizada para las estadísticas de almacenamiento y eventos del informe. |
| ¿Qué significa 4325 ms? | Máximo registrado de la muestra de almacenamiento, dentro del umbral de 5 s declarado. |
| ¿Qué prueba el video de reconexión? | Recuperación de la conectividad y reanudación del intercambio MQTT después de la desconexión. |
| ¿Cómo funciona la vinculación? | La Lambda resuelve cada Thing mediante la tabla de vínculos por usuario y las políticas autorizadas. |
| ¿Verde significa sistema sano? | Solo nivel suficiente; no garantiza red, AWS ni servo. |
| ¿Cómo se garantiza gasto cero? | El registro de plan/cupo es una condición previa; una estimación y una alerta no garantizan costo nulo. |

## Aportes individuales

Integrantes: Jose Franz Corrales Agreda, Rasshid Lopez Mejia y Alejandro Bustamante Del Castillo. El historial revisado registra el trabajo del equipo y el mensaje 27cbd53 menciona a los tres integrantes.

Cada integrante debe poder explicar el sistema completo y la diferencia entre diseño, configuración y resultados. Para ensayar, elegir un registro del CSV y seguir su trayecto desde `capture` hasta la consulta del reporte.
