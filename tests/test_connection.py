"""Tests for the BLE connection: connecting, dropping and reconnecting."""

import asyncio

import pytest

from custom_components.soakstation.mira.helpers.connection import Connection
from custom_components.soakstation.mira.helpers.data_model import SoakStationData, SoakStationMetadata
from custom_components.soakstation.mira.helpers.notifications import Notifications

from .fake_shower import ADDRESS, CLIENT_ID, CLIENT_SLOT


async def make_connection(hass, subscribe=True):
    connection = Connection(hass, ADDRESS, CLIENT_ID, CLIENT_SLOT)
    model = SoakStationData()
    if subscribe:
        await connection.subscribe(Notifications(model=model, metadata=SoakStationMetadata()))
    return connection, model


async def test_connect_subscribes_to_notifications(hass, shower):
    connection, model = await make_connection(hass)
    await connection.connect()

    assert connection.is_connected
    assert shower.client.notify_starts == 1

    await connection.request_device_state()
    await asyncio.sleep(0)
    assert model.actual_temp == 21.5


async def test_reconnect_resubscribes_to_notifications(hass, shower):
    """After a drop, the new connection must listen to the device again."""
    connection, model = await make_connection(hass)
    await connection.connect()
    shower.client.drop()
    assert not connection.is_connected

    await connection.connect()
    assert len(shower.clients) == 2
    assert shower.client.notify_starts == 1

    shower.actual = 37.9
    await connection.request_device_state()
    await asyncio.sleep(0)
    assert model.actual_temp == 37.9


async def test_connect_when_already_connected_does_nothing(hass, shower):
    connection, _ = await make_connection(hass)
    await connection.connect()
    await connection.connect()
    assert shower.connect_attempts == 1


async def test_concurrent_connects_make_one_connection(hass, shower):
    connection, _ = await make_connection(hass)
    await asyncio.gather(connection.connect(), connection.connect(), connection.connect())
    assert shower.connect_attempts == 1


async def test_connect_raises_when_device_out_of_range(hass, shower):
    shower.in_range = False
    connection, _ = await make_connection(hass)
    with pytest.raises(ConnectionError):
        await connection.connect()
    assert shower.connect_attempts == 0


async def test_disconnect_callback_on_unexpected_drop_only(hass, shower):
    connection, _ = await make_connection(hass)
    drops = []
    connection.set_disconnect_callback(lambda: drops.append(1))

    await connection.connect()
    shower.client.drop()
    assert drops == [1]

    # a deliberate disconnect doesn't count, and nor does a late callback from it
    await connection.connect()
    old = shower.client
    await connection.disconnect()
    old.disconnected_callback(old)
    assert drops == [1]


async def test_write_when_disconnected_raises(hass, shower):
    connection, _ = await make_connection(hass)
    with pytest.raises(ConnectionError):
        await connection.request_device_state()

    await connection.connect()
    shower.client.drop()
    with pytest.raises(ConnectionError):
        await connection.request_device_state()


async def test_pairing_connection_does_not_subscribe(hass, shower):
    """Pairing manages its own notification subscription."""
    connection, _ = await make_connection(hass, subscribe=False)
    await connection.connect()
    assert shower.client.notify_starts == 0
