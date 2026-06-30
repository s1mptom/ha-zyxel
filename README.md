# ha-zyxel

<img src="https://raw.githubusercontent.com/zulufoxtrot/ha-zyxel/refs/heads/main/resources/logo.png" alt="Zyxel Logo" width="128"/>

> 📢 🤓 **This project is looking for maintainers** 📢 🤓
> 
> If you are interested, get in touch!

__Home Assistant integration for Zyxel devices__

<img src="https://raw.githubusercontent.com/zulufoxtrot/ha-zyxel/refs/heads/main/resources/screenshot.png" alt="Zyxel Logo" />

[![Open ha-zyxel on Home Assistant Community Store (HACS)](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=zulufoxtrot&repository=ha-zyxel&category=integration)

## Supported devices

Confirmed working on:

- AX7501-B0
- FWA505
- FWA510
- FWA710 5G V2
- LTE3202-M437
- LTE7490-M904
- LTE5398-M904
- NR5103E
- NR5103v2
- NR5307
- NR7101
- NR7102
- NR7302
- VMG3625-T50B
- VMG4005-B50A
- VMG8825-T50

Potentially compatible with a lot more devices.
If you do test and find out your device is working, please submit an issue or a pull request and I'll add it to the list.

## Installation

Prerequisites:

1. The device must be reachable from your home assistant instance (they need to be on the same local network)
2. HTTP access must be enabled in the device's settings (it is the case by default)

### Install via HACS (recommended)

1. Install HACS
2. Click the big blue button above
3. Click Download and confirm
4. Restart HA

### Install manually

1. SSH into your HA instance
3. `git clone https://github.com/zulufoxtrot/ha-zyxel`
2. Navigate to `ha-zyxel/custom_components`
4. Copy `ha_zyxel` to your HA instance's `custom_components` directory
4. Restart your HA instance

## Adding a device

1. Go to HA Settings > Devices & Services.
2. Click Add Integration.
3. Search for Zyxel.
4. Select the Zyxel integration.
5. In Host, type your hostname IP, usually something like https://192.168.1.1 (⚠️ enter the full URL scheme with `https://`)
6. Type your admin username and password
7. Click Submit.

If connection fails, try with `http://` instead of `https://`.

## Adding cards to your dashboard

Add [this code](resources/card_example.yml) to your dashboard to add the cards pictured above. Follow the instructions from the animation below.

Note: the Mushroom card extension is required for the above code to work.

![](resources/import_demo.gif)

## Configuring the poll interval

After adding the device you can change how often it is polled:

1. Go to **Settings > Devices & Services > Zyxel > Configure**.
2. Set the **Polling interval** (seconds).

Range: **5–300 s**, default **5 s**. Note: the CPE refreshes its cellular
statistics internally only every ~1–2 s and caches them, so polling faster than
that just repeats values, adds load and bloats the statistics database. Changes
apply immediately, without reinstalling the integration and without re-logging
into the modem (the single session is preserved, so a short interval does not
trigger session-limit 401s).

## Available entities

In theory, all scalar items listed [here](https://github.com/pkorpine/nr7101?tab=readme-ov-file#example-output) are available as entities. They are generated dynamically and depend on what the device exposes.

In addition, this fork surfaces fields that the modem returns as nested objects/lists:

- **Carrier aggregation (primary):** `CA Combination` plus downlink/uplink bandwidth.
- **NSA (5G n78 anchor):** band, RFCN, physical cell ID, RSRP/RSRQ/SINR and downlink bandwidth.
- **Secondary Component Carriers** as fixed slots **SCC1** and **SCC2** (band, RFCN, RSRP, RSRQ, SINR, downlink bandwidth, CA state). A slot that the modem isn't currently aggregating reports `unavailable` rather than disappearing, so dashboards stay stable.
- **Neighbour Cells:** a single sensor whose state is the number of detected neighbours; per-cell details (type, mode, PCI, RFCN, RSRP, RSRQ, RSSI, SINR) are in its attributes.

Signal-quality sensors (RSRP/RSRQ/SINR/RSSI/bandwidth) carry `state_class: measurement` with proper device classes and units, so Home Assistant keeps long-term statistics and charts them natively.

> This integration is **read-only**: it polls cellular status and never triggers a band scan (`qscan`) or writes to the modem.

## Support

Please submit an [issue](https://github.com/zulufoxtrot/ha-zyxel/issues).

## Credits

This integration uses the [n7101 library](https://github.com/pkorpine/nr7101) by pkorpine.
