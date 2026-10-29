"""Data update coordinator for Mira Soak Station devices.

Owns the BLE connection to one device. It polls the device state, pushes state
the device reports by itself (e.g. someone using the shower's own controls),
reconnects when the connection drops and serialises commands with polls.
Entities become unavailable while the device can't be reached.
"""

import asyncio
import logging
from datetime import timedelta

from bleak.exc import BleakError
from homeassistant.components.bluetooth import (
    BluetoothChange,
    BluetoothServiceInfoBleak,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .mira.helpers.connection import Connection
from .mira.helpers.data_model import SoakStationData, SoakStationMetadata

logger = logging.getLogger(__name__)

# How often to poll the device state
UPDATE_INTERVAL = timedelta(seconds=20)
# How long to wait for the device to answer a request
RESPONSE_TIMEOUT = 5.0
# Temperature to use when turning an outlet on before the device has reported one
DEFAULT_TEMPERATURE = 38.0

# Errors that mean the device couldn't be reached
CONNECTION_ERRORS = (BleakError, ConnectionError, asyncio.TimeoutError, OSError)


class SoakStationCoordinator(DataUpdateCoordinator[SoakStationData]):
    """Keeps the connection to a Mira device alive and its state up to date.

    Attributes:
        connection: BLE connection to the device
        model: Current device state, updated by notifications
        metadata: Device identity and firmware versions
    """

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        connection: Connection,
        model: SoakStationData,
        metadata: SoakStationMetadata,
    ) -> None:
        """Initialize the coordinator.

        Args:
            hass: Home Assistant instance
            config_entry: Configuration entry for the device
            connection: BLE connection to the device
            model: Device state, updated by the connection's notification handler
            metadata: Device metadata, updated by the connection's notification handler
        """
        super().__init__(
            hass,
            logger,
            config_entry=config_entry,
            name=config_entry.title,
            update_interval=UPDATE_INTERVAL,
        )
        self.connection = connection
        self.model = model
        self.metadata = metadata

        self._lock = asyncio.Lock()  # one exchange with the device at a time
        self._busy = False  # a poll or command is waiting for the device
        self._closing = False
        self._metadata_loaded = False
        self._state_received = asyncio.Event()

        model.subscribe(self._handle_model_update)
        connection.set_disconnect_callback(self._handle_disconnect)

    @callback
    def _handle_model_update(self) -> None:
        """Handle new state from the device.

        Wakes a poll or command waiting for an answer; state the device pushes on
        its own goes straight to the entities.
        """
        self._state_received.set()
        if not self._busy:
            self.async_set_updated_data(self.model)

    @callback
    def _handle_disconnect(self) -> None:
        """Reconnect straight away when the connection drops."""
        if self._closing:
            return
        logger.debug("%s: connection dropped, reconnecting", self.name)
        self.config_entry.async_create_background_task(
            self.hass, self.async_request_refresh(), f"{self.name} reconnect"
        )

    @callback
    def handle_advertisement(
        self, service_info: BluetoothServiceInfoBleak, change: BluetoothChange
    ) -> None:
        """Retry promptly when an unreachable device is seen advertising again."""
        if not self.last_update_success and not self._busy and not self._closing:
            self.config_entry.async_create_background_task(
                self.hass, self.async_request_refresh(), f"{self.name} reconnect"
            )

    async def _async_update_data(self) -> SoakStationData:
        """Poll the device state, connecting first if needed.

        Raises:
            UpdateFailed: If the device couldn't be reached or didn't answer
        """
        try:
            await self._exchange(None)
        except CONNECTION_ERRORS as err:
            raise UpdateFailed(f"Couldn't reach {self.name}: {err or type(err).__name__}") from err
        return self.model

    async def async_control_outlets(self, outlet_1: bool, outlet_2: bool) -> None:
        """Turn the outlets on or off, then wait for the device to confirm.

        Args:
            outlet_1: True to run outlet 1
            outlet_2: True to run outlet 2

        Raises:
            HomeAssistantError: If the device couldn't be reached or didn't answer
        """
        temperature = self.model.target_temp or DEFAULT_TEMPERATURE

        async def command() -> None:
            await self.connection.control_outlets(outlet_1, outlet_2, temperature=temperature)

        try:
            await self._exchange(command)
        except CONNECTION_ERRORS as err:
            self.async_set_update_error(err)
            raise HomeAssistantError(f"Couldn't reach {self.name}: {err or type(err).__name__}") from err
        self.async_set_updated_data(self.model)

    async def _exchange(self, command) -> None:
        """Connect if needed, run an optional command, then fetch the device state.

        A connection that stops answering is closed, so the next attempt starts afresh.

        Args:
            command: Optional coroutine function to run before fetching the state
        """
        async with self._lock:
            self._busy = True
            try:
                if not self.connection.is_connected:
                    await self.connection.connect()
                if not self._metadata_loaded:
                    await self._load_metadata()
                if command is not None:
                    await command()
                self._state_received.clear()
                await self.connection.request_device_state()
                await asyncio.wait_for(self._state_received.wait(), RESPONSE_TIMEOUT)
            except CONNECTION_ERRORS:
                await self.connection.disconnect()
                raise
            finally:
                self._busy = False

    async def _load_metadata(self) -> None:
        """Read the device identity and firmware versions, once."""
        info = await self.connection.get_device_info()
        self.metadata.update_device_identity(device_address=self.metadata.device_address, **info)
        await self.connection.request_technical_info()
        if not await self.metadata.wait_for_technical_info(RESPONSE_TIMEOUT):
            logger.debug("%s: no technical info received, firmware versions unknown", self.name)
        self._metadata_loaded = True

    async def async_shutdown(self) -> None:
        """Stop polling and disconnect."""
        self._closing = True
        await super().async_shutdown()
        await self.connection.disconnect()
