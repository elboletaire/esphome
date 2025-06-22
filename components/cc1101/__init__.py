import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import spi
from esphome.const import CONF_ID

DEPENDENCIES = ["spi"]
CODEOWNERS = ["@elboletaire"]

cc1101_ns = cg.esphome_ns.namespace("cc1101")
CC1101Component = cc1101_ns.class_("CC1101Component", cg.Component, spi.SPIDevice)

CONF_GDO0_PIN = "gdo0_pin"
CONF_BANDWIDTH = "bandwidth"
CONF_FREQUENCY = "frequency"

CONFIG_SCHEMA = cv.Schema(
    {
        cv.GenerateID(): cv.declare_id(CC1101Component),
        cv.Required(CONF_GDO0_PIN): cv.int_,
        cv.Optional(CONF_BANDWIDTH, default=200.0): cv.float_,
        cv.Optional(CONF_FREQUENCY, default=868.4): cv.float_,
    }
).extend(cv.COMPONENT_SCHEMA).extend(spi.spi_device_schema())


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)
    await spi.register_spi_device(var, config)

    cg.add(var.set_gdo0_pin(config[CONF_GDO0_PIN]))
    cg.add(var.set_bandwidth(config[CONF_BANDWIDTH]))
    cg.add(var.set_frequency(config[CONF_FREQUENCY]))

    cg.add_library("SmartRC-CC1101-Driver-Lib", None)
