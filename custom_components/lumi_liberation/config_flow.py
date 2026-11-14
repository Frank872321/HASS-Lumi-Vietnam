from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from .const import DOMAIN


class LumiConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Lumi Vietnam."""

    VERSION = 1

    def __init__(self) -> None:
        self.discovered_host: str | None = None
        self.discovered_port: int | None = None
        self.discovered_name: str | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            host = user_input["host"]
            port = user_input["port"]

            await self.async_set_unique_id(host)
            self._abort_if_unique_id_configured(
                updates={"host": host, "port": port},
                reload_on_update=False,
            )

            return self.async_create_entry(
                title=f"Lumi Gateway ({host})",
                data={"host": host, "port": port},
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("host"): str,
                    vol.Required("port", default=1883): int,
                }
            ),
        )

    async def async_step_zeroconf(
        self, discovery_info: ZeroconfServiceInfo
    ) -> ConfigFlowResult:
        host = discovery_info.host
        port = discovery_info.port or 1883
        properties = discovery_info.properties

        unique_id = properties.get("mac", discovery_info.hostname)
        await self.async_set_unique_id(unique_id)

        # If we already know this gateway, update its stored IP/port and bail.
        # The update listener in __init__.py reloads the entry, which spins up
        # a new paho client pointed at the new address.
        self._abort_if_unique_id_configured(
            updates={"host": host, "port": port},
            reload_on_update=False,
        )

        self.discovered_host = host
        self.discovered_port = port
        self.discovered_name = discovery_info.name

        self.context["title_placeholders"] = {"name": self.discovered_name}
        return await self.async_step_discovery_confirm()

    async def async_step_discovery_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(
                title=self.discovered_name
                or f"Lumi Gateway ({self.discovered_host})",
                data={
                    "host": self.discovered_host,
                    "port": self.discovered_port,
                },
            )

        self._set_confirm_only()
        return self.async_show_form(
            step_id="discovery_confirm",
            description_placeholders={
                "name": self.discovered_name or "Lumi Gateway",
                "host": self.discovered_host,
            },
        )