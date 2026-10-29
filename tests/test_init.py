"""Tests for the integration in Home Assistant: setup, polling, reconnecting and commands."""

from datetime import timedelta
from unittest.mock import patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNAVAILABLE
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

from custom_components.soakstation.const import DOMAIN
from custom_components.soakstation.coordinator import UPDATE_INTERVAL

from .fake_shower import ADDRESS, CLIENT_ID, CLIENT_SLOT

NAME = "Mira N86Sd: Master Bathroom"
SWITCH_1 = "switch.outlet_1_mira_n86sd_master_bathroom"
SWITCH_2 = "switch.outlet_2_mira_n86sd_master_bathroom"
OUTLET_2 = "binary_sensor.outlet_2_mira_n86sd_master_bathroom"
ACTUAL = "sensor.actual_temperature_mira_n86sd_master_bathroom"
TIMER = "sensor.timer_state_mira_n86sd_master_bathroom"


@pytest.fixture(autouse=True)
def no_bluetooth_callbacks():
    """Record the advertisement callback instead of registering it with HA's Bluetooth."""
    callbacks = []

    def register(hass, callback, matcher, mode):
        callbacks.append(callback)
        return lambda: callbacks.remove(callback)

    with patch("homeassistant.components.bluetooth.async_register_callback", side_effect=register):
        yield callbacks


@pytest.fixture(autouse=True)
def fast_timeouts():
    with patch("custom_components.soakstation.coordinator.RESPONSE_TIMEOUT", 0.05):
        yield


async def setup(hass) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=NAME,
        data={"device_name": NAME, "device_address": ADDRESS,
              "client_id": CLIENT_ID, "client_slot": CLIENT_SLOT},
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)
    return entry


async def poll(hass) -> None:
    async_fire_time_changed(hass, dt_util.utcnow() + UPDATE_INTERVAL + timedelta(seconds=1))
    await hass.async_block_till_done(wait_background_tasks=True)


async def test_setup(hass, shower):
    entry = await setup(hass)

    assert entry.state is ConfigEntryState.LOADED
    assert hass.states.get(SWITCH_1).state == STATE_OFF
    assert hass.states.get(OUTLET_2).state == STATE_OFF
    assert float(hass.states.get(ACTUAL).state) == 21.5
    assert hass.states.get(TIMER).state == "stopped"
    remaining = hass.states.get("sensor.timer_remaining_mira_n86sd_master_bathroom")
    assert remaining.attributes["device_class"] == "duration"
    assert remaining.attributes["unit_of_measurement"] == "s"

    # unique ids unchanged, so existing entities, dashboards and automations keep working
    registry = er.async_get(hass)
    assert registry.async_get(SWITCH_1).unique_id == "CD2CA2C7EA12_outlet_1"
    assert registry.async_get(OUTLET_2).unique_id == "soakstation_outlet2_CD2CA2C7EA12"
    assert registry.async_get(ACTUAL).unique_id == "soakstation_actual_temp_CD2CA2C7EA12"


async def test_setup_retries_when_out_of_range(hass, shower):
    """Out of range at startup: HA keeps retrying instead of giving up."""
    shower.in_range = False
    entry = await setup(hass)
    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_setup_retries_when_device_does_not_answer(hass, shower):
    shower.answers = False
    entry = await setup(hass)
    assert entry.state is ConfigEntryState.SETUP_RETRY
    assert not shower.client.is_connected  # the silent connection was closed


async def test_polling_updates_state(hass, shower):
    await setup(hass)
    shower.actual = 36.4
    await poll(hass)
    assert float(hass.states.get(ACTUAL).state) == 36.4


async def test_reconnects_after_drop(hass, shower):
    """The bug that froze the entities: after a drop, updates must keep arriving."""
    await setup(hass)
    shower.client.drop()
    await hass.async_block_till_done(wait_background_tasks=True)

    assert len(shower.clients) == 2  # reconnected straight away
    assert hass.states.get(ACTUAL).state != STATE_UNAVAILABLE

    shower.actual = 39.0
    await poll(hass)
    assert float(hass.states.get(ACTUAL).state) == 39.0


