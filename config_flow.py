import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.components.bluetooth import async_get_scanner
import homeassistant.helpers.config_validation as cv

DOMAIN = "soakstation"

class SoakStationConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            return self.async_create_entry(title="SoakStation", data=user_input)

        # Discover nearby Bluetooth devices
        scanner = async_get_scanner(self.hass)
        devices = await scanner.discover(timeout=5.0)

        # Build a list of device choices
        choices = {
            device.address: f"{device.name or 'Unknown'} ({device.address})"
            for device in devices
        }

        schema = vol.Schema({
            vol.Required("devices"): cv.multi_select(choices)
        })

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            description_placeholders={
                "instruction": "Select shower or bath device(s) to monitor and control"
            },
            errors=errors
        )
