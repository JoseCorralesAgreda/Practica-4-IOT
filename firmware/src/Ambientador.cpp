#include "Ambientador.h"
#include <Arduino.h>
#include <ArduinoJson.h>
#include <ESP32Servo.h>
#include <Preferences.h>
#include <PubSubClient.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <time.h>
#include "secrets.h"

// ESP32 clásico. Confirmar placa y calibrar sin conectar una carga mecánica.
constexpr int PIR_PIN = 27;
constexpr int SERVO_PIN = 18;
constexpr int STATUS_LED_PIN = LED_BUILTIN;
constexpr int REST_ANGLE = 0;
constexpr int PRESS_ANGLE = 180;
constexpr uint32_t SERVO_PHASE_MS = 700;
constexpr uint32_t PIR_WARMUP_MS = 60000;
constexpr uint32_t REPORT_MS = 60000;
constexpr uint32_t RETRY_MS = 5000;

Ambientador::Ambientador() : mqtt(tls) {}

void Ambientador::begin() {
    Serial.begin(115200);
    pinMode(PIR_PIN, INPUT);
    pinMode(STATUS_LED_PIN, OUTPUT);
    digitalWrite(STATUS_LED_PIN, LOW);
    storageReady = preferences.begin("ambientador", false);
    lastActivation = preferences.getString("activation", "");
    automatic = preferences.getBool("automatic", false);
    cooldownSeconds = preferences.getUInt("cooldown", 300);
    if (cooldownSeconds < 5 || cooldownSeconds > 86400) cooldownSeconds = 300;
    telemetry.begin();
    servo.setPeriodHertz(50);
    servo.attach(SERVO_PIN, 500, 2400);
    servo.write(REST_ANGLE);
    level.begin();
    Serial.printf("Servo: angulo ordenado=%d grados (reposo); LED apagado\n", REST_ANGLE);
    topic = String("$aws/things/") + THING_NAME + "/shadow";
    tls.setCACert(ROOT_CA);
    tls.setCertificate(DEVICE_CERT);
    tls.setPrivateKey(PRIVATE_KEY);
    tls.setHandshakeTimeout(3);
    mqtt.setServer(IOT_ENDPOINT, 8883);
    mqtt.setBufferSize(8192);
    mqtt.setSocketTimeout(2);
    mqtt.setCallback([this](char* name, byte* payload, unsigned int length) {
      onMessage(String(name), payload, length);
    });
    WiFi.mode(WIFI_STA);
    WiFi.setAutoReconnect(true);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    configTime(0, 0, "pool.ntp.org", "time.google.com");
    Serial.println("Inicio; PIR en estabilización durante 60 s.");
  }

void Ambientador::tick() {
    uint32_t now = millis();
    updateServo(now);
    const String previousColor = level.color();
    if (level.update(now)) capture("rgb", previousColor.c_str(), level.color());
    updateSensor(now);
    if ((dirty && now - lastReport >= 2000) || now - lastReport >= REPORT_MS) report(now);
    // No iniciar conexiones TLS bloqueantes durante un ciclo mecánico.
    if (phase == "idle") connect(now);
    // Durante el ciclo, evitar también lecturas MQTT potencialmente bloqueantes.
    if (mqtt.connected() && phase == "idle") {
      mqtt.loop();
      if (!synchronized && now - lastGet >= RETRY_MS) requestShadow();
      // Un callback MQTT puede haber iniciado un ciclo durante loop().
      if (synchronized && phase == "idle") telemetry.publish(mqtt, topic, now);
    }
    delay(5);
  }

