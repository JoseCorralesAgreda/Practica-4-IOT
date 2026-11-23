#pragma once

#include <Arduino.h>
#include <ArduinoJson.h>
#include <PubSubClient.h>
#include <array>

// Cola RAM acotada. La confirmación es del Shadow, no de DynamoDB.
class TelemetryQueue {
 public:
  void begin();
  void push(JsonObject reported);
  void publish(PubSubClient& mqtt, const String& topic, uint32_t now);
  void acknowledge(const char* token);
  uint32_t dropped() const { return dropped_; }
  static uint64_t epochMs();

 private:
  static constexpr size_t kCapacity = 32;
  std::array<String, kCapacity> pending_;
  String bootId_;
  String inFlight_;
  size_t head_ = 0;
  size_t size_ = 0;
  uint32_t sequence_ = 0;
  uint32_t dropped_ = 0;
  uint32_t lastSend_ = 0;
};
