#include "cc1101.h"
#include "esphome/core/log.h"

namespace esphome {
namespace cc1101 {

static const char *const TAG = "cc1101";

int CC1101Component::module_count_ = 0;

void CC1101Component::setup() {
  ESP_LOGCONFIG(TAG, "Setting up CC1101...");

  this->module_number_ = CC1101Component::module_count_++;

  this->gdo0_pin_->setup();
  this->gdo0_pin_->pin_mode(gpio::FLAG_INPUT);

  // Initialize the CC1101 module
  // Use the SPI pins from the component configuration
  ELECHOUSE_cc1101.addSpiPin(
    this->clk_pin_->get_pin(),
    this->miso_pin_->get_pin(),
    this->mosi_pin_->get_pin(),
    this->cs_pin_->get_pin(),
    this->module_number_
  );
  ELECHOUSE_cc1101.setModul(this->module_number_);
  ELECHOUSE_cc1101.Init();
  ELECHOUSE_cc1101.setRxBW(this->bandwidth_);
  ELECHOUSE_cc1101.setMHZ(this->frequency_);
  ELECHOUSE_cc1101.SetRx();

  this->initialized_ = true;
  ESP_LOGCONFIG(TAG, "CC1101 setup complete");
}

void CC1101Component::dump_config() {
  ESP_LOGCONFIG(TAG, "CC1101:");
  ESP_LOGCONFIG(TAG, "  GDO0 Pin: GPIO%d", this->gdo0_pin_->get_pin());
  ESP_LOGCONFIG(TAG, "  Bandwidth: %.1f kHz", this->bandwidth_);
  ESP_LOGCONFIG(TAG, "  Frequency: %.1f MHz", this->frequency_);
  ESP_LOGCONFIG(TAG, "  Module Number: %.0f", this->module_number_);
}

void CC1101Component::begin_transmission() {
  if (!this->initialized_) {
    ESP_LOGW(TAG, "CC1101 not initialized yet, skipping transmission");
    return;
  }

  ESP_LOGD(TAG, "Beginning transmission...");
  ELECHOUSE_cc1101.setModul(this->module_number_);
  ELECHOUSE_cc1101.SetTx();
  this->gdo0_pin_->pin_mode(gpio::FLAG_OUTPUT);
#ifdef USE_ESP32
  // Critical: Reinitialize remote transmitter for each transmission
  if (this->remote_transmitter_ != nullptr) {
    this->remote_transmitter_->setup();
  }
#endif
  ESP_LOGD(TAG, "Transmission setup complete");
}

void CC1101Component::end_transmission() {
  ESP_LOGD(TAG, "Ending transmission...");
  this->gdo0_pin_->digital_write(false);
  this->gdo0_pin_->pin_mode(gpio::FLAG_INPUT);
  ELECHOUSE_cc1101.setModul(this->module_number_);
  ELECHOUSE_cc1101.SetRx();
  ELECHOUSE_cc1101.SetRx();  // yes, twice as in original

  // Additional reset to ensure clean state for next transmission
  ELECHOUSE_cc1101.setModul(this->module_number_);
  ELECHOUSE_cc1101.Init();
  ELECHOUSE_cc1101.setRxBW(this->bandwidth_);
  ELECHOUSE_cc1101.setMHZ(this->frequency_);
  ELECHOUSE_cc1101.SetRx();

  ESP_LOGD(TAG, "Transmission ended, module reset to RX");
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


// Global function to get CC1101 component instance
CC1101Component *get_cc1101(CC1101Component *component) {
  return component;
}

}  // namespace cc1101
}  // namespace esphome