void Ambientador::connect(uint32_t now) {
    if (mqtt.connected()) return;
    synchronized = false;
    if (now - lastConnect < RETRY_MS) return;
    lastConnect = now;
    if (WiFi.status() != WL_CONNECTED) {
      WiFi.reconnect();
      return;
    }
    // Validar fechas del certificado TLS requiere reloj sincronizado.
    if (time(nullptr) < 1700000000) return;
    if (!mqtt.connect(THING_NAME)) {
      Serial.printf("MQTT no conectado: %d\n", mqtt.state());
      return;
    }
    bool subscribed = true;
    const char* suffixes[] = {"/get/accepted", "/get/rejected", "/update/delta", "/update/accepted", "/update/rejected"};
    for (const char* suffix : suffixes) {
      if (!mqtt.subscribe((topic + suffix).c_str(), 1)) subscribed = false;
    }
    if (!subscribed) {
      mqtt.disconnect();
      return;
    }
    // Una nueva sesión acepta la versión vigente, incluso si se recreó el Shadow.
    lastVersion = 0;
    requestShadow();
    Serial.println("MQTT conectado; solicitando desired pendiente.");
  }

void Ambientador::requestShadow() {
    mqtt.publish((topic + "/get").c_str(), "{}");
    lastGet = millis();
  }

void Ambientador::onMessage(const String& name, byte* payload, unsigned int length) {
    // Documento en heap para no consumir la pequeña pila de loopTask.
    DynamicJsonDocument document(16384);
    if (deserializeJson(document, payload, length)) {
      Serial.println("Shadow JSON inválido o demasiado grande.");
      return;
    }
    if (name.endsWith("/get/rejected")) {
      if (document["code"] == 404) {
        synchronized = true;
        dirty = true;
      } else {
        Serial.printf("GET Shadow rechazado: %d\n", document["code"].as<int>());
      }
      return;
    }
    if (name.endsWith("/update/rejected")) {
      Serial.printf("Reporte rechazado: %d\n", document["code"].as<int>());
      dirty = true;
      return;
    }
    if (name.endsWith("/update/accepted")) {
      telemetry.acknowledge(document["clientToken"] | "");
      if (document["state"]["reported"].is<JsonObject>()) {
        Serial.println("Shadow: actualizacion de reported aceptada por AWS.");
      }
      return;
    }
    uint32_t version = document["version"] | 0UL;
    // Se comparan solo versiones de documentos que contienen desired/delta.
    if (version < lastVersion) return;
    lastVersion = version;
    if (name.endsWith("/get/accepted")) {
      synchronized = true;
      applyDesired(document["state"]["desired"]);
      dirty = true;
    } else if (name.endsWith("/update/delta") && synchronized) {
      applyDesired(document["state"]);
    }
  }

void Ambientador::applyDesired(JsonVariantConst desired) {
    if (desired["automatic"].is<bool>()) {
      const bool requested = desired["automatic"].as<bool>();
      if (requested != automatic && storageReady && preferences.putBool("automatic", requested)) {
        automatic = requested;
        dirty = true;
      }
    }
    if (desired["cooldownSeconds"].is<uint32_t>()) {
      const uint32_t requested = desired["cooldownSeconds"].as<uint32_t>();
      if (requested >= 5 && requested <= 86400 && requested != cooldownSeconds &&
          storageReady && preferences.putUInt("cooldown", requested)) {
        cooldownSeconds = requested;
        dirty = true;
      }
    }
    if (!desired["activationId"].is<const char*>()) return;
    String id = desired["activationId"].as<String>();
    if (id.isEmpty() || id.length() > 128 || id == lastActivation) return;
    // Un comando recibido mientras el servo se mueve queda en desired.
    // Se vuelve a consultar al terminar el ciclo para no perder ese comando.
    if (phase != "idle") return;
    // Guardar ANTES de mover: evita repetir una dosificación tras reiniciar.
    // Un corte en este intervalo puede perder el movimiento: no es exactly-once.
    if (!storageReady || preferences.putString("activation", id) == 0) {
      Serial.println("No se mueve: no fue posible persistir activationId.");
      return;
    }
    lastActivation = id;
    startCycle(millis(), "voz");
  }

