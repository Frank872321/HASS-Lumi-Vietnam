import json
from homeassistant.components import mqtt
from homeassistant.components.switch import SwitchEntity
from . import DOMAIN
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import (
    async_dispatcher_connect, 
    dispatcher_send
)
async def async_setup_entry(hass, config_entry, async_add_entities):
    # Here you pass your hardcoded list of switches
    async_add_entities([
        LumiSwitch(hass, "Kitchen Light", "zigbee-84:2E:14:FF:FE:88:23:A8-1")
    ])

class LumiSwitch(SwitchEntity):
    def __init__(self, hass, name, devid):
        self.hass = hass
        self._attr_name = name
        self._attr_unique_id = f"lumi_switch_{devid}"
        self._devid = devid
        self._attr_is_on = False

    async def async_turn_on(self, **kwargs):
        # Your reverse-engineered command payload
        payload = {
            "cmd": "set",
            "control_source": {"id": "ha-dev", "type": "app"},
            "objects": [{"data": [self._devid], "execution": {"command": "OnOff", "params": {"on": "true"}}, "type":"devices"}],
            "reqid": "ha-dev",
            "source":"core",
            "timestamp": 0,
        }
        await mqtt.async_publish(self.hass, "component/hc-zb/control", json.dumps(payload))
        self._attr_is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        payload = {
            "cmd": "set",
            "control_source": {"id": "ha-dev", "type": "app"},
            "objects": [{"data": [self._devid], "execution": {"command": "OnOff", "params": {"on": "false"}}, "type":"devices"}],
            "reqid": "ha-dev",
            "source":"core",
            "timestamp": 0,
        }
        await mqtt.async_publish(self.hass, "component/hc-zb/control", json.dumps(payload))
        
        self._attr_is_on = False
        self.async_write_ha_state()