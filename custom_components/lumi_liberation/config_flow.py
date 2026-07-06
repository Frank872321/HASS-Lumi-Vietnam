from homeassistant import config_entries
import voluptuous as vol
from . import DOMAIN

class LumiConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        # 1. If the user submitted the form
        if user_input is not None:
            # Create the entry in HA's config database
            return self.async_create_entry(title="Lumi Hub", data=user_input)

        # 2. Define the UI form schema
        schema = vol.Schema({
            vol.Required("host", default="192.168.1.94"): str,
            vol.Required("port", default=1883): int,
        })

        # 3. Show the form to the user
        return self.async_show_form(step_id="user", data_schema=schema)