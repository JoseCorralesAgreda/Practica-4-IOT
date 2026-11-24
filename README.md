# Ambientador inteligente — Práctica 4

Extensión del proyecto de la Práctica 3: ESP32 DOIT DEVKIT V1, PIR HC-SR501 y servo SG90, con **XKC-Y23A-NPN** y **RGB de cátodo común**. El LED se muestra verde con líquido a la altura del sensor y rojo con nivel bajo. **El aviso nunca bloquea la dosificación automática ni por voz.**

El sensor de líquido usa GPIO26 con **pull-up interno del ESP32 (`INPUT_PULLUP`)**, sin resistencia externa de señal. Se mantienen las resistencias del RGB. Ver conexiones y comprobaciones eléctricas en [configuración](docs/practica4/configuracion.md).

Alexa conserva la vinculación de cada usuario con su Thing. Todos los comandos pasan por el Shadow. El ESP32 ejecuta las reglas locales y una nueva Lambda valida y registra lecturas y cambios de actuadores en DynamoDB, con origen e identificadores para deduplicación.

## Documentación vigente

- [Informe técnico de la Práctica 4](docs/practica4/informe.md): desarrollo según rúbrica, resultados, circuito, diagramas, anexos y videos de evidencia.
- [Guía de ejecución de pruebas](docs/practica4/guia-ejecucion-pruebas.md) y [guía de defensa](docs/practica4/defensa.md).

- [Guía de estudio y decisiones](docs/practica4/guia.md): recorrido del código, alcance y reglas.
- [Diseño y diagramas](docs/practica4/diseno.md): bloques, circuito, clases, arquitectura, estados y secuencias.
- [Contratos de datos y Alexa](docs/practica4/contratos.md): Shadow, regla SQL, histórico, intents y consultas.
- [Montaje y despliegue](docs/practica4/configuracion.md): conexiones, preparación local y configuración AWS/Alexa.
- [Costos y seguridad](docs/practica4/costos-seguridad.md): consumo reproducible y condición de capa gratuita.
- [Pruebas fundamentales y trazabilidad](docs/practica4/pruebas.md): seis pruebas manuales integradas, métricas y rúbrica.
- [Mockups de reportes](docs/practica4/reportes.html): abrir en un navegador; datos ficticios y sin conexión a AWS.
- [Estado verificable](evidencias/practica4/estado.md): comprobaciones y resultados de la práctica.

El informe de la Práctica 3 y sus guías constan en el historial Git (por ejemplo, `git show HEAD:docs/informe.md`). La Práctica 4 dispone de un informe técnico completo, con sus pruebas manuales y evidencias audiovisuales anexas.

**Registro AWS y evidencias del 24 de noviembre de 2026:** histórico desplegado, regla habilitada en `us-east-2`, Lambda Alexa actualizada, fotos físicas, nueve capturas Alexa, serial, CSV y dos videos. Consultar el [estado consolidado](evidencias/practica4/estado.md) y el [informe final](docs/practica4/informe.md).

## Uso

1. Vincular: «vincula mi ambientador con thing».
2. Dosificar: «activa el ambientador»; ciclo 0° → 180° → 0°, 700 ms por fase.
3. Control local: «activa el modo automático». Un nuevo flanco PIR dispara una dosis si el motor está libre y transcurrió el intervalo; no dosifica repetidamente por mantener el PIR alto.
4. Configurar: «cambia el intervalo a cinco segundos»; valores enteros de 5 a 86400 s. El valor inicial de depuración es 5 s; un intervalo ya guardado en la placa o presente en `desired` tiene prioridad. Para ajustarlo en una placa existente, usar la orden anterior y consultar el intervalo aplicado.
5. Consultar: «hay movimiento», «cuál es el nivel de fragancia», «de qué color está el led», «cuál es el estado del motor», «cuál es el modo actual» y «cuál es el intervalo».
6. «Desactiva el modo automático» impide nuevos ciclos PIR y deja terminar el actual. La voz sigue permitida con motor libre y puede saltarse el intervalo automático.

## Verificación local

```powershell
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -r backend/requirements-dev.txt platformio
./.venv/Scripts/python.exe -B -m unittest discover -s tests -v
./.venv/Scripts/python.exe -m ruff check backend scripts tests
./.venv/Scripts/python.exe -m platformio run -d firmware
./.venv/Scripts/python.exe scripts/prepare_deployment.py
./.venv/Scripts/cfn-lint.exe .local/deployment/practica4-stack.json
./.venv/Scripts/python.exe scripts/estimate_usage.py
```

Si no existe `firmware/include/secrets.h`, copiar `secrets.example.h` a ese nombre y completar localmente. **Nunca sobrescribir un archivo de secretos existente ni publicarlo.** No subir firmware compilado: contiene las credenciales incorporadas.

La compilación no carga la placa. La preparación no despliega recursos ni actualiza Alexa. El sensor requiere un recipiente no metálico compatible con la fragancia: no atraviesa una lata de aerosol.
