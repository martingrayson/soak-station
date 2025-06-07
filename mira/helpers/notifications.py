# Standard library imports
import asyncio
import logging
import struct
from typing import Callable, Dict, Optional, List, Union

# Local imports
from .const import SUCCESS, FAILURE, OUTLET_RUNNING, TIMER_STOPPED, TIMER_PAUSED, TIMER_RUNNING
from .generic import _bits_to_list, _convert_temperature_reverse
from .data_model import SoakStationData, TimerState, SoakStationMetadata

# Mapping of timer state codes to TimerState enum values
TIMER_STATE_MAP: Dict[int, TimerState] = {
    TIMER_STOPPED: TimerState.STOPPED,
    TIMER_PAUSED: TimerState.PAUSED,
    TIMER_RUNNING: TimerState.RUNNING,
}

# Set up logging
logger = logging.getLogger(__name__)


class Notifications:
    """Handles processing of notification packets from Mira devices.
    
    This class processes different types of notification packets from the device,
    updating the device model and metadata accordingly. It supports both pairing
    and normal operation modes.
    
    Attributes:
        _model: Optional data model to update with device state
        _metadata: Optional metadata object to update with device info
        _is_pairing: Whether this instance is being used for pairing
        _wait_event: Event for synchronizing notification processing
        partial_payload: Buffer for reassembling split packets
        client_slot: Current client slot being processed
        expected_payload_length: Expected length of reassembled packet
    """

    def __init__(self, *, model: Optional[SoakStationData] = None, metadata: Optional[SoakStationMetadata] = None, is_pairing: bool = False) -> None:
        """Initialize notification handler.
        
        Args:
            model: Optional data model to update with device state
            metadata: Optional metadata object to update with device info
            is_pairing: Whether this instance is being used for pairing
        """
        # Store model and metadata references
        self._model: Optional[SoakStationData] = model
        self._metadata: Optional[SoakStationMetadata] = metadata
        self._is_pairing: bool = is_pairing
        
        # Create event for synchronizing notification processing
        self._wait_event: asyncio.Event = asyncio.Event()

        # Initialize buffers for partial message reconstruction
        self.partial_payload: bytearray = bytearray()
        self.client_slot: Optional[int] = None
        self.expected_payload_length: Optional[int] = None

        # Map payload lengths to their corresponding handler methods
        self._handlers: Dict[int, Callable[[int, bytearray], None]] = {
            1: self._handle_success_or_failure,    # Status updates
            2: self._handle_slots,                 # Slot list
            4: self._handle_device_settings,       # Device configuration
            10: self._handle_device_state,         # Current device state
            11: self._handle_controls_operated_or_outlet_settings,  # Control/outlet updates
            16: self._handle_technical_info_or_nickname,  # Device info/nickname
            20: self._handle_client_details,       # Client information
            24: self._handle_preset_details,       # Preset configuration
        }

    async def wait(self) -> None:
        """Wait for notification processing to complete."""
        await self._wait_event.wait()

    def _set(self) -> None:
        """Set the wait event to signal completion."""
        self._wait_event.set()

    def reset(self) -> None:
        """Reset the wait event."""
        self._wait_event.clear()

    def handle_packet(self, client_slot: int, payload_length: int, payload: bytearray) -> None:
        """Process a notification packet.
        
        Args:
            client_slot: Slot number of the client
            payload_length: Length of the payload
            payload: The packet payload data
        """
        # Get appropriate handler for this payload length
        handler = self._handlers.get(payload_length)
        if handler:
            handler(client_slot, payload)
        else:
            logger.debug("No handler for payload length %d", payload_length)
        self._set()

    def _handle_success_or_failure(self, slot: int, payload: bytearray) -> None:
        """Handle success/failure status packet.
        
        Args:
            slot: Client slot number
            payload: Packet payload containing status code
        """
        status: int = payload[0]

        if status == FAILURE:
            logger.debug("The command failed")
        elif self._is_pairing:
            self.client_slot = status
        elif status == SUCCESS:
            logger.debug("The command completed successfully")
        else:
            raise Exception(f"Unrecognized status: {status}")

    def _handle_slots(self, slot: int, payload: bytearray) -> None:
        """Handle slot list packet.
        
        Lists the slots currently in use on the device (e.g. client x in slot 1 on Shower Y)
        
        Args:
            slot: Client slot number
            payload: Packet payload containing slot bitmap
        """
        # Convert 16-bit bitmap to list of active slots
        slots: List[int] = _bits_to_list(struct.unpack(">H", payload)[0], 16)
        if self._model:
            self._model.slots = slots

    def _handle_device_settings(self, slot: int, payload: bytearray) -> None:
        """Handle device settings packet.
        
        Args:
            slot: Client slot number
            payload: Packet payload containing device settings
        """
        # Extract device configuration from payload
        outlet_enabled: List[int] = _bits_to_list(payload[1], 8)
        default_preset_slot: int = payload[2]
        controller_settings: List[int] = _bits_to_list(payload[3], 8)

        if self._metadata:
            self._metadata.update_device_settings(outlet_enabled, default_preset_slot, controller_settings)

    def _handle_device_state(self, slot: int, payload: bytearray) -> None:
        """Handle device state packet.
        
        Get details about the outlets and other status of the device.
        
        Args:
            slot: Client slot number
            payload: Packet payload containing device state
        """
        # Validate payload length
        if len(payload) < 7:
            logger.debug(f"Unexpected payload length for device state: {len(payload)} - {payload}")
            return

        # Extract timer state
        timer_state: Optional[TimerState] = TIMER_STATE_MAP.get(payload[1])
        if timer_state is None:
            logger.debug(f"Unknown timer state value: {payload[1]}")

        # Extract temperature and state information
        target_temperature: float = _convert_temperature_reverse(payload[1:3])
        actual_temperature: float = _convert_temperature_reverse(payload[3:5])
        remaining_seconds: int = struct.unpack(">H", payload[7:9])[0]
        outlet_state_1: bool = payload[5] == OUTLET_RUNNING
        outlet_state_2: bool = payload[6] == OUTLET_RUNNING

        # Update model if available
        if self._model:
            self._model.update_state(outlet_1_on=outlet_state_1, outlet_2_on=outlet_state_2,
                                     target_temp=target_temperature, actual_temp=actual_temperature,
                                     remaining_seconds=remaining_seconds, timer_state=timer_state)

    def _handle_controls_operated_or_outlet_settings(self, slot: int, payload: bytearray) -> None:
        """Handle controls operated or outlet settings packet.
        
        Args:
            slot: Client slot number
            payload: Packet payload containing control or outlet settings
        """
        if payload[0] in [1, 0x80]:  # Handle control operation updates
            # Extract timer state
            timer_state: Optional[TimerState] = TIMER_STATE_MAP.get(payload[1])
            if timer_state is None:
                logger.debug(f"Unknown timer state value: {payload[1]}")

            # Extract temperature and state information
            target_temperature: float = _convert_temperature_reverse(payload[2:4])
            actual_temperature: float = _convert_temperature_reverse(payload[4:6])
            outlet_state_1: bool = payload[6] == OUTLET_RUNNING
            outlet_state_2: bool = payload[7] == OUTLET_RUNNING
            remaining_seconds: int = struct.unpack(">H", payload[8:10])[0]

            # Update model if available
            if self._model:
                self._model.update_state(outlet_1_on=outlet_state_1, outlet_2_on=outlet_state_2,
                                         target_temp=target_temperature, actual_temp=actual_temperature,
                                         remaining_seconds=remaining_seconds, timer_state=timer_state)

        elif payload[0] in [0, 0x4, 0x8]:  # Handle outlet settings updates
            # Extract outlet configuration
            outlet_flag: int = payload[0]
            min_duration_seconds: int = payload[4]
            max_temperature: float = _convert_temperature_reverse(payload[5:7])
            min_temperature: float = _convert_temperature_reverse(payload[7:9])

            if self._metadata:
                self._metadata.update_outlet_settings(outlet_flag, min_duration_seconds, max_temperature,
                                                      min_temperature)

    def _handle_technical_info_or_nickname(self, slot: int, payload: bytearray) -> None:
        """Handle technical info or nickname packet.
        
        Args:
            slot: Client slot number
            payload: Packet payload containing technical info or nickname
        """
        if self._metadata is None:
            return

        if payload[0] == 0:
            values = struct.unpack(">8H", payload)
            valve_sw_version: str = f"{values[0]}.{values[1]}"
            bt_sw_version: str = f"{values[2]}.{values[3]}"
            ui_sw_version: str = f"{values[6]}.{values[7]}"

            self._metadata.update_from_technical_info(valve_sw_version, bt_sw_version, ui_sw_version)
        else:
            self._metadata.update_nickname(payload.decode("UTF-8"))

    def _handle_client_details(self, slot: int, payload: bytearray) -> None:
        if self._metadata:
            self._metadata.update_client_name(payload.decode("UTF-8"))

    def _handle_preset_details(self, slot: int, payload: bytearray) -> None:
        if self._metadata:
            slot: int = payload[0]
            target_temp: float = _convert_temperature_reverse(payload[1:3])
            duration: int = payload[4]
            outlet_flags: List[int] = _bits_to_list(payload[5], 8)
            name: str = payload[8:].decode('UTF-8')

            self._metadata.update_preset(slot, target_temp, duration, outlet_flags, name)
