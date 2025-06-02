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

        mira_devices = []
        for device in devices:
            if device.name and "Mira" in device.name:
                mira_devices.append((device.address, device.name))

        if not mira_devices:
            errors["base"] = "no_mira_devices"

        schema = vol.Schema({
            vol.Required("devices"): cv.multi_select({
                addr: name for addr, name in mira_devices
            })
        })

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            description_placeholders={
                "instruction": "Select shower or bath device(s) to monitor and control"
            },
            errors=errors
        )
