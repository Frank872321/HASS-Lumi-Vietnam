import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from .const import DOMAIN
class LumiConfigFlow(ConfigFlow, domain=DOMAIN):
    async def async_step_user(self, info):
        if info is not None:
            pass  # TODO: process info

        return self.async_show_form(
            step_id="user", data_schema=vol.Schema({vol.Required("host"): str, vol.Required("port"): int})
        )