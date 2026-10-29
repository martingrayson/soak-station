"""Manages Bluetooth Low Energy (BLE) connections to Mira devices.

This module provides the Connection class which handles establishing and maintaining
BLE connections, sending commands, and receiving notifications from Mira devices.
"""

import asyncio
import logging
import struct
from typing import Any, Callable, Dict, Optional, Tuple, Union

from bleak import BleakClient
from bleak.backends.device import BLEDevice
from bleak_retry_connector import BleakClientWithServiceCache, establish_connection

from homeassistant.components.bluetooth import async_ble_device_from_address

from .const import MAGIC_ID, TIMER_RUNNING, OUTLET_RUNNING, OUTLET_STOPPED, TIMER_PAUSED, \
    UUID_DEVICE_NAME, UUID_MANUFACTURER, UUID_MODEL_NUMBER, UUID_READ, UUID_WRITE
from .generic import _get_payload_with_crc, _convert_temperature, _format_bytearray, _split_chunks
from .notifications import Notifications

logger = logging.getLogger(__name__)


class Connection:
    """Manages BLE connections and communication with Mira devices.

    This class handles:
    - Establishing the connection through bleak-retry-connector, which retries,
      caches the GATT services and picks the best Bluetooth adapter or proxy
    - Noticing when the connection drops, and re-subscribing to notifications
      every time it is re-established
    - Sending commands to control device functions
    - Packet validation and reassembly
    - Client pairing and device information retrieval

    Attributes:
        _hass: Home Assistant instance for device discovery
        _address: Bluetooth MAC address of target device
        _client_id: Unique identifier for this client
        _client_slot: Slot number assigned by device
        _client: BleakClient instance for BLE communication
        _notifications: Handler for device notifications, re-subscribed on every connect
        _on_disconnect: Called when the connection drops unexpectedly
        _connect_lock: Stops two callers connecting at the same time
        _partial_payload: Buffer for reassembling split packets
        _reassembly_client_slot: Client slot for packet being reassembled
        _reassembly_payload_length: Expected length of reassembled packet
    """

    def __init__(self, hass: Any, address: str, client_id: Optional[int] = None, client_slot: Optional[int] = None) -> None:
        """Initialize the connection.

        Args:
            hass: Home Assistant instance
            address: Device Bluetooth MAC address
            client_id: Optional client ID to use
            client_slot: Optional client slot to use
        """
        self._hass: Any = hass
        self._address: str = address
        self._client_id: Optional[int] = client_id
        self._client_slot: Optional[int] = client_slot
        self._client: Optional[BleakClient] = None
        self._notifications: Optional[Notifications] = None
        self._on_disconnect: Optional[Callable[[], None]] = None
        self._connect_lock: asyncio.Lock = asyncio.Lock()

        self._response_event: asyncio.Event = asyncio.Event()
        self._response_data: Any = None

        # For packet reassembly
        self._partial_payload: bytearray = bytearray()
        self._reassembly_client_slot: Optional[int] = None
        self._reassembly_payload_length: Optional[int] = None

    def set_client_data(self, client_id: int, client_slot: int) -> None:
        """Set the client ID and slot after pairing.

        Args:
            client_id: Client identifier to use
            client_slot: Slot number assigned by device
        """
        self._client_id = client_id
        self._client_slot = client_slot

    def set_disconnect_callback(self, callback: Optional[Callable[[], None]]) -> None:
        """Set a callback for when the connection drops unexpectedly.

        Args:
            callback: Called (in the event loop) with no arguments
        """
        self._on_disconnect = callback

    @property
    def is_connected(self) -> bool:
        """Whether there is a live connection to the device."""
        return self._client is not None and self._client.is_connected

    async def connect(self, max_attempts: int = 3) -> None:
        """Connect to the device, if not already connected.

        Retries are handled by bleak-retry-connector. When a notification handler
        has been subscribed, notifications are (re-)started on the new connection.

        Args:
            max_attempts: Connection attempts before giving up

        Raises:
            ConnectionError: If no Bluetooth adapter or proxy can see the device
            BleakError: If connecting fails after all attempts
        """
        async with self._connect_lock:
            if self.is_connected:
                return
            device = self._get_ble_device()
            logger.debug(f"Connecting to {self._address}")
            client = await establish_connection(
                BleakClientWithServiceCache,
                device,
                device.name or self._address,
                disconnected_callback=self._handle_disconnected,
                max_attempts=max_attempts,
                ble_device_callback=self._get_ble_device,
            )
            self._client = client
            self._reset_packet_reassembly()
            try:
                if self._notifications is not None:
                    await client.start_notify(UUID_READ, self._handle_raw_notification)
            except Exception:
                self._client = None
                await client.disconnect()
                raise
            logger.debug(f"Connected to {self._address}")

    def _get_ble_device(self) -> BLEDevice:
        """Get the BLE device for the address, from whichever adapter or proxy sees it best.

        Returns:
            BLEDevice: The discovered device

        Raises:
            ConnectionError: If no adapter or proxy can currently see the device
        """
        device = async_ble_device_from_address(self._hass, self._address, connectable=True)
        if not device:
            raise ConnectionError(f"No Bluetooth adapter or proxy can see {self._address}")
        return device

    def _handle_disconnected(self, client: BleakClient) -> None:
        """Handle the connection dropping (bleak disconnected callback)."""
        if client is not self._client:
            return  # an old connection, already replaced or closed deliberately
        logger.debug(f"Disconnected from {self._address}")
        self._client = None
        self._reset_packet_reassembly()
        if self._on_disconnect is not None:
            self._on_disconnect()

    async def reconnect(self) -> None:
        """Disconnect and reconnect to device."""
        logger.debug("Initiating reconnection")
        await self.disconnect()
        await self.connect()

    async def disconnect(self) -> None:
        """Disconnect from device, without calling the disconnect callback."""
        client, self._client = self._client, None
        if client is not None and client.is_connected:
            logger.debug("Disconnecting from device")
            await client.disconnect()

    async def __aenter__(self) -> "Connection":
        """Connect when entering context."""
        await self.connect()
        return self

    async def __aexit__(self, type: Any, value: Any, traceback: Any) -> None:
        """Disconnect when exiting context."""
        await self.disconnect()

    def _validate_packet(self, data: bytearray) -> Tuple[int, int, bytearray]:
        """Validate and parse a received packet.

        Args:
            data: Raw packet data

        Returns:
            tuple: (client_slot, payload_length, payload)

        Raises:
            ValueError: If packet is invalid
        """
        if len(data) < 3:
            raise ValueError(f"Invalid packet length: {len(data)}")

        client_slot = data[0] - 0x40
        payload_length = data[2]
        payload = data[3:]

        if len(payload) != payload_length:
            raise ValueError(f"Expected {payload_length} bytes, got {len(payload)}")

        logger.debug(f"Validated packet - client_slot: {client_slot}, length: {payload_length}")
        return client_slot, payload_length, payload

    def _handle_notification(self, data: bytearray, notifications: Notifications) -> None:
        """Process a notification from the device.

        Args:
            data: Raw notification data
            notifications: Handler for parsed notifications
        """
        try:
            logger.debug(f"Received notification: {_format_bytearray(data)}")
            client_slot, payload_length, payload = self._validate_packet(data)
            notifications.handle_packet(client_slot, payload_length, payload)
        except ValueError as e:
            logger.debug(f"Invalid packet: {e}")

    async def subscribe(self, notifications: Notifications) -> None:
        """Subscribe to device notifications.

        The handler is kept and re-subscribed on every (re)connect.

        Args:
            notifications: Handler for received notifications
        """
        logger.debug("Setting up notification handler")
        self._notifications = notifications
        if self.is_connected:
            await self._client.start_notify(UUID_READ, self._handle_raw_notification)

    def _handle_raw_notification(self, sender: Any, data: bytearray) -> None:
        """Pass a notification chunk to the packet reassembly."""
        if self._notifications is None:
            return
        if len(self._partial_payload) > 0:
            self._handle_partial_packet(data, self._notifications)
        else:
            self._handle_new_packet(data, self._notifications)

    def _handle_partial_packet(self, data: bytearray, notifications: Notifications) -> None:
        """Handle continuation of a split packet.

        Args:
            data: Next chunk of packet data
            notifications: Handler for complete packets
        """
        logger.debug(f"Handling partial packet continuation: {_format_bytearray(data)}")
        self._partial_payload.extend(data)
        payload = self._partial_payload
        client_slot = self._reassembly_client_slot
        payload_length = self._reassembly_payload_length

        self._reset_packet_reassembly()

        if len(payload) >= payload_length:
            if len(payload) == payload_length:
                logger.debug(f"Completed packet reassembly - length: {payload_length}")
                notifications.handle_packet(client_slot, payload_length, payload)
            else:
                logger.debug(f"Payload length mismatch: expected {payload_length}, got {len(payload)}")

    def _handle_new_packet(self, data: bytearray, notifications: Notifications) -> None:
        """Handle a new packet from the device.

        Args:
            data: Raw packet data
            notifications: Handler for complete packets
        """
        if len(data) < 3:
            logger.debug(f"Ignoring too-short packet: {_format_bytearray(data)}")
            return

        client_slot = data[0] - 0x40
        payload_length = data[2]
        payload = data[3:]

        logger.debug(f"New packet - client_slot: {client_slot}, length: {payload_length}, data: {_format_bytearray(payload)}")

        if len(payload) < payload_length:
            logger.debug(f"Starting packet reassembly - expected length: {payload_length}")
            self._start_packet_reassembly(client_slot, payload_length, payload)
        elif len(payload) == payload_length:
            notifications.handle_packet(client_slot, payload_length, payload)
        else:
            logger.debug(f"Payload length mismatch: expected {payload_length}, got {len(payload)}")

    def _reset_packet_reassembly(self) -> None:
        """Reset packet reassembly state."""
        self._partial_payload = bytearray()
        self._reassembly_client_slot = None
        self._reassembly_payload_length = None

    def _start_packet_reassembly(self, client_slot: int, payload_length: int, initial_payload: bytearray) -> None:
        """Start reassembling a split packet.

        Args:
            client_slot: Client slot from packet header
            payload_length: Expected total payload length
            initial_payload: First chunk of payload data
        """
        self._reassembly_client_slot = client_slot
        self._reassembly_payload_length = payload_length
        self._partial_payload.extend(initial_payload)

    async def pair_client(self, new_client_id: int, client_name: str, notifications: Notifications) -> Tuple[int, int]:
        """Pair a new client with the device.

        Args:
            new_client_id: Client ID to register
            client_name: Name to register client under
            notifications: Handler for pairing response

        Returns:
            tuple: (client_id, client_slot) assigned by device

        Raises:
            Exception: If pairing times out
        """
        logger.debug(f"Pairing client {new_client_id} with {client_name}")
        
        payload = self._build_pairing_payload(new_client_id, client_name)
        full_payload = _get_payload_with_crc(payload, MAGIC_ID)

        return await self._execute_pairing(full_payload, new_client_id, notifications)

    def _build_pairing_payload(self, new_client_id: int, client_name: str) -> bytearray:
        """Build payload for pairing request.

        Args:
            new_client_id: Client ID to register
            client_name: Name to register client under

        Returns:
            bytearray: Formatted pairing payload

        Raises:
            ValueError: If client name too long
        """
        new_client_id_bytes = struct.pack(">I", new_client_id)
        client_name_bytes = client_name.encode("UTF-8")

        if len(client_name_bytes) > 20:
            raise ValueError("The client name is too long")

        client_name_bytes += bytearray([0] * (20 - len(client_name_bytes)))
        return bytearray([0, 0xEB, 24]) + new_client_id_bytes + client_name_bytes

    async def _execute_pairing(self, full_payload: bytearray, new_client_id: int, 
                             notifications: Notifications) -> Tuple[int, int]:
        """Execute pairing process with device.

        Args:
            full_payload: Complete pairing request payload
            new_client_id: Client ID being registered
            notifications: Handler for pairing response

        Returns:
            tuple: (client_id, client_slot) assigned by device

        Raises:
            Exception: If no response received
        """
        self._response_event.clear()
        self._response_data = None

        await self._client.start_notify(UUID_READ, 
            lambda _, data: self._handle_notification(data, notifications))

        try:
            notifications.reset()
            await self._write_chunks(full_payload)

            try:
                await asyncio.wait_for(notifications.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                raise Exception("No response received from device after pairing")

            return new_client_id, notifications.client_slot
        finally:
            await self._client.stop_notify(UUID_READ)

    async def _read(self, characteristic: str) -> bytes:
        """Read value from BLE characteristic.

        Args:
            characteristic: UUID of characteristic to read

        Returns:
            bytes: Data read from characteristic
        """
        client = self._client
        if client is None or not client.is_connected:
            raise ConnectionError(f"Not connected to {self._address}")
        return await client.read_gatt_char(characteristic)

    async def _write_chunks(self, data: bytearray, chunk_size: int = 20) -> None:
        """Write data in chunks to device.

        Args:
            data: Data to write
            chunk_size: Maximum size of each chunk
        """
        for chunk in _split_chunks(data, chunk_size):
            await self._write(chunk)

    async def _write(self, data: Union[bytes, bytearray]) -> None:
        """Write data to device.

        Args:
            data: Data to write

        Raises:
            ConnectionError: If not connected
        """
        client = self._client
        if client is None or not client.is_connected:
            raise ConnectionError(f"Not connected to {self._address}")
        logger.debug(f"Writing data to device: {_format_bytearray(data)}")
        await client.write_gatt_char(UUID_WRITE, bytes(data), response=False)
        logger.debug("Write completed")

    async def get_device_info(self) -> Dict[str, str]:
        """Get basic device information.

        Returns:
            dict: Device name, manufacturer and model
        """
        logger.debug("Requesting device information")
        device_name = (await self._read(UUID_DEVICE_NAME)).decode('UTF-8')
        manufacturer = (await self._read(UUID_MANUFACTURER)).decode('UTF-8')
        model_number = (await self._read(UUID_MODEL_NUMBER)).decode('UTF-8')

        logger.debug(f"Device info - name: {device_name}, manufacturer: {manufacturer}, model: {model_number}")
        return {'name': device_name, 'manufacturer': manufacturer, 'model': model_number}

    async def request_client_details(self, client_slot: int) -> None:
        """Request details about a specific client slot.

        Args:
            client_slot: Slot number to query
        """
        payload = bytearray([self._client_slot, 0x6b, 1, 0x10 + client_slot])
        await self._write(_get_payload_with_crc(payload, self._client_id))

    async def request_client_slots(self) -> None:
        """Request list of active client slots."""
        payload = bytearray([self._client_slot, 0x6b, 1, 0])
        await self._write(_get_payload_with_crc(payload, self._client_id))

    async def request_device_settings(self) -> None:
        """Request device settings."""
        payload = bytearray([self._client_slot, 0x3e, 0])
        await self._write(_get_payload_with_crc(payload, self._client_id))

    async def request_device_state(self) -> None:
        """Request current device state."""
        payload = bytearray([self._client_slot, 0x7, 0])
        await self._write(_get_payload_with_crc(payload, self._client_id))

    async def request_nickname(self) -> None:
        """Request device nickname."""
        payload = bytearray([self._client_slot, 0x44, 0])
        await self._write(_get_payload_with_crc(payload, self._client_id))

    async def request_outlet_settings(self) -> None:
        """Request outlet configuration settings."""
        payload = bytearray([self._client_slot, 0x10, 0])
        await self._write(_get_payload_with_crc(payload, self._client_id))

    async def request_preset_details(self, preset_slot: int) -> None:
        """Request details about a specific preset.

        Args:
            preset_slot: Preset slot number to query
        """
        payload = bytearray([self._client_slot, 0x30, 1, 0x40 + preset_slot])
        await self._write(_get_payload_with_crc(payload, self._client_id))

    async def request_preset_slots(self) -> None:
        """Request list of preset slots."""
        payload = bytearray([self._client_slot, 0x30, 1, 0x80])
        await self._write(_get_payload_with_crc(payload, self._client_id))

    async def request_technical_info(self) -> None:
        """Request technical device information."""
        payload = bytearray([self._client_slot, 0x32, 1, 1])
        await self._write(_get_payload_with_crc(payload, self._client_id))

    async def unpair_client(self, client_slot_to_unpair: int) -> None:
        """Unpair a client from the device.

        Args:
            client_slot_to_unpair: Slot number to unpair
        """
        payload = bytearray(
            [self._client_slot, 0xeb, 1, client_slot_to_unpair])
        await self._write(_get_payload_with_crc(payload, self._client_id))

    async def control_outlets(self, outlet1: bool, outlet2: bool, temperature: float) -> None:
        """Control outlet states and temperature.

        Args:
            outlet1: True to enable outlet 1
            outlet2: True to enable outlet 2
            temperature: Temperature setpoint
        """
        temperature_bytes = _convert_temperature(temperature)
        payload = bytearray([
            self._client_slot,
            0x87, 0x05,
            TIMER_RUNNING if outlet1 or outlet2 else TIMER_PAUSED,
            temperature_bytes[0], temperature_bytes[1],
            OUTLET_RUNNING if outlet1 else OUTLET_STOPPED,
            OUTLET_RUNNING if outlet2 else OUTLET_STOPPED])
        await self._write(_get_payload_with_crc(payload, self._client_id))

    async def start_preset(self, preset_slot: int) -> None:
        """Start a preset program.

        Args:
            preset_slot: Preset slot number to start
        """
        payload = bytearray([self._client_slot, 0xb1, 1, preset_slot])
        await self._write(_get_payload_with_crc(payload, self._client_id))
