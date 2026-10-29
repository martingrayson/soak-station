"""A fake Mira shower for tests: stands in for the BLE client and the HA Bluetooth lookup.

It answers the requests the integration sends with packets in the device's own
format, and can drop the connection or go out of range on demand.
"""

import asyncio
import struct
from unittest.mock import MagicMock, patch

from custom_components.soakstation.mira.helpers.const import (
    OUTLET_RUNNING,
    OUTLET_STOPPED,
    TIMER_RUNNING,
    TIMER_STOPPED,
    UUID_DEVICE_NAME,
    UUID_MANUFACTURER,
    UUID_MODEL_NUMBER,
)

ADDRESS = "CD:2C:A2:C7:EA:12"
CLIENT_ID = 12345
CLIENT_SLOT = 1

CONNECTION = "custom_components.soakstation.mira.helpers.connection"


def packet(payload: bytes, slot: int = CLIENT_SLOT) -> bytes:
    """A notification as the device sends it: slot, unused byte, length, payload."""
    return bytes([0x40 + slot, 0, len(payload)]) + bytes(payload)


def temp(celsius: float) -> bytes:
    return struct.pack(">H", round(celsius * 10))


class FakeClient:
    """Stands in for a connected BleakClient."""

    def __init__(self, shower: "FakeShower", disconnected_callback) -> None:
        self.shower = shower
        self.is_connected = True
        self.disconnected_callback = disconnected_callback
        self.notify_callback = None
        self.notify_starts = 0

    async def start_notify(self, uuid, callback) -> None:
        self.notify_callback = callback
        self.notify_starts += 1

    async def stop_notify(self, uuid) -> None:
        self.notify_callback = None

    async def read_gatt_char(self, uuid) -> bytes:
        return {
            UUID_DEVICE_NAME: b"Mira N86Sd: Master Bathroom",
            UUID_MANUFACTURER: b"Kohler Mira Ltd",
            UUID_MODEL_NUMBER: b"Soak Station",
        }[uuid]

    async def write_gatt_char(self, uuid, data, response=False) -> None:
        self.shower.writes.append(bytes(data))
        if self.shower.answers:
            reply = self.shower.reply_to(bytes(data))
            if reply is not None:
                asyncio.get_running_loop().call_soon(self.notify, reply)

    async def disconnect(self) -> None:
        self.is_connected = False

    def notify(self, data: bytes, chunk: int = 20) -> None:
        """Deliver a packet the way BLE does: in chunks of at most 20 bytes."""
        if self.notify_callback is None or not self.is_connected:
            return
        for i in range(0, len(data), chunk):
            self.notify_callback(None, bytearray(data[i:i + chunk]))

    def drop(self) -> None:
        """The link drops (out of range, interference, proxy restart)."""
        self.is_connected = False
        self.disconnected_callback(self)


class FakeShower:
    """The device: its state, what it was sent, and whether it can be reached."""

    def __init__(self) -> None:
        self.in_range = True
        self.answers = True
        self.outlet_1 = False
        self.outlet_2 = False
        self.target = 38.0
        self.actual = 21.5
        self.remaining = 0
        self.writes: list[bytes] = []
        self.clients: list[FakeClient] = []
        self.connect_attempts = 0

    @property
    def client(self) -> FakeClient:
        return self.clients[-1]

    def state_payload(self) -> bytes:
        """Device state (reply to request_device_state): 10 bytes."""
        running = self.outlet_1 or self.outlet_2
        return (bytes([TIMER_RUNNING if running else TIMER_STOPPED]) + temp(self.target) + temp(self.actual)
                + bytes([OUTLET_RUNNING if self.outlet_1 else OUTLET_STOPPED,
                         OUTLET_RUNNING if self.outlet_2 else OUTLET_STOPPED])
                + struct.pack(">H", self.remaining) + bytes([0]))

    def controls_operated_payload(self) -> bytes:
        """Pushed when someone uses the shower's own controls: 11 bytes."""
        running = self.outlet_1 or self.outlet_2
        return (bytes([1, TIMER_RUNNING if running else TIMER_STOPPED]) + temp(self.target) + temp(self.actual)
                + bytes([OUTLET_RUNNING if self.outlet_1 else OUTLET_STOPPED,
                         OUTLET_RUNNING if self.outlet_2 else OUTLET_STOPPED])
                + struct.pack(">H", self.remaining) + bytes([0]))

    def reply_to(self, data: bytes):
        command = data[1]
        if command == 0x07:  # request device state
            return packet(self.state_payload())
        if command == 0x32:  # request technical info: valve 1.2, bt 3.4, ui 7.8
            return packet(struct.pack(">8H", 1, 2, 3, 4, 5, 6, 7, 8))
        if command == 0x87:  # control outlets
            self.outlet_1 = data[6] == OUTLET_RUNNING
            self.outlet_2 = data[7] == OUTLET_RUNNING
            self.target = struct.unpack(">H", data[4:6])[0] / 10
            return packet(bytes([1]))
        return None

    # stand-ins for HA's Bluetooth lookup and bleak-retry-connector

    def ble_device_from_address(self, hass, address, connectable=True):
        if not self.in_range:
            return None
        device = MagicMock()
        device.address = address
        device.name = "Mira N86Sd: Master Bathroom"
        return device

    async def establish_connection(self, client_class, device, name, disconnected_callback=None, **kwargs):
        self.connect_attempts += 1
        client = FakeClient(self, disconnected_callback)
        self.clients.append(client)
        return client

    def patch(self):
        """Patch the integration's Bluetooth access to talk to this shower."""
        return _MultiPatch(
            patch(f"{CONNECTION}.async_ble_device_from_address", side_effect=self.ble_device_from_address),
            patch(f"{CONNECTION}.establish_connection", side_effect=self.establish_connection),
        )


class _MultiPatch:
    def __init__(self, *patches) -> None:
        self._patches = patches

    def __enter__(self):
        for p in self._patches:
            p.start()
        return self

    def __exit__(self, *exc) -> None:
        for p in reversed(self._patches):
            p.stop()
