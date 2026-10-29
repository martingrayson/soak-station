"""Tests for parsing the packets the device sends."""

import struct

from custom_components.soakstation.mira.helpers.connection import Connection
from custom_components.soakstation.mira.helpers.data_model import (
    SoakStationData,
    SoakStationMetadata,
    TimerState,
)
from custom_components.soakstation.mira.helpers.notifications import Notifications

from .fake_shower import FakeShower, packet


def parse(payload: bytes):
    model, metadata = SoakStationData(), SoakStationMetadata()
    Notifications(model=model, metadata=metadata).handle_packet(1, len(payload), bytearray(payload))
    return model, metadata


def test_device_state_off():
    """The timer state is byte 0: an idle shower set to 38 °C is stopped, not running."""
    shower = FakeShower()
    model, _ = parse(shower.state_payload())

    assert model.timer_state is TimerState.STOPPED
    assert model.target_temp == 38.0
    assert model.actual_temp == 21.5
    assert model.outlet_1_on is False
    assert model.outlet_2_on is False


def test_device_state_running():
    shower = FakeShower()
    shower.outlet_2, shower.target, shower.actual, shower.remaining = True, 40.5, 39.8, 300
    model, _ = parse(shower.state_payload())

    assert model.timer_state is TimerState.RUNNING
    assert model.target_temp == 40.5
    assert model.actual_temp == 39.8
    assert model.outlet_1_on is False
    assert model.outlet_2_on is True
    assert model.remaining_seconds == 300


def test_controls_operated():
    shower = FakeShower()
    shower.outlet_1 = True
    model, _ = parse(shower.controls_operated_payload())

    assert model.timer_state is TimerState.RUNNING
    assert model.outlet_1_on is True
    assert model.outlet_2_on is False


def test_technical_info_versions():
    """valve = words 0-1, Bluetooth = words 2-3, UI = words 6-7."""
    _, metadata = parse(struct.pack(">8H", 1, 2, 3, 4, 5, 6, 7, 8))

    assert metadata.valve_sw_version == "1.2"
    assert metadata.bt_sw_version == "3.4"
    assert metadata.ui_sw_version == "7.8"
    assert metadata.get_device_info()["sw_version"] == "v1.2/b3.4/u7.8"


def test_device_info_without_versions():
    metadata = SoakStationMetadata()
    metadata.update_device_identity(name="Shower", manufacturer="Mira", model=None, device_address="AA")
    assert metadata.get_device_info()["sw_version"] is None


def test_split_packet_is_reassembled(hass):
    """A 16-byte payload arrives as a 19-byte packet; BLE may split it across notifications."""
    connection = Connection(hass, "AA:BB")
    metadata = SoakStationMetadata()
    connection._notifications = Notifications(metadata=metadata)

    data = packet(struct.pack(">8H", 1, 2, 3, 4, 5, 6, 7, 8))
    connection._handle_raw_notification(None, bytearray(data[:10]))
    assert metadata.valve_sw_version is None
    connection._handle_raw_notification(None, bytearray(data[10:]))
    assert metadata.valve_sw_version == "1.2"
