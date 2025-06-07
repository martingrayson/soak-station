import logging
import asyncio
from typing import Callable
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Optional

from homeassistant.helpers.device_registry import DeviceInfo

from ... import DOMAIN

_LOGGER = logging.getLogger(__name__)


class TimerState(Enum):
    STOPPED = "stopped"
    PAUSED = "paused"
    RUNNING = "running"


class SoakStationData:
    def __init__(self):
        self.slots = []
        self.client_slot = None
        self.outlet_1_on = None
        self.outlet_2_on = None

        self.target_temp = None
        self.actual_temp = None

        self.timer_state = None
        self.remaining_seconds = None
        self.subscribers: list[Callable[[], None]] = []

    def update_state(
            self,
            *,
            slots=None,
            client_slot=None,
            outlet_1_on=None,
            outlet_2_on=None,
            target_temp=None,
            actual_temp=None,
            timer_state=None,
            remaining_seconds=None
    ):
        # Update each field only if provided (not None)
        if slots is not None:
            self.slots = slots
        if client_slot is not None:
            self.client_slot = client_slot
        if outlet_1_on is not None:
            self.outlet_1_on = outlet_1_on
        if outlet_2_on is not None:
            self.outlet_2_on = outlet_2_on
        if target_temp is not None:
            self.target_temp = target_temp
        if actual_temp is not None:
            self.actual_temp = actual_temp
        if timer_state is not None:
            self.timer_state = timer_state
        if remaining_seconds is not None:
            self.remaining_seconds = remaining_seconds

        # Notify subscribers
        for callback in self.subscribers:
            callback()

    def subscribe(self, callback: Callable[[], None]):
        self.subscribers.append(callback)


class Preset:
    def __init__(self, slot: int, target_temp: float, duration_seconds: int, outlet_enabled: list[bool], name: str):
        self.slot = slot
        self.target_temp = target_temp
        self.duration_seconds = duration_seconds
        self.outlet_enabled = outlet_enabled
        self.name = name

class SoakStationMetadata:
    def __init__(self):
        self.valve_sw_version: Optional[str] = None
        self.ui_sw_version: Optional[str] = None
        self.bt_sw_version: Optional[str] = None

        self.nickname: Optional[str] = None
        self.client_name: Optional[str] = None

        # Device Info
        self.name: Optional[str] = None
        self.manufacturer: Optional[str] = None
        self.model: Optional[str] = None
        self.device_address: Optional[str] = None
        self.serial_number: Optional[str] = ""

        # Presets
        self.presets: Dict[int, Preset] = {}

        # Outlet settings
        self.outlet_flag: Optional[int] = None
        self.min_duration_seconds: Optional[int] = None
        self.max_temperature: Optional[float] = None
        self.min_temperature: Optional[float] = None

        # Device settings
        self.outlet_enabled: Optional[list[bool]] = None
        self.default_preset_slot: Optional[int] = None
        self.controller_settings: Optional[list[bool]] = None

        self._technical_info_event = asyncio.Event()

    def get_device_info(self) -> DeviceInfo:
        return DeviceInfo(
            sw_version=f"valve:{self.valve_sw_version} bt:{self.bt_sw_version} ui:{self.ui_sw_version}",
            suggested_area="Bathroom",
            serial_number=self.serial_number,
            name=self.name,
            model=self.model,
            manufacturer=self.manufacturer,
            identifiers={(DOMAIN, self.device_address)},
        )

    def update_from_technical_info(self, valve_sw_version, ui_sw_version, bt_sw_version):
        self.valve_sw_version = valve_sw_version
        self.ui_sw_version = ui_sw_version
        self.bt_sw_version = bt_sw_version
        self._technical_info_event.set()  # signal completion

    def update_nickname(self, name: str):
        self.nickname = name

    def update_client_name(self, name: str):
        self.client_name = name

    def update_device_identity(self, name: str, manufacturer: str, model: str, device_address: str):
        self.name = name
        self.manufacturer = manufacturer
        self.model = model
        self.device_address = device_address

    def update_preset(self, slot: int, target_temp: float, duration: int, outlets: list[bool], name: str):
        self.presets[slot] = Preset(
            slot=slot,
            target_temp=target_temp,
            duration_seconds=duration,
            outlet_enabled=outlets,
            name=name
        )

    def update_outlet_settings(self, outlet_flag: int, min_duration_seconds: int, max_temperature: float, min_temperature: float):
        self.outlet_flag = outlet_flag
        self.min_duration_seconds = min_duration_seconds
        self.max_temperature = max_temperature
        self.min_temperature = min_temperature

    def update_device_settings(self, outlet_enabled: list[bool], default_preset_slot: int, controller_settings: list[bool]):
        self.outlet_enabled = outlet_enabled
        self.default_preset_slot = default_preset_slot
        self.controller_settings = controller_settings

    async def wait_for_technical_info(self):
        await self._technical_info_event.wait()