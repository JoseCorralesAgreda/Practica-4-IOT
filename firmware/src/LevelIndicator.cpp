#include "LevelIndicator.h"

namespace {
constexpr int kLevelPin = 26;
constexpr int kRedPin = 21;
constexpr int kGreenPin = 22;
constexpr int kBluePin = 23;
// ESP32Servo asigna desde el canal 0; reservar 12..14 evita compartir su timer.
constexpr int kRedChannel = 12;
constexpr int kGreenChannel = 13;
constexpr int kBlueChannel = 14;
constexpr uint32_t kStableMs = 500;
// Verificar polaridad con líquido real al montar. LOW significa líquido detectado.
constexpr int kLiquidDetected = LOW;
}  // namespace

void LevelIndicator::begin() {
  // OUT NPN de colector abierto: usar solo el pull-up interno hacia 3.3 V.
  // No requiere resistencia externa; comprobar que OUT no incorpora 5 V.
  pinMode(kLevelPin, INPUT_PULLUP);
  ledcSetup(kRedChannel, 5000, 8);
  ledcSetup(kGreenChannel, 5000, 8);
  ledcSetup(kBlueChannel, 5000, 8);
  ledcAttachPin(kRedPin, kRedChannel);
  ledcAttachPin(kGreenPin, kGreenChannel);
  ledcAttachPin(kBluePin, kBlueChannel);
  ledcWrite(kRedChannel, 0);
  ledcWrite(kGreenChannel, 0);
  ledcWrite(kBlueChannel, 0);
  raw_ = digitalRead(kLevelPin) != kLiquidDetected;
  changedAt_ = millis();
}

bool LevelIndicator::update(uint32_t now) {
  const bool reading = digitalRead(kLevelPin) != kLiquidDetected;
  if (reading != raw_) {
    raw_ = reading;
    changedAt_ = now;
  }
  if (now - changedAt_ < kStableMs || (ready_ && low_ == raw_)) return false;
  low_ = raw_;
  ready_ = true;
  // Nivel bajo: solo rojo; nivel suficiente: solo verde.
  ledcWrite(kRedChannel, low_ ? 255 : 0);
  ledcWrite(kGreenChannel, low_ ? 0 : 255);
  ledcWrite(kBlueChannel, 0);
  return true;
}