async def test_unavailable_while_out_of_range_then_recovers(hass, shower, no_bluetooth_callbacks):
    await setup(hass)
    shower.in_range = False
    shower.client.drop()
    await hass.async_block_till_done(wait_background_tasks=True)
    assert hass.states.get(SWITCH_1).state == STATE_UNAVAILABLE
    assert hass.states.get(ACTUAL).state == STATE_UNAVAILABLE

    # still unavailable at the next poll
    await poll(hass)
    assert hass.states.get(ACTUAL).state == STATE_UNAVAILABLE

    # back in range: seeing it advertise triggers a reconnect without waiting for a poll
    shower.in_range = True
    shower.actual = 22.0
    no_bluetooth_callbacks[0](None, None)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert float(hass.states.get(ACTUAL).state) == 22.0


async def test_silent_connection_is_replaced(hass, shower):
    """A connection that stops answering is closed and a fresh one made at the next poll."""
    await setup(hass)
    stale = shower.client
    shower.answers = False
    await poll(hass)
    assert hass.states.get(ACTUAL).state == STATE_UNAVAILABLE
    assert not stale.is_connected

    shower.answers = True
    await poll(hass)
    assert shower.client is not stale
    assert hass.states.get(ACTUAL).state != STATE_UNAVAILABLE


async def test_turn_on_and_off(hass, shower):
    await setup(hass)

    await hass.services.async_call("switch", "turn_on", {"entity_id": SWITCH_2}, blocking=True)
    assert shower.outlet_2 and not shower.outlet_1
    assert shower.target == 38.0  # keeps the shower's own target temperature
    assert hass.states.get(SWITCH_2).state == STATE_ON
    assert hass.states.get(OUTLET_2).state == STATE_ON
    assert hass.states.get(TIMER).state == "running"

    await hass.services.async_call("switch", "turn_on", {"entity_id": SWITCH_1}, blocking=True)
    assert shower.outlet_1 and shower.outlet_2  # the other outlet stays on

    await hass.services.async_call("switch", "turn_off", {"entity_id": SWITCH_2}, blocking=True)
    assert shower.outlet_1 and not shower.outlet_2
    assert hass.states.get(SWITCH_2).state == STATE_OFF


async def test_turn_on_reconnects_first(hass, shower):
    await setup(hass)
    shower.client.is_connected = False  # dropped without a callback
    await hass.services.async_call("switch", "turn_on", {"entity_id": SWITCH_1}, blocking=True)
    assert shower.outlet_1
    assert len(shower.clients) == 2


async def test_turn_on_when_unreachable_raises(hass, shower):
    await setup(hass)
    shower.in_range = False
    shower.client.is_connected = False
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call("switch", "turn_on", {"entity_id": SWITCH_1}, blocking=True)
    assert hass.states.get(SWITCH_1).state == STATE_UNAVAILABLE


async def test_shower_controls_are_pushed(hass, shower):
    """Someone using the shower's own controls shows up without waiting for a poll."""
    await setup(hass)
    shower.outlet_1 = True
    shower.client.notify(bytes([0x40 + CLIENT_SLOT, 0, 11]) + shower.controls_operated_payload())
    await hass.async_block_till_done(wait_background_tasks=True)
    assert hass.states.get(SWITCH_1).state == STATE_ON


async def test_unload_disconnects_and_stops_polling(hass, shower, no_bluetooth_callbacks):
    entry = await setup(hass)
    client = shower.client
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)

    assert entry.state is ConfigEntryState.NOT_LOADED
    assert not client.is_connected
    assert no_bluetooth_callbacks == []

    writes = len(shower.writes)
    await poll(hass)
    assert len(shower.writes) == writes
    assert len(shower.clients) == 1  # no reconnect after a deliberate disconnect
