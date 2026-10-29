# CHANGELOG


## v0.1.1 (2026-10-29)

### Bug Fixes

- Keep the shower connection alive and recover from drops
  ([`8b30df0`](https://github.com/martingrayson/soak-station/commit/8b30df0254e707e38074a87ce459892f0af40c2b))

The connection froze after the first drop: reconnecting never re-subscribed to notifications, most
  errors never triggered a reconnect, and a shower out of range at startup failed setup for good
  (the Ensuite had been unavailable for 60 days).

- connect with bleak-retry-connector (retries, GATT cache, best adapter or proxy), notice drops
  through the disconnected callback, and re-subscribe to notifications on every connect - a
  DataUpdateCoordinator polls every 20 s, reconnecting first when needed; a drop reconnects straight
  away, a connection that stops answering is replaced, and entities are unavailable while the shower
  can't be reached - reconnect as soon as an unreachable shower advertises again - setup raises
  ConfigEntryNotReady so Home Assistant keeps retrying - switching an outlet reconnects if needed,
  waits for the shower to confirm and raises an error in Home Assistant when it can't - unloading
  stops polling and disconnects - entities keep their names and unique ids

Also fixes two parsing bugs: the timer state was read from the target temperature's high byte (so it
  always said running), and the Bluetooth and UI firmware versions were swapped.

Tests use a fake shower that speaks the device's protocol.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>

Claude-Session: https://claude.ai/code/session_018ZK9daMxG7vmV6TdDt6LU6

- Report the time left as a duration
  ([`a1b41a7`](https://github.com/martingrayson/soak-station/commit/a1b41a7ae2b6d6c51783de41e4031d1b6e8a2362))

So Home Assistant shows it as minutes and seconds instead of a bare count.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>

Claude-Session: https://claude.ai/code/session_018ZK9daMxG7vmV6TdDt6LU6

### Continuous Integration

- Run the tests and release with semantic-release
  ([`9c0de0f`](https://github.com/martingrayson/soak-station/commit/9c0de0f31a5959b5f09a7e66efdc7f9b60862fb0))

The workflow installed the project with Poetry, which this pyproject isn't set up for, so it failed
  before the tests ran. Install the test dependencies from requirements_test.txt on Python 3.13
  instead, run the tests on pull requests too, and only release from main once they pass.

Configure semantic-release to bump pyproject.toml and manifest.json, write CHANGELOG.md and tag the
  release, replacing the missing update_manifest.py script. Drop the stray trailing spaces from the
  CHANGELOG.md and .pre-commit-config.yaml filenames.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>

Claude-Session: https://claude.ai/code/session_018ZK9daMxG7vmV6TdDt6LU6

### Testing

- Run the suite with Home Assistant's test harness
  ([`fa678b1`](https://github.com/martingrayson/soak-station/commit/fa678b1cc194f2d68c098895196cd90d81ab1694))

Use pytest-homeassistant-custom-component (asyncio auto mode), make custom_components a regular
  package so HA's loader finds the integration under an editable install, and fix the clamp test:
  1000 °C fits in two bytes, 7000 °C is what overflows.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>

Claude-Session: https://claude.ai/code/session_018ZK9daMxG7vmV6TdDt6LU6


## v0.1.0 (2026-10-29)
