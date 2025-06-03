import asyncio
import logging
import struct

import bleak
import retrying
from bleak import BLEDevice
from homeassistant.components.bluetooth import (
    async_ble_device_from_address
)

from .const import MAGIC_ID, TIMER_RUNNING, OUTLET_RUNNING, OUTLET_STOPPED, TIMER_PAUSED, \
    UUID_DEVICE_NAME, UUID_MANUFACTURER, UUID_MODEL_NUMBER, UUID_READ, UUID_WRITE
from .generic import _get_payload_with_crc, _convert_temperature, _convert_temperature_reverse, \
    _bits_to_list, _format_bytearray, _split_chunks


logger = logging.getLogger(__name__)


class Connection:
    def __init__(self, hass, address, client_id=None, client_slot=None):
        self._hass = hass
        self._address = address
        self._peripheral: BLEDevice = None
        self._client_id = client_id
        self._client_slot = client_slot
        self._client = None

    def set_client_data(self, client_id, client_slot):
        self._client_id = client_id
        self._client_slot = client_slot

    @retrying.retry(stop_max_attempt_number=10)
    async def connect(self):
        self._peripheral: BLEDevice = async_ble_device_from_address(self._hass, self._address,
                                                                              connectable=True)
        self._client = bleak.BleakClient(self._peripheral)
        await self._client.connect()


    async def disconnect(self):
        self._peripheral = None
        await self._client.disconnect()

    async def __aenter__(self):
        self.connect()
        return self

    async def __aexit__(self, type, value, traceback):
        self.disconnect()

    async def pair_client(self, new_client_id, client_name):
        new_client_id_bytes = struct.pack(">I", new_client_id)
        client_name_bytes = client_name.encode("UTF-8")

        if len(client_name_bytes) > 20:
            raise Exception("The client name is too long")

        client_name_bytes += bytearray([0] * (20 - len(client_name_bytes)))

        payload = (bytearray([0, 0xeb, 24]) + new_client_id_bytes +
                   client_name_bytes)
        await self._write_chunks(_get_payload_with_crc(payload, MAGIC_ID))

    async def _read(self, characteristic):
        return await self._client.read_gatt_char(characteristic)

    async def _write_chunks(self, data, chunk_size=20):
        for chunk in _split_chunks(data, chunk_size):
            await self._write(chunk)

    async def _write(self, data):
        logger.debug(f"Writing data: {_format_bytearray(data)}")
        await self._client.write_gatt_char(UUID_WRITE, bytes(data), response=False)

    # def _get_service_for_characteristic(self, characteristic):
    #     services = self._peripheral.services()
    #     for service in services:
    #         for c in service.characteristics():
    #             logger.debug(f'Found service: "{service.uuid()}", '
    #                          f'characteristic: "{c.uuid()}"')
    #             if c.uuid() == characteristic:
    #                 return service.uuid()
    #     raise Exception(f"Characteristic not found: {characteristic}")

    # def subscribe(self, notifications):
    #     notifications.partial_payload = bytearray()
    #     notifications.client_slot = None
    #     notifications.expected_payload_length = None
    #
    #     service = self._get_service_for_characteristic(UUID_READ)
    #
    #     self._peripheral.notify(
    #         service, UUID_READ, lambda value: self._handle_data(
    #             value, notifications))

    def _handle_data(self, value, notifications):
        if len(notifications.partial_payload) > 0:
            notifications.partial_payload.extend(value)
            client_slot = notifications.client_slot
            payload = notifications.partial_payload
            payload_length = notifications.expected_payload_length

            notifications.partial_payload = bytearray()
            notifications.client_slot = None
            notifications.expected_payload_length = None
        else:
            if len(value) < 2:
                logger.warning(
                    f"Packet length is too short, skipping: {len(value)}")
                return

            client_slot = value[0] - 0x40
            payload_length = value[2]
            payload = value[3:]

        if len(payload) < payload_length:
            notifications.client_slot = client_slot
            notifications.expected_payload_length = payload_length
            notifications.partial_payload.extend(payload)
            return

        if len(payload) != payload_length:
            logger.warning(
                "Inconsistent payload length, skipping: "
                f"{payload_length}, {len(payload)}")
            return

        logger.debug(
            f"Payload length: {payload_length}, "
            f"payload : {_format_bytearray(payload)}")

        if payload_length == 1:
            notifications.success_or_failure(client_slot, payload[0])

        elif payload_length == 2:
            slots = []
            slot_bits = struct.unpack(">H", payload)[0]
            slots = _bits_to_list(slot_bits, 16)

            notifications.slots(client_slot, slots)

        elif payload_length == 4:
            outlet_enabled = _bits_to_list(payload[1], 8)
            default_preset_slot = payload[2]
            controller_senntings = _bits_to_list(payload[3], 8)

            notifications.device_settings(
                client_slot, outlet_enabled, default_preset_slot,
                controller_senntings)

        elif payload_length == 10:
            timer_state = payload[0]
            target_temperature = _convert_temperature_reverse(payload[1:3])
            actual_temperature = _convert_temperature_reverse(payload[3:5])
            outlet_state_1 = payload[5] == OUTLET_RUNNING
            outlet_state_2 = payload[6] == OUTLET_RUNNING
            remaining_seconds = struct.unpack(">H", payload[7:9])[0]
            successful_update_command_counter = payload[9]

            notifications.device_state(
                client_slot, timer_state, target_temperature,
                actual_temperature, outlet_state_1, outlet_state_2,
                remaining_seconds, successful_update_command_counter)

        elif payload_length == 11 and payload[0] in [1, 0x80]:
            change_made = payload[0] == 1
            timer_state = payload[1]
            target_temperature = _convert_temperature_reverse(payload[2:4])
            actual_temperature = _convert_temperature_reverse(payload[4:6])
            outlet_state_1 = payload[6] == OUTLET_RUNNING
            outlet_state_2 = payload[7] == OUTLET_RUNNING
            remaining_seconds = struct.unpack(">H", payload[8:10])[0]
            successful_update_command_counter = payload[10]

            notifications.controls_operated(
                client_slot, change_made, timer_state, target_temperature,
                actual_temperature, outlet_state_1, outlet_state_2,
                remaining_seconds, successful_update_command_counter)

        elif payload_length == 11 and payload[0] in [0, 0x4, 0x8]:
            outlet_flag = payload[0]
            min_duration_seconds = payload[4]
            max_temperature = _convert_temperature_reverse(payload[5:7])
            min_temperature = _convert_temperature_reverse(payload[7:9])
            successful_update_command_counter = payload[10]

            notifications.outlet_settings(
                client_slot, outlet_flag, min_duration_seconds,
                max_temperature, min_temperature,
                successful_update_command_counter)

        elif payload_length == 16 and payload[0] == 0:
            valve_type = payload[1]
            valve_sw_version = payload[3]
            ui_type = payload[5]
            ui_sw_version = payload[7]
            bt_sw_version = payload[15]

            notifications.technical_information(
                client_slot, valve_type, valve_sw_version, ui_type,
                ui_sw_version, bt_sw_version)

        elif payload_length == 16 and payload[0] != 0:
            nickname = payload.decode('UTF-8')
            notifications.nickname(client_slot, nickname)

        elif payload_length == 20:
            client_name = payload.decode('UTF-8')
            notifications.client_details(client_slot, client_name)

        elif payload_length == 24:
            preset_slot = payload[0]
            target_temperature = _convert_temperature_reverse(payload[1:3])
            duration_seconds = payload[4]
            outlet_enabled = _bits_to_list(payload[5], 8)
            preset_name = payload[8:].decode('UTF-8')

            notifications.preset_details(
                client_slot, preset_slot, target_temperature, duration_seconds,
                outlet_enabled, preset_name)

    async def get_device_info(self):
        device_name = (await self._read(UUID_DEVICE_NAME).decode('UTF-8'))
        manufacturer = (await self._read(UUID_MANUFACTURER).decode('UTF-8'))
        model_number = (await self._read(UUID_MODEL_NUMBER).decode('UTF-8'))

        return device_name, manufacturer, model_number

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
