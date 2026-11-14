import json
from homeassistant.components import mqtt
from homeassistant.components.switch import SwitchEntity
from .const import DOMAIN, DISCOVERY_SIGNAL
import logging
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers import entity_registry as er

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the switch platform."""
    registry = er.async_get(hass)
    
    # 1. Load existing entities already registered to this config entry on restart
    stored_entities = er.async_entries_for_config_entry(registry, entry.entry_id)
    
    entities_to_add = []
    for ent in stored_entities:
        # Re-instantiate your switch object from the stored data
        # This brings the entity "alive" in HA immediately on boot
        dev_hash = ent.unique_id.split('_')[-1]
        new_switch = LumiSwitch(hass, ent.original_name or f"Lumi Switch {dev_hash}", dev_hash)
        entities_to_add.append(new_switch)
        
    if entities_to_add:
        async_add_entities(entities_to_add, True)

    @callback
    def add_new_switch(dev_hash):
        """Helper to instantiate and add a newly discovered switch at runtime."""
        new_switch = LumiSwitch(hass, f"Lumi Switch {dev_hash}", dev_hash)
        async_add_entities([new_switch], True)

    # 2. Listen for NEW devices discovered during runtime via dispatcher signal
    async_dispatcher_connect(hass, DISCOVERY_SIGNAL, add_new_switch)

    return True


class LumiSwitch(SwitchEntity):
    def __init__(self, hass, name, devid):
        self.hass = hass
        self._attr_name = name
        # IMPORTANT: This unique_id must NEVER change or you'll get duplicate entities
        self._attr_unique_id = f"lumi_switch_{devid}" 
        self._devid = devid
        self._attr_is_on = False

    @property
    def device_info(self):
        """Link to parent device (The Hub Box)"""
        # Split MAC from the endpoint ID safely
        parts = self._devid.split("-")
        mac = "-".join(parts[:-1]) if len(parts) > 1 else self._devid
        return {
            "identifiers": {(DOMAIN, mac)},
            "name": f"Lumi Hub {mac[-4:] if len(mac) >= 4 else mac}",
            "manufacturer": "Lumi",
        }

    async def async_turn_on(self, **kwargs):
        # Your reverse-engineered command payload
        payload = {
            "cmd": "set",
            "control_source": {"id": "ha-dev", "type": "app"},
            "objects": [{"data": [self._devid], "execution": {"command": "OnOff", "params": {"on": True}}, "type": "devices"}],
            "reqid": "ha-dev",
            "source": "core",
            "timestamp": 0,
        }
        await mqtt.async_publish(self.hass, "component/hc-zb/control", json.dumps(payload))
        self._attr_is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        payload = {
            "cmd": "set",
            "control_source": {"id": "ha-dev", "type": "app"},
            "objects": [{"data": [self._devid], "execution": {"command": "OnOff", "params": {"on": False}}, "type": "devices"}],
            "reqid": "ha-dev",
            "source": "core",
            "timestamp": 0,
        }
        await mqtt.async_publish(self.hass, "component/hc-zb/control", json.dumps(payload))
        self._attr_is_on = False
        self.async_write_ha_state()

    async def async_added_to_hass(self):
        """Register the listener for state updates from MQTT dispatcher."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, 
                f"{DOMAIN}_state_update_{self._devid}", 
                self._handle_state_update
            )
        )

    @callback
    def _handle_state_update(self, new_state):
        """Update state when the central dispatcher signals us."""
        _LOGGER.debug("Switch %s received update: %s", self._devid, new_state)
        self._attr_is_on = bool(new_state)
        self.async_write_ha_state()