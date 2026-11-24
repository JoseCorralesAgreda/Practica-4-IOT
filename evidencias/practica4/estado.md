# Estado verificable de la Práctica 4

Fecha de trabajo inicial: 21 de noviembre de 2026. Integración AWS actualizada el 23 de noviembre de 2026. Este documento es una bitácora de validación, no el informe final. Las evidencias antiguas pertenecen a la Práctica 3.

## Implementado localmente

- XKC-Y23A-NPN, filtrado temporal y RGB de cátodo común; nivel bajo solo avisa.
- Montaje de nivel actualizado a pull-up interno de GPIO26 (`INPUT_PULLUP`), sin resistencia externa de señal. El firmware ya habilitaba ese modo; se corrigieron comentarios, guías y diagramas contradictorios. Validación eléctrica y estabilidad con el servo pendientes.
- PIR y servo heredados, modo/intervalo persistentes, operación local sin WiFi y comandos por Shadow.
- Eventos de servo/RGB con origen y cola RAM acotada con ACK por token.
- Backend Alexa ampliado y modelo es-ES actualizado.
- Lambda de validación/almacenamiento con deduplicación y tabla por Thing/tiempo.
- Plantilla AWS con SQL, permisos, tabla, TTL, logs y regla desactivada por defecto.
- Documentación de estudio, diagramas, mockups y seis escenarios manuales.
- Herramientas para empaquetado, estimación de consumo e integridad/latencia.

## Verificación local

La versión final pasó **43 tests de Python** y compiló el firmware: **RAM estática 47 140 bytes (14.4 %), Flash 940 461 bytes (71.8 %)**. La memoria dinámica de TLS y de la cola no está incluida en esa cifra estática. Se incluyen pruebas de análisis de evidencia y observación consistente. Consultar [registro Python](verificacion-local.txt) y [registro de compilación](compilacion.txt).

Se validó la plantilla generada con cfn-lint, sin desplegar recursos. El código Python se normalizó y revisó con Ruff, sin incidencias. Se verificaron diez JSON de aplicación y los enlaces Markdown actuales; el archivo de extensiones VS Code es JSON con comentarios y no se trata como JSON estricto. La revisión de archivos publicables no detectó patrones de claves de acceso o claves privadas; `secrets.h`, los binarios y ZIP están ignorados. Estos resultados no prueban funcionamiento de la infraestructura remota ni calibración física.

## Pendiente de integración real

| Área | Estado y causa |
|---|---|
| Identidad y Free Tier | STS confirmado en cuenta 679937333206; plan FREE ACTIVE, créditos 119.94 USD, vencimiento 2027-05-07; uso detallado vacío, no equivale a consumo cero |
| Recursos AWS nuevos | Pila ambientador-p4 desplegada, regla habilitada; recorrido Shadow → IoT → Lambda → DynamoDB comprobado con muestra sintética separada |
| Lambda Alexa remota | Código actualizado y SHA-256 verificado; entorno/disparador conservados; inicio y consulta sin vínculo comprobados por invocación directa |
| Modelo Alexa remoto | JSON local preparado; importación/build/test en consola pendientes |
| ESP32 físico | Firmware compilado, no cargado en esta sesión |
| Sensor/recipiente/RGB | GPIO, polaridad, material del depósito, compatibilidad con fragancia y color rojo pendientes de prueba |
| Métricas de integración | Integridad, latencia real, reconexión, control Edge y gasto real pendientes de M01–M06 |

No se publicaron secretos, no se hizo push ni se generó el informe final. La eliminación preexistente de `Práctica_3.md` se dejó intacta; el informe y las evidencias de la Práctica 3 no se sobrescribieron.

El 23 de noviembre se repitieron satisfactoriamente los 43 tests, la compilación (mismas cifras de RAM/Flash), cfn-lint y la validación CloudFormation. El Shadow físico consultado no tenía `schemaVersion=4`; no se cargó la placa. Ver [evidencia AWS y límites](aws-integracion-2026-11-23.md). Los ensayos sintéticos no se cuentan como resultados de M01–M06.

## Registro manual por completar

| Prueba | Fecha / condiciones | Resultado medido | Evidencia / incidencia |
|---|---|---|---|
| M01 | Pendiente | — | — |
| M02 | Pendiente | — | — |
| M03 | Pendiente | — | — |
| M04 | Pendiente | — | — |
| M05 | Pendiente | — | — |
| M06 | Pendiente | — | — |

## Ajuste local de LED e intervalo de debug

Nivel bajo cambiado a rojo (`red`) e intervalo inicial a 5 s. Verificados: 43 tests Python, Ruff y compilación PlatformIO correctos. Pendientes: carga de placa, actualización de Lambdas y pruebas integradas de color/intervalo. La configuración persistida o desired anterior requiere solicitar 5 s por Alexa y confirmar reported; no se modificaron recursos AWS en este ajuste.
