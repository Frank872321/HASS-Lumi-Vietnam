from typing import Any
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components.zeroconf import ZeroconfServiceInfo
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN


class LumiConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Lumi Vietnam."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize flow instance variables."""
        self.discovered_host: str | None = None
        self.discovered_port: int | None = None
        self.discovered_name: str | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the manual fallback step when adding the integration via UI."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input["host"]
            port = user_input["port"]

            await self.async_set_unique_id(host)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=f"Lumi Gateway ({host})",
                data={"host": host, "port": port},
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("host"): str,
                    vol.Required("port", default=80): int,
                }
            ),
            errors=errors,
        )

    async def async_step_zeroconf(
        self, discovery_info: ZeroconfServiceInfo
    ) -> FlowResult:
        """Handle zeroconf discovery."""
        host = discovery_info.host
        port = discovery_info.port
        properties = discovery_info.properties
        
        # Use a unique identifier from the device (e.g., MAC or hostname)
        unique_id = properties.get("mac", discovery_info.hostname)
        await self.async_set_unique_id(unique_id)
        
        # Automatically updates the config entry IP/port if it changes in the background
        self._abort_if_unique_id_configured(
            updates={"host": host, "port": port}
        )

        # Store for the confirmation step
        self.discovered_host = host
        self.discovered_port = port
        self.discovered_name = discovery_info.name

        self.context["title_placeholders"] = {"name": self.discovered_name}

        return await self.async_step_discovery_confirm()

    async def async_step_discovery_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirm discovery dialog prompt to the user in the UI."""
        if user_input is not None:
            return self.async_create_entry(
                title=self.discovered_name or f"Lumi Gateway ({self.discovered_host})",
                data={
                    "host": self.discovered_host,
                    "port": self.discovered_port,
                },
            )

        self._set_confirm_only()
        return self.async_show_form(
            step_id="discovery_confirm",
            description_placeholders={
                "name": self.discovered_name,
                "host": self.discovered_host,
            },
        )