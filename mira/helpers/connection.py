import asyncio
import logging
import struct
from typing import Optional
import bleak

from homeassistant.components.bluetooth import (
    async_ble_device_from_address
)

from .const import MAGIC_ID, TIMER_RUNNING, OUTLET_RUNNING, OUTLET_STOPPED, TIMER_PAUSED, \
    UUID_DEVICE_NAME, UUID_MANUFACTURER, UUID_MODEL_NUMBER, UUID_READ, UUID_WRITE
from .generic import _get_payload_with_crc, _convert_temperature, _format_bytearray, _split_chunks
from .notifications import Notifications

logger = logging.getLogger(__name__)


class Connection:
    def __init__(self, hass, address, client_id=None, client_slot=None):
        self._hass = hass
        self._address = address
        self._peripheral: Optional[bleak.BLEDevice] = None
        self._client_id = client_id
        self._client_slot = client_slot
        self._client = None
        self._notifications = None

        self._response_event = asyncio.Event()
        self._response_data = None

        # For packet reassembly
        self.partial_payload = bytearray()
        self.client_slot = None
        self.expected_payload_length = None

    def set_client_data(self, client_id, client_slot):
        self._client_id = client_id
        self._client_slot = client_slot

    async def connect(self, retries=10, delay=1.0):
        for attempt in range(retries):
            try:
                self._peripheral = async_ble_device_from_address(
                    self._hass, self._address, connectable=True
                )
                if not self._peripheral:
                    raise Exception("Device not found")

                self._client = bleak.BleakClient(self._peripheral)
                await self._client.connect()
                return
            except Exception as e:
                if attempt == retries - 1:
                    raise
                await asyncio.sleep(delay)

    async def reconnect(self):
        await self.disconnect()
        await asyncio.sleep(1)  # small delay to allow clean BLE state
        await self.connect()

    async def disconnect(self):
        logger.warning("Disconnecting")
        self._peripheral = None
        if self._client and self._client.is_connected:
            await self._client.disconnect()

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, type, value, traceback):
        await self.disconnect()

    def _handle_notification(self, data: bytearray, notifications: Notifications):
        logger.warning(f"Notification received: {_format_bytearray(data)}")

        if len(data) < 3:
            logger.warning(f"Invalid packet length: {len(data)}")
            return

        client_slot = data[0] - 0x40
        payload_length = data[2]
        payload = data[3:]

        if len(payload) != payload_length:
            logger.warning(f"Expected {payload_length} bytes, got {len(payload)}")
            return

        notifications.handle_packet(client_slot, payload_length, payload)

    def subscribe(self, notifications):
        """Subscribe to notifications and route to the given Notifications handler."""
        self._notifications = notifications

        async def handle(sender, data):
            if len(self.partial_payload) > 0:
                self.partial_payload.extend(data)
                payload = self.partial_payload
                client_slot = self.client_slot
                payload_length = self.expected_payload_length

                self.partial_payload = bytearray()
                self.client_slot = None
                self.expected_payload_length = None
            else:
                if len(data) < 3:
                    logger.warning(f"Ignoring too-short packet: {data}")
                    return

                client_slot = data[0] - 0x40
                payload_length = data[2]
                payload = data[3:]

            if len(payload) < payload_length:
                self.client_slot = client_slot
                self.expected_payload_length = payload_length
                self.partial_payload.extend(payload)
                return

            if len(payload) != payload_length:
                logger.warning(
                    f"Payload length mismatch: expected {payload_length}, got {len(payload)}"
                )
                return

            self._notifications.handle_packet(client_slot, payload_length, payload)

        # Start notification listener
        logger.warning("Subscribing to BLE notifications for UUID_READ")
        asyncio.create_task(self._client.start_notify(UUID_READ, handle))

    async def pair_client(self, new_client_id, client_name, notifications: Notifications):
        logger.warning(f"Pairing client {new_client_id} with {client_name}")
        new_client_id_bytes = struct.pack(">I", new_client_id)
        client_name_bytes = client_name.encode("UTF-8")

        if len(client_name_bytes) > 20:
            raise Exception("The client name is too long")

        client_name_bytes += bytearray([0] * (20 - len(client_name_bytes)))
        payload = bytearray([0, 0xEB, 24]) + new_client_id_bytes + client_name_bytes
        full_payload = _get_payload_with_crc(payload, MAGIC_ID)

        # Clear previous response
        self._response_event.clear()
        self._response_data = None

        # Subscribe to notifications before writing
        logger.warning(f"Pairing ... awaiting notify")
        await self._client.start_notify(UUID_READ, lambda _, data: self._handle_notification(data, notifications))

        try:
            notifications.reset()
            await self._write_chunks(full_payload)

            try:
                await asyncio.wait_for(notifications.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                raise Exception("No response received from device after pairing")

            logger.warning(f"{new_client_id}, {notifications.client_slot}")
            return new_client_id, notifications.client_slot
        finally:
            logger.warning(f"Stopping notify!!")
            await self._client.stop_notify(UUID_READ)


    async def _read(self, characteristic):
        return await self._client.read_gatt_char(characteristic)

    async def _write_chunks(self, data, chunk_size=20):
        for chunk in _split_chunks(data, chunk_size):
            await self._write(chunk)

    async def _write(self, data):
        logger.debug(f"Writing data: {_format_bytearray(data)}")
        await self._client.write_gatt_char(UUID_WRITE, bytes(data), response=False)

    async def get_device_info(self):
        device_name = (await self._read(UUID_DEVICE_NAME)).decode('UTF-8')
        manufacturer = (await self._read(UUID_MANUFACTURER)).decode('UTF-8')
        model_number = (await self._read(UUID_MODEL_NUMBER)).decode('UTF-8')

        return {'name': device_name, 'manufacturer': manufacturer, 'model': model_number}

    async def request_client_details(self, client_slot):
        payload = bytearray([self._client_slot, 0x6b, 1, 0x10 + client_slot])
        await self._write(_get_payload_with_crc(payload, self._client_id))

    async def request_client_slots(self):
        payload = bytearray([self._client_slot, 0x6b, 1, 0])
        await self._write(_get_payload_with_crc(payload, self._client_id))

    async def request_device_settings(self):
        payload = bytearray([self._client_slot, 0x3e, 0])
        await self._write(_get_payload_with_crc(payload, self._client_id))

    async def request_device_state(self):
        payload = bytearray([self._client_slot, 0x7, 0])
        await self._write(_get_payload_with_crc(payload, self._client_id))

    async def request_nickname(self):
        payload = bytearray([self._client_slot, 0x44, 0])
        await self._write(_get_payload_with_crc(payload, self._client_id))

    async def request_outlet_settings(self):
        payload = bytearray([self._client_slot, 0x10, 0])
        await self._write(_get_payload_with_crc(payload, self._client_id))

    async def request_preset_details(self, preset_slot):
        payload = bytearray([self._client_slot, 0x30, 1, 0x40 + preset_slot])
        await self._write(_get_payload_with_crc(payload, self._client_id))

    async def request_preset_slots(self):
        payload = bytearray([self._client_slot, 0x30, 1, 0x80])
        await self._write(_get_payload_with_crc(payload, self._client_id))

    async def request_technical_info(self):
        logger.warning("requesting technical info")
        payload = bytearray([self._client_slot, 0x32, 1, 1])
        await self._write(_get_payload_with_crc(payload, self._client_id))

    async def unpair_client(self, client_slot_to_unpair):
        payload = bytearray(
            [self._client_slot, 0xeb, 1, client_slot_to_unpair])
        await self._write(_get_payload_with_crc(payload, self._client_id))

    async def control_outlets(self, outlet1, outlet2, temperature):
        temperature_bytes = _convert_temperature(temperature)
        payload = bytearray([
            self._client_slot,
            0x87, 0x05,
            TIMER_RUNNING if outlet1 or outlet2 else TIMER_PAUSED,
            temperature_bytes[0], temperature_bytes[1],
            OUTLET_RUNNING if outlet1 else OUTLET_STOPPED,
            OUTLET_RUNNING if outlet2 else OUTLET_STOPPED])
        await self._write(_get_payload_with_crc(payload, self._client_id))

    async def start_preset(self, preset_slot):
        payload = bytearray([self._client_slot, 0xb1, 1, preset_slot])
        await self._write(_get_payload_with_crc(payload, self._client_id))
