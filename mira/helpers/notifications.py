import asyncio
import logging
import struct
from typing import Callable, Dict

from .const import SUCCESS, FAILURE, OUTLET_RUNNING, TIMER_STOPPED, TIMER_PAUSED, TIMER_RUNNING
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
            11: self._handle_controls_operated_or_outlet_settings,
            16: self._handle_technical_info_or_nickname,
            20: self._handle_client_details,
            24: self._handle_preset_details,
        }

    async def wait(self):
        await self._wait_event.wait()

    def _set(self):
        self._wait_event.set()

    def reset(self):
        self._wait_event.clear()

    def handle_packet(self, client_slot, payload_length, payload):
        # logger.warning(f"Handle packet {client_slot}, {payload_length}, {payload}")
        handler = self._handlers.get(payload_length)
        if handler:
            # logger.warning(f"calling handler {handler}")
            handler(client_slot, payload)
        else:
            logger.warning("No handler for payload length %d", payload_length)
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

        #TODO: Move this logic.
        if payload[1] == TIMER_STOPPED:
            timer_state = "stopped"
        elif payload[1] == TIMER_PAUSED:
            timer_state = "paused"
        elif payload[1] == TIMER_RUNNING:
            timer_state = "running"

        target_temperature = _convert_temperature_reverse(payload[1:3])
        actual_temperature = _convert_temperature_reverse(payload[3:5])
        remaining_seconds = struct.unpack(">H", payload[7:9])[0]
        outlet_state_1 = payload[5] == OUTLET_RUNNING
        outlet_state_2 = payload[6] == OUTLET_RUNNING

        logger.warning(f"Timer state: {timer_state}, target temperature: {target_temperature}, actual temperature: {actual_temperature}, remaining seconds: {remaining_seconds}, outlet state 1: {outlet_state_1}, outlet state 2: {outlet_state_2}")

        self._model.update_state(outlet_1_on=outlet_state_1, outlet_2_on=outlet_state_2,
                                 target_temp=target_temperature, actual_temp=actual_temperature,
                                 remaining_seconds=remaining_seconds, timer_state=timer_state)

    def _handle_controls_operated_or_outlet_settings(self, slot, payload):
        if payload[0] in [1, 0x80]:  # controls operated
            # change_made = payload[0] == 1
            if payload[1] == TIMER_STOPPED:
                timer_state = "stopped"
            elif payload[1] == TIMER_PAUSED:
                timer_state = "paused"
            elif payload[1] == TIMER_RUNNING:
                timer_state = "running"

            target_temperature = _convert_temperature_reverse(payload[2:4])
            actual_temperature = _convert_temperature_reverse(payload[4:6])
            outlet_state_1 = payload[6] == OUTLET_RUNNING
            outlet_state_2 = payload[7] == OUTLET_RUNNING
            remaining_seconds = struct.unpack(">H", payload[8:10])[0]

            self._model.update_state(outlet_1_on=outlet_state_1, outlet_2_on=outlet_state_2,
                                     target_temp=target_temperature, actual_temp=actual_temperature,
                                     remaining_seconds=remaining_seconds, timer_state=timer_state)

        elif payload[0] in [0, 0x4, 0x8]:  # outlet settings
            outlet_flag = payload[0]
            min_duration_seconds = payload[4]
            max_temperature = _convert_temperature_reverse(payload[5:7])
            min_temperature = _convert_temperature_reverse(payload[7:9])

            #TODO: Update the model here later



    def _handle_technical_info_or_nickname(self, slot, payload):
        if payload[0] == 0:
            valve_type = payload[1]
            valve_sw_version = payload[3]
            ui_type = payload[5]
            ui_sw_version = payload[7]
            bt_sw_version = payload[15]

            # TODO: Update the model here later

        else:
            nickname = payload.decode("UTF-8")
            # TODO: Update the model here later

    def _handle_client_details(self, slot, payload):
        name = payload.decode("UTF-8")
        # TODO: Update the model here later

    def _handle_preset_details(self, slot, payload):
        preset_slot = payload[0]
        target_temperature = _convert_temperature_reverse(payload[1:3])
        duration_seconds = payload[4]
        outlet_enabled = _bits_to_list(payload[5], 8)
        preset_name = payload[8:].decode('UTF-8')

        # TODO: Update the model here later