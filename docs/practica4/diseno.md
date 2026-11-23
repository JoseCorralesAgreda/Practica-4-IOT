# Diseño del sistema

Diagramas de la versión implementada; el montaje y las mediciones físicas siguen pendientes. Los contratos y patrones de acceso están en [contratos](contratos.md), y los pines en [configuración](configuracion.md).

## Bloques del objeto

```mermaid
flowchart LR
  PIR[HC-SR501: movimiento] --> ESP[ESP32: Ambientador]
  XKC[XKC-Y23A-NPN: nivel puntual] --> FIL[Filtrado 500 ms]
  FIL --> ESP
  ESP --> SERVO[SG90: pulsación del atomizador]
  ESP --> LED[RGB cátodo común: verde / anaranjado]
  NVS[(NVS: modo, intervalo, última orden)] <--> ESP
  ESP --> Q[Cola RAM: 32 registros]
  Q --> TLS[MQTT TLS: Shadow]
  PWR[Fuente regulada 5 V y GND común] --> ESP
  PWR --> SERVO
```

## Arquitectura

```mermaid
flowchart LR
  U[Usuarios diferentes] --> AX[Alexa: simulador es-ES]
  AX --> SK[Lambda Alexa existente]
  SK <--> V[(DynamoDB: userId → thingName)]
  SK -->|Get / Update desired| SH[IoT Core: Shadow por Thing]
  SH -->|get y delta| ESP[ESP32: reglas Edge]
  ESP -->|reported + clientToken| SH
  SH -->|update/accepted| RULE[IoT Rule: esquema 4 y token válido]
  RULE --> L[Lambda de validación y almacenamiento]
  L -->|PutItem condicional| H[(DynamoDB histórico: Thing + tiempo/ID)]
  H -.-> MOCK[Mockups: reposición y uso]
  SH -->|ACK token| ESP
```

Los mockups no se conectan a AWS. No hay ruta Alexa → dispositivo fuera del Shadow ni control de actuadores desde la Lambda de almacenamiento.

## Circuito propuesto

![Esquema eléctrico con GPIO, resistencias y conexiones](circuito.svg)

[Abrir esquema SVG](circuito.svg). El diagrama siguiente detalla también las redes de alimentación y masa.

```mermaid
flowchart TB
  V5[Fuente regulada 5 V DC] --- SV[SG90 V+]
  V5 --- PV[PIR VCC]
  V5 --- XV[XKC VCC según identificación del fabricante]
  G[GND común] --- SG[SG90 GND]
  G --- PG[PIR GND]
  G --- XG[XKC GND / emisor NPN]
  G --- EG[ESP32 GND]
  G --- C[RGB cátodo común]
  P18[ESP32 GPIO18] --> SS[SG90 señal]
  PO[PIR OUT 3.3 V] --> P27[ESP32 GPIO27]
  subgraph ESPIN[Interior del ESP32]
    V33[3.3 V interno] --- RP[Pull-up interno habilitado por INPUT_PULLUP]
    RP --- P26[GPIO26]
  end
  XO[XKC salida NPN / colector] --- N
  N[Nodo de señal 0..3.3 V] --- P26
  P21[GPIO21 PWM canal12] --> RR[330 Ω] --> R[RGB ánodo rojo]
  P22[GPIO22 PWM canal13] --> RG[330 Ω] --> GR[RGB ánodo verde]
  P23[GPIO23 PWM canal14] --> RB[330 Ω] --> B[RGB ánodo azul]
  R --> C
  GR --> C
  B --> C
```

ESP32 alimentado por USB; fuente de 5 V del servo con masa común. No unir dos fuentes de 5 V ni alimentar el servo desde GPIO/3V3. Añadir desacoplo próximo al servo (100 nF y 470 µF propuestos, verificar respuesta de la fuente). Identificar cables por el diagrama del ejemplar, no por colores supuestos. Comprobar que OUT no entrega 5 V antes de conectar GPIO26; con colector abierto desconectado puede quedar flotante. El esquema presupone salida NPN de colector abierto; si el ejemplar incluye pull-up interno a 5 V, emplear adaptación de nivel. GPIO26 usa exclusivamente el pull-up interno del ESP32, sin resistencia externa ni cable a 3V3; las resistencias del RGB permanecen. Verificar niveles y estabilidad tras inicializar el firmware. Fuente y todas las cargas permanecen por debajo de 12 V DC.

## Clases y módulos

```mermaid
classDiagram
  class Ambientador {
    +begin()
    +tick()
    -applyDesired(desired)
    -updateSensor(now)
    -startCycle(now, origin)
    -updateServo(now)
    -capture(actuator, from, to, origin)
  }
  class LevelIndicator {
    +begin()
    +update(now) bool
    +ready() bool
    +low() bool
    +color() char_ptr
  }
  class TelemetryQueue {
    +push(reported)
    +publish(mqtt, topic, now)
    +acknowledge(token)
    +epochMs() uint64
  }
  class AmbientadorSkill {
    +handle(event)
    +command(thing, request_id, automatic, cooldown_seconds)
    +get_shadow(thing)
    +respond(text)
  }
  class StorageModule {
    <<module>>
    +validate_record(event, stored_at_ms)
    +store_record(event, table, now_ms)
    +lambda_handler(event, context)
  }
  Ambientador *-- LevelIndicator
  Ambientador *-- TelemetryQueue
  Ambientador --> Servo
  Ambientador --> Preferences
  Ambientador --> PubSubClient
  AmbientadorSkill --> DynamoDBBindings
  AmbientadorSkill --> IoTShadowClient
  StorageModule --> DynamoDBHistory
```

