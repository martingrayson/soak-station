
# 🚿 SoakStation

**SoakStation** is a custom [Home Assistant](https://www.home-assistant.io/) integration that allows you to monitor and control **Mira Bluetooth-enabled smart showers and baths**.

It provides real-time access to device state, temperature readings, and timer data, all accessible as native Home Assistant entities.


> ⚠️ This project is heavily inspired by and based on [alexpilotti/python-miramode](https://github.com/alexpilotti/python-miramode). Many thanks to [@alexpilotti](https://github.com/alexpilotti) for reverse-engineering the Mira protocol.



## 🔧 Features

- 💧 Detect when outlets are running (shower/bath flow).
- 🌡️ Report both **target** and **actual** water temperatures.
- ⏲️ Monitor remaining timer duration.
- 📶 Uses Bluetooth Low Energy (BLE) to communicate locally.
- 🔐 Built-in pairing mechanism with Mira's client-slot system.



## 📦 Installation

1. Place this repo under your Home Assistant config directory:

   ```bash
   /config/custom_components/soak_station/
   ```

2. Ensure Bluetooth is supported and enabled on your host.

3. Restart Home Assistant.

4. Go to **Settings > Devices & Services > Integrations** → **+ Add Integration** → Search for `SoakStation`.

5. Follow the pairing wizard. Ensure your Mira device is in **pairing mode**.



## 🧪 Exposed Entities

| Entity Type        | Description                                    |
|--------------------|------------------------------------------------|
| `binary_sensor`    | Outlet 1 & 2 state (running or off)            |
| `sensor`           | Target temp, actual temp, timer state & time   |



## 💡 Usage Example

Once installed, you can:

- Automate alerts if the shower runs too long
- Show water temperature in a dashboard
- Pause the bath timer if the room gets too cold (via automation)



## 🧰 Troubleshooting

- Ensure your Mira device is in **pairing mode** (usually by holding the control dial/button).
- BLE range matters — ensure your Home Assistant host is nearby.
- Some USB BLE adapters may require additional permissions or setup on Linux.



## 🤝 Acknowledgements

This integration builds upon:

- [python-miramode](https://github.com/alexpilotti/python-miramode) by [@alexpilotti](https://github.com/alexpilotti)
- [Home Assistant Bluetooth integration framework](https://www.home-assistant.io/integrations/bluetooth/)
- [Bleak](https://github.com/hbldh/bleak) for low-level BLE communication



## 📜 License

MIT License



## 🛠 Maintainer

Built by [@martingrayson](https://github.com/martingrayson)
Issues and PRs welcome!