void Ambientador::updateSensor(uint32_t now) {
    // Diagnostico sin filtrar: registrar el nivel observado incluso al arrancar.
    // Son muestras del loop, no una captura de todos los pulsos electricos.
    bool reading = digitalRead(PIR_PIN) == HIGH;
    if (!pirRawInitialized || reading != pirRaw || now - lastPirLog >= REPORT_MS) {
      Serial.printf("PIR t=%lu ms GPIO%d=%s listo=%d servo=%s automatico=%d\n",
                    static_cast<unsigned long>(now), PIR_PIN, reading ? "HIGH" : "LOW",
                    (pirReady || now >= PIR_WARMUP_MS) ? 1 : 0,
                    phase.c_str(), automatic ? 1 : 0);
      lastPirLog = now;
    }
    pirRawInitialized = true;
    pirRaw = reading;
    if (!pirReady && now >= PIR_WARMUP_MS) {
      pirReady = true;
      // No considerar el nivel inicial como un flanco de detección nuevo.
      presence = reading;
      dirty = true;
    }
    if (!pirReady) return;
    if (reading == presence) return;
    presence = reading;
    dirty = true;
    bool cooldownElapsed = !activatedBefore || now - lastCycle >= cooldownSeconds * 1000UL;
    if (presence && automatic && phase == "idle" && cooldownElapsed) {
      startCycle(now, "edge");
    }
  }

void Ambientador::startCycle(uint32_t now, const char* origin) {
    cycleOrigin = origin;
    digitalWrite(STATUS_LED_PIN, HIGH);
    servo.write(PRESS_ANGLE);
    Serial.printf("Servo: angulo ordenado=%d grados (presion); LED encendido\n", PRESS_ANGLE);
    phase = "pressing";
    capture("servo", "idle", "pressing", cycleOrigin);
    phaseStarted = now;
    lastCycle = now;
    activatedBefore = true;
    dirty = true;
    Serial.printf("Inicio ciclo: %lu ms\n", static_cast<unsigned long>(now));
  }

void Ambientador::updateServo(uint32_t now) {
    if (phase == "idle" || now - phaseStarted < SERVO_PHASE_MS) return;
    phaseStarted = now;
    if (phase == "pressing") {
      servo.write(REST_ANGLE);
      Serial.printf("Servo: angulo ordenado=%d grados (retorno); LED encendido\n", REST_ANGLE);
      phase = "returning";
      capture("servo", "pressing", "returning", cycleOrigin);
    } else {
      digitalWrite(STATUS_LED_PIN, LOW);
      phase = "idle";
      Serial.printf("Servo: ciclo terminado, angulo ordenado=%d grados; LED apagado\n", REST_ANGLE);
      cycles++;
      capture("servo", "returning", "idle", cycleOrigin);
      if (mqtt.connected()) requestShadow();
    }
    dirty = true;
  }

void Ambientador::report(uint32_t now) {
    capture();
    lastReport = now;
    dirty = false;
  }

void Ambientador::capture(const char* actuator, const char* from, const char* to, const char* origin) {
    StaticJsonDocument<2048> document;
    JsonObject reported = document.to<JsonObject>();
    reported["presence"] = presence;
    reported["pirReady"] = pirReady;
    reported["automatic"] = automatic;
    reported["cooldownSeconds"] = cooldownSeconds;
    reported["levelReady"] = level.ready();
    reported["lowLevel"] = level.low();
    reported["ledColor"] = level.color();
    reported["activationId"] = lastActivation;
    reported["servoState"] = phase;
    reported["servoAngle"] = phase == "pressing" ? PRESS_ANGLE : REST_ANGLE;
    reported["cyclesSinceBoot"] = cycles;
    reported["uptimeSeconds"] = millis() / 1000;
    reported["sampledAt"] = TelemetryQueue::epochMs() / 1000;
    reported["recordKind"] = actuator ? "event" : "reading";
    reported["event"] = nullptr;  // Elimina el evento anterior del Shadow en una lectura.
    if (actuator) {
      JsonObject event = reported.createNestedObject("event");
      event["actuator"] = actuator;
      event["from"] = from;
      event["to"] = to;
      event["origin"] = origin;
    }
    telemetry.push(reported);
  }
