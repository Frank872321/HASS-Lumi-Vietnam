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
    
    # Get all entities already registered to this integration
    stored_entities = er.async_entries_for_config_entry(registry, entry.entry_id)
    
    entities_to_add = []
    for ent in stored_entities:
        # Re-instantiate your switch object from the stored data
        # This brings the entity "alive" in HA immediately on boot
        new_switch = LumiSwitch(hass, ent.original_name, ent.unique_id.split('_')[-1])
        entities_to_add.append(new_switch)
        
    if entities_to_add:
        async_add_entities(entities_to_add, True)
    @callback
    def add_new_switch(dev_hash):
        # We define a helper to instantiate the class
        new_switch = LumiSwitch(hass, f"Lumi Switch {dev_hash}", dev_hash)
        async_add_entities([new_switch], True)

    # 1. Listen for NEW devices discovered during runtime
    async_dispatcher_connect(hass, DISCOVERY_SIGNAL, add_new_switch)

    # 2. LOAD EXISTING DEVICES from registry on restart

    # Get all entities that belong to this config entry
    er_value = er.async_get(hass)
    stored_entries = er.async_entries_for_config_entry(er_value, entry.entry_id)

    # Tell them to exist
    for entity in stored_entities:
        if entity.unique_id and entity.unique_id.startswith("lumi_switch_"):
            dev_hash = entity.unique_id.replace("lumi_switch_", "")
            add_new_switch(dev_hash)
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
        # Split MAC from the endpoint ID
        mac = "-".join(self._devid.split("-")[:-1])
        return {
            "identifiers": {(DOMAIN, mac)},
            "name": f"Lumi Hub {mac[-4:]}",
            "manufacturer": "Lumi",
        }
    async def async_turn_on(self, **kwargs):
        # Your reverse-engineered command payload
        payload = {
            "cmd": "set","control_source": {"id": "ha-dev", "type": "app"},
            "objects": [{"data": [self._devid], "execution": {"command": "OnOff", "params": {"on": True}}, "type":"devices"}],
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
            "objects": [{"data": [self._devid], "execution": {"command": "OnOff", "params": {"on": False}}, "type":"devices"}],
            "reqid": "ha-dev",
            "source":"core",
            "timestamp": 0,
        }
        await mqtt.async_publish(self.hass, "component/hc-zb/control", json.dumps(payload))
        self._attr_is_on = False
    async def async_added_to_hass(self):
        # Register the listener for the specific signal: {DOMAIN}_state_update_{zigbee-84...}
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
        _LOGGER.info(f"DEBUG: Switch {self._devid} received update: {new_state}")
        self._attr_is_on = bool(new_state)
        self.async_write_ha_state()