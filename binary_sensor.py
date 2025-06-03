from __future__ import annotations

import logging
from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary sensors from config entry."""
    data = config_entry.data
    address = data["device_address"]
    client_id = data["client_id"]
    client_slot = data["client_slot"]
    device_name = data["device_name"]

    sensors = [
        SoakStationOutletBinarySensor(hass, device_name, address, client_id, client_slot, outlet_num=1),
        SoakStationOutletBinarySensor(hass, device_name, address, client_id, client_slot, outlet_num=2),
        SoakStationConnectionSensor(hass, device_name, address, client_id, client_slot),
    ]

    async_add_entities(sensors)


class SoakStationOutletBinarySensor(BinarySensorEntity):
    def __init__(self, hass, device_name, address, client_id, client_slot, outlet_num):
        self.hass = hass
        self._address = address
        self._device_name = device_name
        self._client_id = client_id
        self._client_slot = client_slot
        self._outlet_num = outlet_num

        self._attr_name = f"SoakStation Outlet {outlet_num} ({device_name})"
        self._attr_unique_id = f"soakstation_outlet{outlet_num}_{address.replace(':', '')}"
        self._attr_device_class = BinarySensorDeviceClass.RUNNING
        self._attr_icon = "mdi:shower-head"

    async def async_update(self):
        """Update state from Mira device."""
        # is_on = await self.hass.async_add_executor_job(
        #     update_outlet_state_from_device,
        #     self._address,
        #     self._client_id,
        #     self._client_slot,
        #     self._outlet_num
        # )
        self._attr_is_on = True


class SoakStationConnectionSensor(BinarySensorEntity):
    def __init__(self, hass, device_name, address, client_id, client_slot):
        self.hass = hass
        self._address = address
        self._device_name = device_name
        self._client_id = client_id
        self._client_slot = client_slot

        self._attr_name = f"SoakStation Connected ({device_name})"
        self._attr_unique_id = f"soakstation_connection_{address.replace(':', '')}"
        self._attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
        self._attr_icon = "mdi:bluetooth-connect"

    async def async_update(self):
        """Set connection status to True if device is in Bluetooth range."""

        self._attr_is_on = True
