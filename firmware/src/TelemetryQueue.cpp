#include "TelemetryQueue.h"

#include <esp_system.h>
#include <sys/time.h>

uint64_t TelemetryQueue::epochMs() {
  timeval value{};
  gettimeofday(&value, nullptr);
  if (value.tv_sec < 1700000000) return 0;  // Reloj aún no sincronizado.
  return static_cast<uint64_t>(value.tv_sec) * 1000 + value.tv_usec / 1000;
}

void TelemetryQueue::begin() {
  char id[25];
  snprintf(id, sizeof(id), "%08lx%08lx%08lx", static_cast<unsigned long>(esp_random()),
           static_cast<unsigned long>(esp_random()), static_cast<unsigned long>(esp_random()));
  bootId_ = id;
}

void TelemetryQueue::push(JsonObject reported) {
  if (size_ == kCapacity) {
    ++dropped_;  // Descartar el nuevo registro; conservar el que espera ACK.
    Serial.printf("QUEUE_DROP total=%lu\n", static_cast<unsigned long>(dropped_));
    return;
  }
  const String id = "p4-" + bootId_ + "-" + String(++sequence_);
  reported["schemaVersion"] = 4;
  reported["messageId"] = id;
  reported["observedAtMs"] = epochMs();
  reported["droppedRecords"] = dropped_;
  DynamicJsonDocument document(3072);
  document["clientToken"] = id;
  document["state"]["reported"].set(reported);
  String& payload = pending_[(head_ + size_) % kCapacity];
  payload = "";
  serializeJson(document, payload);
  ++size_;
}

void TelemetryQueue::publish(PubSubClient& mqtt, const String& topic, uint32_t now) {
  if (!size_ || !mqtt.connected()) return;
  if (now - lastSend_ < (inFlight_.isEmpty() ? 250U : 5000U)) return;
  DynamicJsonDocument document(3072);
  String& payload = pending_[head_];
  if (deserializeJson(document, payload)) return;
  if (!document["state"]["reported"].containsKey("publishedAtMs")) {
    document["state"]["reported"]["publishedAtMs"] = epochMs();
    payload = "";
    serializeJson(document, payload);
  }
  inFlight_ = document["clientToken"].as<String>();
  lastSend_ = now;
  if (mqtt.publish((topic + "/update").c_str(),
                   reinterpret_cast<const uint8_t*>(payload.c_str()), payload.length(), false)) {
    Serial.printf("PUBLISH id=%s\n", inFlight_.c_str());
  }
}

void TelemetryQueue::acknowledge(const char* token) {
  if (!size_ || inFlight_.isEmpty() || inFlight_ != token) return;
  Serial.printf("SHADOW_ACK id=%s\n", token);
  pending_[head_] = "";
  head_ = (head_ + 1) % kCapacity;
  --size_;
  inFlight_ = "";
}
