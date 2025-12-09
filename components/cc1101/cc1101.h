#pragma once

#include "esphome/core/component.h"
#include "esphome/core/gpio.h"
#include "esphome/components/remote_transmitter/remote_transmitter.h"
#include "ELECHOUSE_CC1101_SRC_DRV.h"

namespace esphome {
namespace cc1101 {

class CC1101Component : public Component {
 public:
  void setup() override;
  void dump_config() override;
  float get_setup_priority() const override { return setup_priority::DATA; }

  void set_clk_pin(InternalGPIOPin *pin) { this->clk_pin_ = pin; }
  void set_miso_pin(InternalGPIOPin *pin) { this->miso_pin_ = pin; }
  void set_mosi_pin(InternalGPIOPin *pin) { this->mosi_pin_ = pin; }
  void set_cs_pin(InternalGPIOPin *pin) { this->cs_pin_ = pin; }
  void set_gdo0_pin(InternalGPIOPin *pin) { this->gdo0_pin_ = pin; }
  void set_bandwidth(float bandwidth) { this->bandwidth_ = bandwidth; }
  void set_frequency(float frequency) { this->frequency_ = frequency; }
  void set_remote_transmitter(remote_transmitter::RemoteTransmitterComponent *transmitter) { this->remote_transmitter_ = transmitter; }

  void begin_transmission();
  void end_transmission();
  void set_bandwidth_runtime(float bandwidth);
  void set_frequency_runtime(float frequency);

  int get_rssi();

 protected:
  InternalGPIOPin *clk_pin_{nullptr};
  InternalGPIOPin *miso_pin_{nullptr};
  InternalGPIOPin *mosi_pin_{nullptr};
  InternalGPIOPin *cs_pin_{nullptr};
  InternalGPIOPin *gdo0_pin_{nullptr};
  float bandwidth_;
  float frequency_;
  float module_number_;
  static int module_count_;
  remote_transmitter::RemoteTransmitterComponent *remote_transmitter_{nullptr};
  bool initialized_{false};
};


// Global function to get CC1101 component instance
CC1101Component *get_cc1101(CC1101Component *component);

}  // namespace cc1101
}  // namespace esphome
