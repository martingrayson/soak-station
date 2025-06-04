import asyncio
import logging
import struct
from typing import Callable, Dict

from .const import SUCCESS, FAILURE, OUTLET_RUNNING
from .generic import _bits_to_list, _convert_temperature_reverse
from .data_model import SoakStationData

logger = logging.getLogger(__name__)

class Notifications:
    def __init__(self, *, model:SoakStationData=None, is_pairing=False):
        self._model = model
        self._is_pairing = is_pairing
        self._wait_event = asyncio.Event()  # internal event for awaiters

        # for partial message reconstruction
        self.partial_payload = bytearray()
        self.client_slot = None
        self.expected_payload_length = None

        # map payload_length to handler
        self._handlers: Dict[int, Callable[[int, bytearray], None]] = {
            1: self._handle_success_or_failure,
            2: self._handle_slots,
            4: self._handle_device_settings,
            10: self._handle_device_state,
            # 11: self._handle_controls_operated_or_outlet_settings,
            # 16: self._handle_technical_info_or_nickname,
            # 20: self._handle_client_details,
            # 24: self._handle_preset_details,
        }

    async def wait(self):
        await self._wait_event.wait()

    def _set(self):
        self._wait_event.set()

    def reset(self):
        self._wait_event.clear()

    def handle_packet(self, client_slot, payload_length, payload):
        logger.warning(f"Handle packet {client_slot}, {payload_length}, {payload}")
        handler = self._handlers.get(payload_length)
        if handler:
            logger.warning(f"calling handler {handler}")
            handler(client_slot, payload)
        logger.warning("finished handling packet")
        self._set()

    # === Individual Handlers ===
    def _handle_success_or_failure(self, slot, payload):
        status = payload[0]

        if status == FAILURE:
            logger.info("The command failed")
        elif self._is_pairing:
            self.client_slot = status
            logger.info(f"Assigned client slot: {status}")
        elif status == SUCCESS:
            logger.info("The command completed successfully")
        else:
            raise Exception(f"Unrecognized status: {status}")


    def _handle_slots(self, slot, payload):
        """ Lists the slots currently in use on the device (e.g. client x in slot 1  on Shower Y"""
        slots = _bits_to_list(struct.unpack(">H", payload)[0], 16)
        if self._model:
            self._model.slots = slots

    def _handle_device_settings(self, slot, payload):
        outlet_enabled = _bits_to_list(payload[1], 8)
        default_preset_slot = payload[2]
        controller_settings = _bits_to_list(payload[3], 8)
        # store or log as needed

    def _handle_device_state(self, slot, payload):
        """ Get details about the outlets and other status of the device """
        if len(payload) < 7:
            logger.warning(f"Unexpected payload length for device state: {len(payload)} - {payload}")
            return

        timer_state = payload[0]
        target_temperature = _convert_temperature_reverse(payload[1:3])
        actual_temperature = _convert_temperature_reverse(payload[3:5])
        remaining_seconds = struct.unpack(">H", payload[7:9])[0]
        outlet_state_1 = payload[5] == OUTLET_RUNNING
        outlet_state_2 = payload[6] == OUTLET_RUNNING
        logger.warning(f"Outlet state: {payload[5]}, {payload[6]}")

        self._model.update_state(outlet_1_on=outlet_state_1, outlet_2_on=outlet_state_2,
                                 target_temp=target_temperature, actual_temp=actual_temperature,
                                 remaining_seconds=remaining_seconds, timer_state=timer_state)

    # def _handle_controls_operated_or_outlet_settings(self, slot, payload):
    #     if payload[0] in [1, 0x80]:  # controls operated
    #         ...
    #     elif payload[0] in [0, 0x4, 0x8]:  # outlet settings
    #         ...
    #
    # def _handle_technical_info_or_nickname(self, slot, payload):
    #     if payload[0] == 0:
    #         ...
    #     else:
    #         nickname = payload.decode("UTF-8")
    #         print(f"Nickname: {nickname}")
    #
    # def _handle_client_details(self, slot, payload):
    #     name = payload.decode("UTF-8")
    #     print(f"Client name: {name}")
    #
    # def _handle_preset_details(self, slot, payload):
    #     ...
