import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import sensor
from esphome.const import (
    CONF_ID,
    DEVICE_CLASS_SIGNAL_STRENGTH,
    STATE_CLASS_MEASUREMENT,
    UNIT_DECIBEL_MILLIWATT,
)
from . import CC1101Component, cc1101_ns

DEPENDENCIES = ["cc1101"]

CC1101Sensor = cc1101_ns.class_("CC1101Sensor", sensor.Sensor, cg.PollingComponent)

CONF_CC1101_ID = "cc1101_id"
CONF_RSSI = "rssi"

CONFIG_SCHEMA = cv.Schema(
    {
        cv.GenerateID(): cv.declare_id(CC1101Sensor),
        cv.GenerateID(CONF_CC1101_ID): cv.use_id(CC1101Component),
        cv.Optional(CONF_RSSI, default=False): cv.boolean,
    }
).extend(cv.polling_component_schema("100ms")).extend(sensor.SENSOR_SCHEMA)


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)
    await sensor.register_sensor(var, config)

    cc1101_component = await cg.get_variable(config[CONF_CC1101_ID])
    cg.add(var.set_cc1101_parent(cc1101_component))
    cg.add(var.set_rssi_enabled(config[CONF_RSSI]))
