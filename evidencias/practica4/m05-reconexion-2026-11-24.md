# Registro de reconexión M05

```text
PIR t=3941683 ms GPIO27=LOW listo=1 servo=idle automatico=1
SHADOW_ACK id=p4-4a27d428b949d4267291bf5e-302
Shadow: actualizacion de reported aceptada por AWS.
PUBLISH id=p4-4a27d428b949d4267291bf5e-303
[3942494][E][ssl_client.cpp:37] _handle_error(): [data_to_read():361]: (-76) UNKNOWN ERROR CODE (004C)
PIR t=3972105 ms GPIO27=HIGH listo=1 servo=idle automatico=1
Servo: angulo ordenado=180 grados (presion); LED encendido
Inicio ciclo: 3972105 ms
Servo: angulo ordenado=0 grados (retorno); LED encendido
Servo: ciclo terminado, angulo ordenado=0 grados; LED apagado
PIR t=3975163 ms GPIO27=LOW listo=1 servo=idle automatico=1
MQTT conectado; solicitando desired pendiente.
PUBLISH id=p4-4a27d428b949d4267291bf5e-303
SHADOW_ACK id=p4-4a27d428b949d4267291bf5e-303
Shadow: actualizacion de reported aceptada por AWS.
PUBLISH id=p4-4a27d428b949d4267291bf5e-304
SHADOW_ACK id=p4-4a27d428b949d4267291bf5e-304
Shadow: actualizacion de reported aceptada por AWS.
PUBLISH id=p4-4a27d428b949d4267291bf5e-311
SHADOW_ACK id=p4-4a27d428b949d4267291bf5e-311
Shadow: actualizacion de reported aceptada por AWS.
```

El registro muestra un error TLS, un flanco PIR y ciclo Edge durante el incidente, reconexión MQTT, solicitud de `desired` y reenvío confirmado de la publicación pendiente `303`. El video EV12 complementa este registro y muestra visualmente la recuperación correcta de la conexión del objeto inteligente.
