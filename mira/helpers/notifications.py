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
        logger.debug(f"Initializing notification handler - pairing mode: {is_pairing}")
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
        logger.debug("Notification handler initialized")

    async def wait(self) -> None:
        """Wait for notification processing to complete."""
        logger.debug("Waiting for notification processing")
        await self._wait_event.wait()
        logger.debug("Notification processing completed")

    def _set(self) -> None:
        """Set the wait event to signal completion."""
        logger.debug("Setting notification completion event")
        self._wait_event.set()

    def reset(self) -> None:
        """Reset the wait event."""
        logger.debug("Resetting notification event")
        self._wait_event.clear()

    def handle_packet(self, client_slot: int, payload_length: int, payload: bytearray) -> None:
        """Handle a packet from the device.

        Args:
            client_slot: Client slot from packet header
            payload_length: Expected payload length
            payload: Packet payload data
        """
        logger.debug(f"Handling packet - client_slot: {client_slot}, length: {payload_length}")
        
        if payload_length not in self._handlers:
            logger.debug(f"No handler for payload length {payload_length}")
            return

        handler = self._handlers[payload_length]
        if not handler(client_slot, payload):
            logger.debug("Command failed")
            return

        logger.debug("Packet handled successfully")
        self._set()

    def _handle_success_or_failure(self, slot: int, payload: bytearray) -> bool:
        """Handle success/failure status packet.
        
        Args:
            slot: Client slot number
            payload: Packet payload containing status code
        """
        status: int = payload[0]
        logger.debug(f"Processing status packet - status: {status}")

        if status == FAILURE:
            logger.debug("The command failed")
            return False
        elif self._is_pairing:
            self.client_slot = status
            logger.debug(f"Pairing successful - assigned client slot: {status}")
        elif status == SUCCESS:
            logger.debug("The command completed successfully")
        else:
            logger.debug(f"Unrecognized status: {status}")
            raise Exception(f"Unrecognized status: {status}")
        return True

    def _handle_slots(self, slot: int, payload: bytearray) -> bool:
        """Handle slot list packet.
        
        Lists the slots currently in use on the device (e.g. client x in slot 1 on Shower Y)
        
        Args:
            slot: Client slot number
            payload: Packet payload containing slot bitmap
        """
        logger.debug("Processing slot list packet")
        # Convert 16-bit bitmap to list of active slots
        slots: List[int] = _bits_to_list(struct.unpack(">H", payload)[0], 16)
        if self._model:
            self._model.slots = slots
            logger.debug(f"Updated slots: {slots}")
        return True

    def _handle_device_settings(self, slot: int, payload: bytearray) -> bool:
        """Handle device settings packet.
        
        Args:
            slot: Client slot number
            payload: Packet payload containing device settings
        """
        logger.debug("Processing device settings packet")
        # Extract device configuration from payload
        outlet_enabled: List[int] = _bits_to_list(payload[1], 8)
        default_preset_slot: int = payload[2]
        controller_settings: List[int] = _bits_to_list(payload[3], 8)

        if self._metadata:
            self._metadata.update_device_settings(outlet_enabled, default_preset_slot, controller_settings)
            logger.debug(f"Updated device settings - outlets: {outlet_enabled}, default preset: {default_preset_slot}")
        return True

    def _handle_device_state(self, slot: int, payload: bytearray) -> bool:
        """Handle device state packet.
        
        Get details about the outlets and other status of the device.
        
        Args:
            slot: Client slot number
            payload: Packet payload containing device state
        """
        logger.debug("Processing device state packet")
        # Validate payload length
        if len(payload) < 8:
            logger.debug(f"Unexpected payload length for device state: {len(payload)}")
            return False

        # Extract timer state
        timer_state: Optional[TimerState] = TIMER_STATE_MAP.get(payload[1])
        if timer_state is None:
            logger.debug(f"Unknown timer state value: {payload[1]}")
            return False

        # Extract temperature and state information
        target_temperature: float = _convert_temperature_reverse(payload[1:3])
        actual_temperature: float = _convert_temperature_reverse(payload[3:5])
        remaining_seconds: int = struct.unpack(">H", payload[7:9])[0]
        outlet_state_1: bool = payload[5] == OUTLET_RUNNING
        outlet_state_2: bool = payload[6] == OUTLET_RUNNING

        logger.debug(f"Device state - timer: {timer_state}, target temp: {target_temperature}, "
                    f"actual temp: {actual_temperature}, remaining: {remaining_seconds}s, "
                    f"outlets: [{outlet_state_1}, {outlet_state_2}]")

        # Update model if available
        if self._model:
            self._model.update_state(outlet_1_on=outlet_state_1, outlet_2_on=outlet_state_2,
                                     target_temp=target_temperature, actual_temp=actual_temperature,
                                     remaining_seconds=remaining_seconds, timer_state=timer_state)
        return True

    def _handle_controls_operated_or_outlet_settings(self, slot: int, payload: bytearray) -> bool:
        """Handle controls operated or outlet settings packet.
        
        Args:
            slot: Client slot number
            payload: Packet payload containing control or outlet settings
        """
        logger.debug(f"Processing control/outlet packet - type: {payload[0]}")
        
        if payload[0] in [1, 0x80]:  # Handle control operation updates
            # Extract timer state
            timer_state: Optional[TimerState] = TIMER_STATE_MAP.get(payload[1])
            if timer_state is None:
                logger.debug(f"Unknown timer state value: {payload[1]}")
                return False

            # Extract temperature and state information
            target_temperature: float = _convert_temperature_reverse(payload[2:4])
            actual_temperature: float = _convert_temperature_reverse(payload[4:6])
            outlet_state_1: bool = payload[6] == OUTLET_RUNNING
            outlet_state_2: bool = payload[7] == OUTLET_RUNNING
            remaining_seconds: int = struct.unpack(">H", payload[8:10])[0]

            logger.debug(f"Control update - timer: {timer_state}, target temp: {target_temperature}, "
                        f"actual temp: {actual_temperature}, remaining: {remaining_seconds}s, "
                        f"outlets: [{outlet_state_1}, {outlet_state_2}]")

            # Update model if available
            if self._model:
                self._model.update_state(outlet_1_on=outlet_state_1, outlet_2_on=outlet_state_2,
                                         target_temp=target_temperature, actual_temp=actual_temperature,
                                         remaining_seconds=remaining_seconds, timer_state=timer_state)
            return True

        elif payload[0] in [0, 0x4, 0x8]:  # Handle outlet settings updates
            # Extract outlet configuration
            outlet_flag: int = payload[0]
            min_duration_seconds: int = payload[4]
            max_temperature: float = _convert_temperature_reverse(payload[5:7])
            min_temperature: float = _convert_temperature_reverse(payload[7:9])

            logger.debug(f"Outlet settings - flag: {outlet_flag}, min duration: {min_duration_seconds}s, "
                        f"temp range: {min_temperature}-{max_temperature}°C")

            if self._metadata:
                self._metadata.update_outlet_settings(outlet_flag, min_duration_seconds, max_temperature,
                                                      min_temperature)
            return True

        return False

    def _handle_technical_info_or_nickname(self, slot: int, payload: bytearray) -> bool:
        """Handle technical info or nickname packet.
        
        Args:
            slot: Client slot number
            payload: Packet payload containing technical info or nickname
        """
        logger.debug("Processing technical info/nickname packet")
        
        if self._metadata is None:
            logger.debug("No metadata object available")
            return False

        if payload[0] == 0:
            values = struct.unpack(">8H", payload)
            valve_sw_version: str = f"{values[0]}.{values[1]}"
            bt_sw_version: str = f"{values[2]}.{values[3]}"
            ui_sw_version: str = f"{values[6]}.{values[7]}"

            logger.debug(f"Technical info - valve: {valve_sw_version}, bt: {bt_sw_version}, ui: {ui_sw_version}")
            self._metadata.update_from_technical_info(valve_sw_version, bt_sw_version, ui_sw_version)
            return True
        else:
            nickname = payload.decode("UTF-8")
            logger.debug(f"Updating nickname: {nickname}")
            self._metadata.update_nickname(nickname)
            return True

    def _handle_client_details(self, slot: int, payload: bytearray) -> bool:
        """Handle client details packet."""
        if self._metadata:
            client_name = payload.decode("UTF-8")
            logger.debug(f"Updating client name: {client_name}")
            self._metadata.update_client_name(client_name)
            return True
        logger.debug("No metadata object available for client details")
        return False

    def _handle_preset_details(self, slot: int, payload: bytearray) -> bool:
        """Handle preset details packet."""
        if self._metadata:
            slot: int = payload[0]
            target_temp: float = _convert_temperature_reverse(payload[1:3])
            duration: int = payload[4]
            outlet_flags: List[int] = _bits_to_list(payload[5], 8)
            name: str = payload[8:].decode('UTF-8').rstrip('\0')

            logger.debug(f"Preset details - slot: {slot}, temp: {target_temp}°C, "
                        f"duration: {duration}s, outlets: {outlet_flags}, name: {name}")
            
            self._metadata.update_preset(slot, target_temp, duration, outlet_flags, name)
            return True
        logger.debug("No metadata object available for preset details")
        return False
