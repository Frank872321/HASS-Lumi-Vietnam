from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from .const import DOMAIN


class LumiConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Lumi Vietnam."""

    VERSION = 1

    def __init__(self) -> None:
        self.discovered_name: str | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manual add - no host/port, HA's MQTT integration owns that."""
        if user_input is not None:
            return self.async_create_entry(title="Lumi Vietnam", data={})

        return self.async_show_form(
            step_id="user",
            data_schema=None,
            description_placeholders={},
        )

    async def async_step_zeroconf(
        self, discovery_info: ZeroconfServiceInfo
    ) -> ConfigFlowResult:
        properties = discovery_info.properties
        unique_id = properties.get("mac", discovery_info.hostname)
        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured()

        self.discovered_name = discovery_info.name
        self.context["title_placeholders"] = {"name": self.discovered_name}
        return await self.async_step_discovery_confirm()

    async def async_step_discovery_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(
                title=self.discovered_name or "Lumi Gateway",
                data={},
            )

        self._set_confirm_only()
        return self.async_show_form(
            step_id="discovery_confirm",
            description_placeholders={
                "name": self.discovered_name or "Lumi Gateway",
            },
        )