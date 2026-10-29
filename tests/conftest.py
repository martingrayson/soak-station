"""Shared fixtures."""

import pytest

from .fake_shower import FakeShower


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Let Home Assistant load the integration from custom_components/."""
    yield


@pytest.fixture
def shower():
    """A fake shower, in range, wired into the integration's Bluetooth access."""
    shower = FakeShower()
    with shower.patch():
        yield shower
