import logging
import voluptuous as vol
from .const import DOMAIN

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv
from homeassistant.components.bluetooth import async_get_scanner

_LOGGER = logging.getLogger(__name__)

CONF_DEVICE = "device"
CONF_CLIENT_ID = "client_id"
CONF_CLIENT_SLOT = "client_slot"


class SoakStationConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:

        from .mira.config_helper import config_flow_pairing

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
                return self.async_abort(reason="no_devices_found") # type: ignore

            self._device_options = mira_devices

            return await self.show_selection_form(errors, mira_devices) # type: ignore

        # User selected a device by name
        device_address = user_input[CONF_DEVICE]
        device_name = self._device_options[device_address]

        # Pair the client
        try:
            client_id, client_slot = await config_flow_pairing (self.hass, device_address)
        except Exception as e:
            _LOGGER.exception("Failed to pair with Mira device")
            errors["base"] = "pairing_failed"
            return await self.show_selection_form(errors, mira_devices) # type: ignore

        # Success — store config entry

        return self.async_create_entry( # type: ignore
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
            errors=errors
        )


