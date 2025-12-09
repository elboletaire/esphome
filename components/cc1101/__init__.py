import esphome.codegen as cg
import esphome.config_validation as cv
from esphome import pins
from esphome.components import remote_transmitter
from esphome.const import (
    CONF_CLK_PIN,
    CONF_CS_PIN,
    CONF_ID,
    CONF_MISO_PIN,
    CONF_MOSI_PIN,
)

CODEOWNERS = ["@elboletaire"]

cc1101_ns = cg.esphome_ns.namespace("cc1101")
CC1101Component = cc1101_ns.class_("CC1101Component", cg.Component)

CONF_GDO0_PIN = "gdo0_pin"
CONF_BANDWIDTH = "bandwidth"
CONF_FREQUENCY = "frequency"
CONF_REMOTE_TRANSMITTER_ID = "remote_transmitter_id"

CONFIG_SCHEMA = cv.Schema(
    {
        cv.GenerateID(): cv.declare_id(CC1101Component),
        cv.Required(CONF_CLK_PIN): pins.internal_gpio_output_pin_schema,
        cv.Required(CONF_MISO_PIN): pins.internal_gpio_input_pin_schema,
        cv.Required(CONF_MOSI_PIN): pins.internal_gpio_output_pin_schema,
        cv.Required(CONF_CS_PIN): pins.internal_gpio_output_pin_schema,
        cv.Required(CONF_GDO0_PIN): pins.internal_gpio_output_pin_schema,
        cv.Optional(CONF_BANDWIDTH, default=200.0): cv.float_,
        cv.Optional(CONF_FREQUENCY, default=868.4): cv.float_,
        cv.Optional(CONF_REMOTE_TRANSMITTER_ID): cv.use_id(remote_transmitter.RemoteTransmitterComponent),
    }
).extend(cv.COMPONENT_SCHEMA)


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)

    clk_pin = await cg.gpio_pin_expression(config[CONF_CLK_PIN])
    cg.add(var.set_clk_pin(clk_pin))

    miso_pin = await cg.gpio_pin_expression(config[CONF_MISO_PIN])
    cg.add(var.set_miso_pin(miso_pin))

    mosi_pin = await cg.gpio_pin_expression(config[CONF_MOSI_PIN])
    cg.add(var.set_mosi_pin(mosi_pin))

    cs_pin = await cg.gpio_pin_expression(config[CONF_CS_PIN])
    cg.add(var.set_cs_pin(cs_pin))

    gdo0_pin = await cg.gpio_pin_expression(config[CONF_GDO0_PIN])
    cg.add(var.set_gdo0_pin(gdo0_pin))

    cg.add(var.set_bandwidth(config[CONF_BANDWIDTH]))
    cg.add(var.set_frequency(config[CONF_FREQUENCY]))

    if CONF_REMOTE_TRANSMITTER_ID in config:
        transmitter = await cg.get_variable(config[CONF_REMOTE_TRANSMITTER_ID])
        cg.add(var.set_remote_transmitter(transmitter))

    # Add required libraries for vendored ELECHOUSE library
    cg.add_library("SPI", None)
