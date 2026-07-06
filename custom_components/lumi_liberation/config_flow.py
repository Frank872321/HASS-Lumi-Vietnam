import voluptuous as vol
from homeassistant import config_entries
from .const import DOMAIN
@config_entries.config_flow_handler(DOMAIN)
class LumiConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Lumi Liberation."""
    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial user step."""
        errors = {}

        if user_input is not None:
            # Here you would typically validate the connection
            # For now, we just save the data provided by the user
            return self.async_create_entry(
                title="Lumi Hub", 
                data=user_input
            )

        # Define the form schema
        data_schema = vol.Schema({
            vol.Required("host", default="192.168.1.94"): str,
            vol.Required("port", default=1883): int,
        })

        return self.async_show_form(
            step_id="user", 
            data_schema=data_schema, 
            errors=errors
        )