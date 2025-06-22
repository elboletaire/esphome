#pragma once

#include "esphome/core/component.h"
#include "esphome/components/spi/spi.h"
#include "esphome/components/remote_transmitter/remote_transmitter.h"
#include <ELECHOUSE_CC1101_SRC_DRV.h>

namespace esphome {
namespace cc1101 {

class CC1101Component : public Component, public spi::SPIDevice<spi::BIT_ORDER_MSB_FIRST, spi::CLOCK_POLARITY_LOW, spi::CLOCK_PHASE_LEADING, spi::DATA_RATE_4MHZ> {
 public:
  void setup() override;
  void dump_config() override;
  float get_setup_priority() const override { return setup_priority::DATA; }

  void set_gdo0_pin(int pin) { this->gdo0_pin_ = pin; }
  void set_bandwidth(float bandwidth) { this->bandwidth_ = bandwidth; }
  void set_frequency(float frequency) { this->frequency_ = frequency; }
  void set_remote_transmitter(remote_transmitter::RemoteTransmitterComponent *transmitter) { this->remote_transmitter_ = transmitter; }

  void begin_transmission();
  void end_transmission();
  void set_bandwidth_runtime(float bandwidth);
  void set_frequency_runtime(float frequency);

  int get_rssi();

 protected:
  int gdo0_pin_;
  float bandwidth_;
  float frequency_;
  float module_number_;
  static int module_count_;
  remote_transmitter::RemoteTransmitterComponent *remote_transmitter_{nullptr};
};


// Global function to get CC1101 component instance
CC1101Component *get_cc1101(CC1101Component *component);

}  // namespace cc1101
}  // namespace esphome
