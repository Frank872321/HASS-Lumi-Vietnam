from __future__ import annotations

import json
import logging
import re
from typing import Any

from homeassistant.components import mqtt
from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN, DISCOVERY_SIGNAL

_LOGGER = logging.getLogger(__name__)

# devid looks like: zigbee-84:2E:14:FF:FE:88:23:A8-1
_DEVID_RE = re.compile(r"^(?P<proto>[^-]+)-(?P<mac>[0-9A-Fa-f:]{17,23})-(?P<ep>\d+)$")
_UNIQUE_PREFIX = "lumi_switch_"


def _split_devid(devid: str) -> tuple[str, str, str]:
    m = _DEVID_RE.match(devid)
    if not m:
        return ("unknown", devid, "1")
    return m["proto"], m["mac"], m["ep"]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    known: dict[str, LumiSwitch] = hass.data[DOMAIN].setdefault(entry.entry_id, {})

    @callback
    def _add(devid: str) -> None:
        if devid in known:
            return
        entity = LumiSwitch(devid)
        known[devid] = entity
        async_add_entities([entity])

    # Rehydrate from registry on restart (device list only; state via RestoreEntity)
    registry = er.async_get(hass)
    for ent in er.async_entries_for_config_entry(registry, entry.entry_id):
        if ent.domain != "switch" or not ent.unique_id.startswith(_UNIQUE_PREFIX):
            continue
        _add(ent.unique_id[len(_UNIQUE_PREFIX):])

    entry.async_on_unload(async_dispatcher_connect(hass, DISCOVERY_SIGNAL, _add))


class LumiSwitch(SwitchEntity, RestoreEntity):
    _attr_should_poll = False

    def __init__(self, devid: str) -> None:
        self._devid = devid
        _, self._mac, endpoint = _split_devid(devid)
        self._attr_unique_id = f"{_UNIQUE_PREFIX}{devid}"
        self._attr_name = f"Lumi Switch {self._mac[-5:]}-{endpoint}"
        self._attr_is_on = False

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._mac)},
            name=f"Lumi Hub {self._mac[-5:]}",
            manufacturer="Lumi",
            model="Home Controller",
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last := await self.async_get_last_state()) is not None:
            self._attr_is_on = last.state == "on"
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{DOMAIN}_state_update_{self._devid}",
                self._handle_state_update,
            )
        )

    @callback
    def _handle_state_update(self, new_state: bool) -> None:
        self._attr_is_on = bool(new_state)
        self.async_write_ha_state()

    async def _publish(self, on: bool) -> None:
        payload = {
            "cmd": "set",
            "control_source": {
                "id": "ha-dev",
                "previous_control_reqid": "",
                "type": "app",
            },
            "objects": [
                {
                    "data": [self._devid],
                    "execution": {"command": "OnOff", "params": {"on": on}},
                    "type": "devices",
                }
            ],
            "reqid": "ha-dev",
            "source": "core",
            "timestamp": 0,
        }
        await mqtt.async_publish(
            self.hass, "component/hc-zb/control", json.dumps(payload)
        )
        # Optimistic for now — the HC will echo the real state on
        # component/dnet-relay/in/status and _handle_state_update will correct us.
        self._attr_is_on = on
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._publish(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._publish(False)