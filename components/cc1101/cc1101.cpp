#include "cc1101.h"
#include "esphome/core/log.h"

namespace esphome {
namespace cc1101 {

static const char *const TAG = "cc1101";

int CC1101Component::module_count_ = 0;

void CC1101Component::setup() {
  ESP_LOGCONFIG(TAG, "Setting up CC1101...");

  this->module_number_ = CC1101Component::module_count_++;

  pinMode(this->gdo0_pin_, INPUT);

  // Initialize the CC1101 module
  ELECHOUSE_cc1101.addSpiPin(this->get_clk_pin(), this->get_miso_pin(), this->get_mosi_pin(), this->get_cs_pin(), this->module_number_);
  ELECHOUSE_cc1101.setModul(this->module_number_);
  ELECHOUSE_cc1101.Init();
  ELECHOUSE_cc1101.setRxBW(this->bandwidth_);
  ELECHOUSE_cc1101.setMHZ(this->frequency_);
  ELECHOUSE_cc1101.SetRx();

  ESP_LOGCONFIG(TAG, "CC1101 setup complete");
}

void CC1101Component::dump_config() {
  ESP_LOGCONFIG(TAG, "CC1101:");
  LOG_PIN("  GDO0 Pin: ", this->gdo0_pin_);
  ESP_LOGCONFIG(TAG, "  Bandwidth: %.1f kHz", this->bandwidth_);
  ESP_LOGCONFIG(TAG, "  Frequency: %.1f MHz", this->frequency_);
  ESP_LOGCONFIG(TAG, "  Module Number: %.0f", this->module_number_);
}

void CC1101Component::begin_transmission() {
  ELECHOUSE_cc1101.setModul(this->module_number_);
  ELECHOUSE_cc1101.SetTx();
  pinMode(this->gdo0_pin_, OUTPUT);
}

void CC1101Component::end_transmission() {
  digitalWrite(this->gdo0_pin_, 0);
  pinMode(this->gdo0_pin_, INPUT);
  ELECHOUSE_cc1101.setModul(this->module_number_);
  ELECHOUSE_cc1101.SetRx();
  ELECHOUSE_cc1101.SetRx();  // yes, twice as in original
}

void CC1101Component::set_bandwidth_runtime(float bandwidth) {
  this->bandwidth_ = bandwidth;
  ELECHOUSE_cc1101.setModul(this->module_number_);
  ELECHOUSE_cc1101.setRxBW(bandwidth);
}

void CC1101Component::set_frequency_runtime(float frequency) {
  this->frequency_ = frequency;
  ELECHOUSE_cc1101.setModul(this->module_number_);
  ELECHOUSE_cc1101.setMHZ(frequency);
}

int CC1101Component::get_rssi() {
  ELECHOUSE_cc1101.setModul(this->module_number_);
  return ELECHOUSE_cc1101.getRssi();
}

void CC1101Sensor::update() {
  if (this->rssi_enabled_) {
    int rssi = this->parent_->get_rssi();
    if (rssi != this->last_rssi_) {
      this->publish_state(rssi);
      this->last_rssi_ = rssi;
    }
  }
}

// Global function to get CC1101 component instance
CC1101Component *get_cc1101(CC1101Component *component) {
  return component;
}

}  // namespace cc1101
}  // namespace esphome
