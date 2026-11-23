#pragma once

#include <Arduino.h>

// XKC-Y23A-NPN con pull-up interno del ESP32; RGB de cátodo común.
// No mide porcentaje ni diagnostica fallos de conexión del sensor.
class LevelIndicator {
 public:
  void begin();
  bool update(uint32_t now);  // true solo cuando cambia el estado filtrado.
  bool ready() const { return ready_; }
  bool low() const { return low_; }
  const char* color() const { return !ready_ ? "off" : low_ ? "orange" : "green"; }

 private:
  bool raw_ = false;
  bool low_ = false;
  bool ready_ = false;
  uint32_t changedAt_ = 0;
};
