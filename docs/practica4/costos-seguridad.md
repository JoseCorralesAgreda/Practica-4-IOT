# Costos y seguridad

## Condición de gasto cero

No se activan recursos hasta verificar la **oferta aplicable a la cuenta**, vigencia y consumo agregado. El bloqueo `NoCredentials` registrado el 21 de noviembre se resolvió el 23 de noviembre de 2026 con `aws login`. STS confirmó la cuenta `679937333206`. `get-account-plan-state` devolvió plan `FREE`, estado `ACTIVE`, saldo de créditos de **119.94 USD** y vencimiento **2027-05-07T21:32:10.160000Z**, antes de desplegar y antes de habilitar la regla. El saldo es agregado a la cuenta y no representa una medición del costo de este proyecto.

`get-free-tier-usage` devolvió una lista vacía: no acredita consumo cero ni cuotas gratuitas por servicio. Esta cuenta usa el plan gratuito con créditos; no se le atribuyen automáticamente las cuotas históricas de 12 meses descritas abajo. AWS incluye IoT Core entre los servicios elegibles para esos créditos ([precios IoT Core](https://aws.amazon.com/iot-core/pricing/)); el plan gratuito limita su vigencia y acceso ([planes de AWS](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/free-tier-plans.html)). No se cambió el plan ni se invocó Cost Explorer. El consumo puede reflejarse con demora: repetir las consultas antes y después de las sesiones, y no interpretar un saldo sin cambios como prueba de costo nulo.

La página de [precios de IoT Core](https://aws.amazon.com/iot-core/pricing/), consultada en esta sesión, publica una oferta temporal de 12 meses con 500 000 mensajes, 225 000 operaciones Registry/Shadow, 250 000 reglas y acciones, y 2 250 000 minutos mensuales. Es una referencia pública, no prueba de que esta cuenta tenga esa oferta. AWS ha cambiado sus planes y condiciones; confirmar `get-account-plan-state` y `get-free-tier-usage`, sin interpretar ausencia de un servicio en la respuesta como gratuidad.

## Estimación reproducible

Ejecutar [estimate_usage.py](../../scripts/estimate_usage.py). Hipótesis: un Thing, 30 días, 20 dosis/día, 40 cambios PIR/día, dos cambios de nivel/día, 20 solicitudes Alexa/día, un arranque diario y 200 ms promedio por Lambda a 128 MB. No son mediciones. Mensajes con hasta 2 KB para presupuesto Shadow/DynamoDB; comprobar tamaño real, especialmente metadatos y documentos aceptados.

| Magnitud mensual estimada | Sesiones de 2 h/día | Encendido 24 h/día |
|---|---:|---:|
| Registros de histórico / disparos de regla / acciones | 9 120 | 48 720 |
| Presupuesto de mensajes MQTT (incluye respuestas y margen) | 40 080 | 198 480 |
| Unidades presupuestadas de operaciones Shadow | 20 640 | 99 840 |
| Invocaciones Lambda, incluido Alexa | 9 720 | 49 320 |
| GB-s Lambda estimados | 243 | 1 233 |
| Escrituras DynamoDB, incluido margen para vínculos | 9 720 | 49 320 |
| Unidades de escritura del histórico, hasta 2 KB por fila | 18 240 | 97 440 |
| Minutos conectados | 3 600 | 43 200 |
| Almacenamiento histórico estimado con TTL de siete días, bytes | 4 358 144 | 23 281 664 |

No se suman mensajes, Shadow y reglas como si fueran una sola cuota: cada dimensión tiene su propio límite. Las cifras de tráfico quedan por debajo de la referencia pública citada, **sin incluir el resto de la cuenta ni certificar elegibilidad**. Sumar lecturas del histórico, consultas Alexa, reintentos, logs y otros dispositivos. Los flancos frecuentes o un intervalo de cinco segundos pueden invalidar completamente estas hipótesis.

La [capa gratuita de DynamoDB](https://aws.amazon.com/dynamodb/pricing/) incluye capacidad provisionada Standard; la tabla nueva usa 1 RCU y 5 WCU, frente a la referencia publicada de 25 RCU/25 WCU. La capacidad se factura por aprovisionamiento, incluso sin solicitudes; sumar tablas e índices existentes. TTL no elimina filas inmediatamente. La [oferta Lambda](https://aws.amazon.com/lambda/pricing/) debe comprobarse en la cuenta antes de comparar invocaciones y GB-s; los logs tienen su propio consumo.

## Medidas aplicadas

La regla nueva se creó desactivada y se habilitó el 23 de noviembre después de comprobar las Lambdas y reconfirmar el plan gratuito. No se añaden API Gateway, NAT, S3, EventBridge, índices, backups, réplicas ni interfaces web conectadas. La frecuencia base pasa de 15 a 60 s y los cambios de estado se agrupan en muestras adicionales con separación de dos segundos; las transiciones de actuadores se conservan individualmente. Pruebas cortas, sin tráfico de carga innecesario.

La tabla de vínculos heredada está en `PAY_PER_REQUEST`; se conservó su configuración. La tabla de histórico usa 1 RCU y 5 WCU con TTL de siete días. No declarar gratuitas las operaciones bajo demanda por analogía con la cuota de capacidad provisionada. El despliegue y los ensayos consumen recursos elegibles del plan; sus importes reales por servicio no se midieron en esta sesión.

Revisar uso antes y después de cada sesión. Si no hay margen, detener el ensayo y desconectar la placa de AWS; desactivar solo la regla no detiene consumo MQTT/Shadow. Las alarmas de presupuesto avisan con retraso y **no son un interruptor de gasto**. No se configura un correo de alerta inventado. Configurar las alertas gratuitas disponibles en la cuenta con un destinatario confirmado; no contratar funciones pagadas de presupuesto.

## Secretos y permisos

- `secrets.h`, certificados, claves, `.env`, `.aws/`, `.local/`, ZIP y `.pio/` están ignorados. Los binarios incorporan credenciales: tampoco se publican.
- Las funciones usan roles IAM; no reciben access keys. El empaquetado usa una lista explícita de un archivo Python y no recorre el directorio del proyecto.
- El firmware conserva TLS con CA y certificado del Thing, sin conexiones inseguras ni credenciales en logs.
- Certificado IoT: Connect limitado a su clientId; Publish/Subscribe/Receive limitados a los tópicos de su Shadow.
- Alexa: acceso a la tabla de vínculos y a la lista autorizada de Things, con comprobación de applicationId y userId.
- Almacenamiento: solo PutItem de su tabla y escritura en su grupo de logs. Invocación autorizada únicamente desde el ARN de la regla y la cuenta.
- No publicar userId Alexa ni exportaciones sin revisar. Las plantillas con ARN del proyecto heredado contienen identificadores, no claves de acceso; revisarlos antes de reutilizar otra cuenta.

Antes de cualquier push revisar nombres de archivos y coincidencias de secretos sin imprimir sus valores. Que un archivo esté ignorado no lo elimina si ya fue rastreado en Git. No se hizo push ni se alteraron certificados en esta sesión.
