import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv
from homeassistant.components.bluetooth import async_get_scanner


from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

CONF_DEVICE = "device"
CONF_CLIENT_ID = "client_id"
CONF_CLIENT_SLOT = "client_slot"


class SoakStationConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        errors = {}

        mira_devices = {}
        # First step: show the list of Mira devices
        if user_input is None:
            scanner = async_get_scanner(self.hass)
            devices = await scanner.discover(timeout=5.0)

            for device in devices:
                name = device.name or "Unknown"
                if "Mira" in name:
                    mira_devices[device.address] = name

            if not mira_devices:
                return self.async_abort(reason="no_devices_found")

            self._device_options = mira_devices

            return await self.show_selection_form(errors, mira_devices)

        # User selected a device by name
        device_name = user_input[CONF_DEVICE]
        device_address = self._device_options[device_name]

        # Pair the client
        try:
            client_id = 1
            client_slot = 1
            pass
            # client_id, client_slot = await self.hass.async_add_executor_job(
            #     pair_client, device_address, device_name
            # )
        except Exception as e:
            _LOGGER.exception("Failed to pair with Mira device")
            errors["base"] = "pairing_failed"
            return self.show_selection_form(errors, mira_devices)

        # Success — store config entry
        return self.async_create_entry(
            title=device_name,
            data={
                "device_name": device_name,
                "device_address": device_address,
                "client_id": client_id,
                "client_slot": client_slot,
            }
        )

    async def show_selection_form(self, errors, mira_devices):
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_DEVICE): vol.In(mira_devices)
            }),
            errors=errors,
            description_placeholders={
                "instruction": "Select shower or bath device to monitor and control"
            },
        )


