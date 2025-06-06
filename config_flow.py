"""Configuration flow for Mira Soak Station devices.

This module handles the device discovery and pairing process during
initial setup of the Mira Soak Station integration.
"""

import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv
from homeassistant.components.bluetooth import async_get_scanner

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Configuration schema keys
CONF_DEVICE = "device"
CONF_CLIENT_ID = "client_id"
CONF_CLIENT_SLOT = "client_slot"


class SoakStationConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the configuration flow for Mira Soak Station devices."""

    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        """Handle the initial step of the configuration flow.
        
        This step discovers available Mira devices and handles the pairing process.
        
        Args:
            user_input: User input from the configuration form
            
        Returns:
            FlowResult: The next step in the configuration flow
        """
        from .mira.config_helper import config_flow_pairing

        errors = {}
        mira_devices = {}

        # First step: discover and show available Mira devices
        if user_input is None:
            scanner = async_get_scanner(self.hass)
            devices = await scanner.discover(timeout=5.0)

            # Filter for Mira devices
            for device in devices:
                name = device.name or "Unknown"
                if "Mira" in name:
                    mira_devices[device.address] = name

            if not mira_devices:
                return self.async_abort(reason="no_devices_found")

            self._device_options = mira_devices
            return await self.show_selection_form(errors, mira_devices)

        # Handle device selection and pairing
        device_address = user_input[CONF_DEVICE]
        device_name = self._device_options[device_address]

        try:
            # Attempt to pair with the selected device
            client_id, client_slot = await config_flow_pairing(self.hass, device_address)
        except Exception as e:
            _LOGGER.exception("Failed to pair with Mira device")
            errors["base"] = "pairing_failed"
            return await self.show_selection_form(errors, mira_devices)

        # Create configuration entry on successful pairing
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
        """Display the device selection form.
        
        Args:
            errors: Any errors to display
            mira_devices: Dictionary of discovered Mira devices
            
        Returns:
            FlowResult: The form to display
        """
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_DEVICE): vol.In(mira_devices)
            }),
            errors=errors
        )
