from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN
from .mira.sensors.temp_sensor import SoakStationTempSensor
from .mira.sensors.timer_remaining_sensor import SoakStationTimerRemainingSensor
from .mira.sensors.timer_state_sensor import SoakStationTimerStateSensor

async def async_setup_entry(
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        async_add_entities,
) -> None:
    data = config_entry.data
    address = data["device_address"]
    device_name = data["device_name"]

    config_data = hass.data[DOMAIN][config_entry.entry_id]["data"]
    meta = hass.data[DOMAIN][config_entry.entry_id]["metadata"]

    sensors = [
        SoakStationTempSensor(hass, config_data, meta, address, device_name, "target_temp", "Target Temperature"),
        SoakStationTempSensor(hass, config_data, meta, address, device_name, "actual_temp", "Actual Temperature"),
        SoakStationTimerStateSensor(hass, config_data, meta, address, device_name),
        SoakStationTimerRemainingSensor(hass, config_data, meta, address, device_name),
    ]
    async_add_entities(sensors)
