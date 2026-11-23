# Reglas del proyecto

- Extender el código de la Práctica 3 conforme a `Práctica_4.md`; conservar su informe y sus evidencias históricas. No generar el informe final de la Práctica 4 hasta culminar el proyecto.
- Comunicar las dudas de implementación antes de implementar. No inventar conexiones, características eléctricas, resultados físicos ni evidencias de AWS.
- Mantener firmware C++ modular y orientado a objetos, con control temporal sin esperas bloqueantes en la lógica de actuadores; Python conforme a PEP 8, con validación explícita y responsabilidades separadas.
- Conservar la vinculación multiusuario. Alexa controla el dispositivo exclusivamente mediante `desired`; `reported` describe el estado observado o aplicado, distinguiendo órdenes de mediciones.
- Incorporar PIR, servomotor del atomizador, sensor XKC-Y23A-NPN y LED RGB de cátodo común: verde con nivel suficiente y anaranjado con nivel bajo. El nivel bajo solo avisa: nunca bloquea dosis automáticas ni por voz. Usar cargas de hasta 12 V DC.
- Actualizar documentación de estudio, contratos, diagramas y configuraciones junto con cada cambio de código. Mantener trazabilidad con la rúbrica y un conjunto acotado de pruebas manuales fundamentales.
- Verificar cambios con pruebas pertinentes de Python y compilación del firmware. Separar resultados comprobados de validaciones pendientes en hardware, AWS y Alexa.
- Nunca publicar secretos ni mostrarlos en salidas de herramientas: WiFi, claves privadas, certificados y credenciales permanecen en archivos locales ignorados; solo versionar plantillas ficticias. No sobrescribir `secrets.h`.
- Usar AWS únicamente dentro de la capa gratuita verificando elegibilidad y consumo de la cuenta antes de provisionar o activar recursos. Una alerta de presupuesto no garantiza gasto cero. Si no se puede verificar la condición, preparar configuración local y comunicar el impedimento.
- Aplicar permisos mínimos, limitar frecuencia de mensajes y retención de datos; evitar servicios o configuraciones con cargos. No publicar, hacer push ni modificar recursos ajenos al proyecto sin autorización.
- Respetar cambios existentes del usuario y no atribuirse aportes de otros integrantes.