La Lambda histórica es funcional; el rectángulo `StorageModule` representa un módulo, no una clase artificial. El backend Alexa mantiene la clase ya existente para reutilizar clientes y facilitar pruebas con dobles.

## Consulta de sensores por voz

```mermaid
sequenceDiagram
  participant ESP as ESP32
  participant SH as Shadow
  participant U as Usuario
  participant A as Alexa
  participant L as Lambda skill
  participant V as Vinculaciones
  ESP->>ESP: Leer PIR y nivel, aplicar filtro
  ESP->>SH: reported + sampledAt
  U->>A: ¿Cuál es el nivel de fragancia?
  A->>L: Intent + userId
  L->>V: GetItem consistente(userId)
  V-->>L: thingName
  L->>SH: GetThingShadow(thingName)
  SH-->>L: reported
  L->>L: Verificar frescura y levelReady
  L-->>A: Nivel puntual o datos no recientes
  A-->>U: Respuesta hablada
```

Una consulta no fuerza una lectura directa en la placa: usa el último reporte, con su fecha. La misma secuencia aplica a PIR, motor, LED, modo e intervalo.

## Comando de voz sobre el motor

```mermaid
sequenceDiagram
  actor U as Usuario
  participant A as Alexa
  participant L as Lambda skill
  participant V as Vinculaciones
  participant SH as Shadow
  participant ESP as ESP32
  participant S as Servo
  U->>A: Activa el ambientador
  A->>L: ActivarIntent + requestId + userId
  L->>V: Resolver Thing
  L->>SH: GET y verificar orden pendiente
  L->>SH: UPDATE desired.activationId con version
  SH-->>ESP: delta (o GET tras reconexión)
  L-->>A: Solicitud enviada, no confirmación mecánica
  A-->>U: Respuesta
  ESP->>ESP: Validar ID y persistir antes de mover
  ESP->>S: 180°; luego 0°; terminar ciclo
  ESP->>ESP: Capturar tres eventos, origin=voz
  ESP->>SH: reported + ACK de activationId
```

Cambiar modo/intervalo usa el mismo flujo, pero se persiste el parámetro y se confirma en `reported`; no mueve el servo por sí solo.

## Almacenamiento

```mermaid
sequenceDiagram
  participant E as ESP32 / cola
  participant S as Shadow
  participant R as IoT Rule
  participant L as Lambda almacenamiento
  participant D as DynamoDB histórico
  E->>S: update reported (messageId, clientToken)
  S-->>E: update/accepted mismo token
  E->>E: Retirar cabeza de cola
  S->>R: update/accepted
  R->>R: Filtrar esquema/token; enriquecer Thing y recepción
  R->>L: Invocación asíncrona
  L->>L: Validar tipos, rangos y coherencia
  alt Mensaje válido
    L->>D: PutItem con condición de no existencia
    D-->>L: Guardado / ya existe
  else Mensaje inválido
    L->>L: Descartar sin escribir
  end
```

Un error transitorio de DynamoDB se propaga para reintento; una invocación repetida no genera otra fila. ACK y almacenamiento son dos confirmaciones distintas.

## Regla automática PIR y temporización

```mermaid
sequenceDiagram
  participant P as PIR
  participant E as Ambientador
  participant M as Servo
  participant Q as Cola
  P->>E: Flanco LOW → HIGH después de estabilización
  E->>E: automatic && idle && intervalo cumplido
  E->>M: 180°
  E->>Q: idle → pressing, origen edge
  Note over E: Pasan al menos 700 ms, sin espera bloqueante
  E->>M: 0°
  E->>Q: pressing → returning, origen edge
  Note over E: Pasan al menos otros 700 ms
  E->>Q: returning → idle, origen edge
  Note over E,Q: Funciona sin WiFi; cola limitada
```

## Regla automática de nivel y RGB

```mermaid
sequenceDiagram
  participant X as XKC-Y23A-NPN
  participant F as LevelIndicator
  participant L as RGB
  participant Q as Cola
  X->>F: Cambio de salida digital
  F->>F: Esperar estabilidad durante 500 ms
  alt Sin líquido a la altura del sensor
    F->>L: PWM rojo 255, verde 65, azul 0
  else Con líquido
    F->>L: PWM rojo 0, verde 255, azul 0
  end
  F->>Q: Transición RGB con origen edge
  Note over F,L: No altera el modo ni impide dosificar
```

## Estados ortogonales

```mermaid
stateDiagram-v2
  state Modo {
    [*] --> RecuperadoNVS
    RecuperadoNVS --> Manual: automatic=false por defecto
    RecuperadoNVS --> Automatico: automatic=true persistido
    Manual --> Automatico: desired automatic=true
    Automatico --> Manual: desired automatic=false
  }
  state Motor {
    [*] --> Reposo
    Reposo --> Presion: voz válida / PIR elegible
    Presion --> Retorno: 700 ms, ordenar 0°
    Retorno --> Reposo: 700 ms, contar ciclo
  }
  state Indicador {
    [*] --> Apagado
    Apagado --> Verde: primera lectura suficiente estable
    Apagado --> Anaranjado: primera lectura baja estable
    Verde --> Anaranjado: nivel bajo estable 500 ms
    Anaranjado --> Verde: nivel suficiente estable 500 ms
  }
```

El modo, el motor y el indicador no se excluyen entre sí: puede dosificarse con LED anaranjado en cualquiera de los modos. Una pérdida de WiFi no cambia estas máquinas de estados.
