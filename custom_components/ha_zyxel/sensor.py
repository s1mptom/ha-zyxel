"""Support for Zyxel device sensors."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from custom_components.ha_zyxel.const import DOMAIN, PRESEED_BANDS, SCC_SLOTS

_LOGGER = logging.getLogger(__name__)

# Define some known sensor types for proper configuration
KNOWN_SENSORS = {
    "INTF_RSSI": {
        "name": "Cellular RSSI",
        "unit": "dBm",
        "icon": "mdi:signal",
        "device_class": SensorDeviceClass.SIGNAL_STRENGTH,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    "INTF_PhyCell_ID": {
        "name": "Physical Cell ID",
        "unit": None,
        "icon": "mdi:antenna",
        "device_class": None,
        "state_class": None,
    },
    "INTF_RSRP": {
        "name": "Cellular Reference Signal Received Power",
        "unit": "dBm",
        "icon": "mdi:signal",
        "device_class": SensorDeviceClass.SIGNAL_STRENGTH,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    "INTF_RSRQ": {
        "name": "Cellular Reference Signal Received Quality",
        "unit": "dB",
        "icon": "mdi:signal",
        "device_class": SensorDeviceClass.SIGNAL_STRENGTH,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    "INTF_SINR": {
        "name": "Cellular Signal-to-Noise Ratio",
        "unit": "dB",
        "icon": "mdi:signal",
        "device_class": SensorDeviceClass.SIGNAL_STRENGTH,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    "INTF_MCS": {
        "name": "Cellular Modulation and Coding Scheme",
        "unit": "",
        "icon": "mdi:signal",
        "device_class": None,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    "INTF_CQI": {
        "name": "Cellular Channel Quality Indicator",
        "unit": "",
        "icon": "mdi:signal",
        "device_class": None,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    "INTF_RI": {
        "name": "Cellular Rank Indicator",
        "unit": "",
        "icon": "mdi:signal",
        "device_class": None,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    "INTF_PMI": {
        "name": "Cellular Precoding Matrix Indicator",
        "unit": "",
        "icon": "mdi:signal",
        "device_class": None,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    "NSA_PhyCellID": {
        "name": "NSA Physical Cell ID",
        "unit": None,
        "icon": "mdi:antenna",
        "device_class": None,
        "state_class": None,
    },
    "NSA_RSRP": {
        "name": "NSA Reference Signal Received Power",
        "unit": "dBm",
        "icon": "mdi:signal",
        "device_class": SensorDeviceClass.SIGNAL_STRENGTH,
        "state_class": SensorStateClass.MEASUREMENT
    },
    "NSA_RSRQ": {
        "name": "NSA Reference Signal Received Quality",
        "unit": "dB",
        "icon": "mdi:signal",
        "device_class": SensorDeviceClass.SIGNAL_STRENGTH,
        "state_class": SensorStateClass.MEASUREMENT
    },
    "NSA_RSSI": {
        "name": "NSA Reference Signal Strength Indicator",
        "unit": "dBm",
        "icon": "mdi:signal",
        "device_class": SensorDeviceClass.SIGNAL_STRENGTH,
        "state_class": SensorStateClass.MEASUREMENT
    },
    "NSA_SINR": {
        "name": "NSA Signal-to-Noise Ratio",
        "unit": "dB",
        "icon": "mdi:signal",
        "device_class": SensorDeviceClass.SIGNAL_STRENGTH,
        "state_class": SensorStateClass.MEASUREMENT
    },
    "X_ZYXEL_TEMPERATURE_AMBIENT": {
        "name": "Ambient Temperature",
        "unit": "°C",
        "icon": "mdi:thermometer",
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT
    },
    "X_ZYXEL_TEMPERATURE_SDX": {
        "name": "SDX Temperature",
        "unit": "°C",
        "icon": "mdi:thermometer",
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT
    },
    "X_ZYXEL_TEMPERATURE_CPU0": {
        "name": "CPU Temperature",
        "unit": "°C",
        "icon": "mdi:thermometer",
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT
    },
    "BytesSent": {
        "name": "Bytes Sent",
        "unit": "B",
        "icon": "mdi:numeric-10-box",
        "device_class": SensorDeviceClass.DATA_SIZE,
        "state_class": SensorStateClass.TOTAL_INCREASING,
    },
    "BytesReceived": {
        "name": "Bytes Received",
        "unit": "B",
        "icon": "mdi:numeric-10-box",
        "device_class": SensorDeviceClass.DATA_SIZE,
        "state_class": SensorStateClass.TOTAL_INCREASING,
    },
    # --- Carrier aggregation (primary cell) ---
    "INTF_CA_COMBINATION": {
        "name": "CA Combination",
        "unit": None,
        "icon": "mdi:format-list-bulleted",
        "device_class": None,
        "state_class": None,
    },
    "INTF_Downlink_Bandwidth": {
        "name": "Downlink Bandwidth",
        "unit": "MHz",
        "icon": "mdi:arrow-down-bold",
        "device_class": None,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    "INTF_Uplink_Bandwidth": {
        "name": "Uplink Bandwidth",
        "unit": "MHz",
        "icon": "mdi:arrow-up-bold",
        "device_class": None,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    # --- NSA (5G n78 anchor) ---
    "NSA_Band": {
        "name": "NSA Band",
        "unit": None,
        "icon": "mdi:radio-tower",
        "device_class": None,
        "state_class": None,
    },
    "NSA_RFCN": {
        "name": "NSA RFCN",
        "unit": None,
        "icon": "mdi:radio-tower",
        "device_class": None,
        "state_class": None,
    },
    "NSA_DL_BW": {
        "name": "NSA Downlink Bandwidth",
        "unit": "MHz",
        "icon": "mdi:arrow-down-bold",
        "device_class": None,
        "state_class": SensorStateClass.MEASUREMENT,
    },
}

# Per-SCC (secondary component carrier) fields exposed as fixed SCC1/SCC2 slots.
SCC_FIELDS = {
    "Band": {
        "name": "Band",
        "unit": None,
        "icon": "mdi:radio-tower",
        "device_class": None,
        "state_class": None,
    },
    "RFCN": {
        "name": "RFCN",
        "unit": None,
        "icon": "mdi:radio-tower",
        "device_class": None,
        "state_class": None,
    },
    "RSRP": {
        "name": "RSRP",
        "unit": "dBm",
        "icon": "mdi:signal",
        "device_class": SensorDeviceClass.SIGNAL_STRENGTH,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    "RSRQ": {
        "name": "RSRQ",
        "unit": "dB",
        "icon": "mdi:signal",
        "device_class": SensorDeviceClass.SIGNAL_STRENGTH,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    "SINR": {
        "name": "SINR",
        "unit": "dB",
        "icon": "mdi:signal",
        "device_class": SensorDeviceClass.SIGNAL_STRENGTH,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    "DownlinkBandwidth": {
        "name": "Downlink Bandwidth",
        "unit": "MHz",
        "icon": "mdi:arrow-down-bold",
        "device_class": None,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    "CA_STATE": {
        "name": "CA State",
        "unit": None,
        "icon": "mdi:state-machine",
        "device_class": None,
        "state_class": None,
    },
}

# Attributes copied verbatim from each NBR_Info entry into the neighbour sensor.
NBR_ATTR_KEYS = (
    "NeighbourType",
    "ConnectionMode",
    "PhyCellID",
    "RFCN",
    "RSRP",
    "RSRQ",
    "RSSI",
    "SINR",
)


def _flatten_dict(d: dict, parent_key: str = "") -> dict:
    """Flatten a nested dictionary with dot notation for keys."""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}.{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(_flatten_dict(v, new_key).items())
        else:
            items.append((new_key, v))
    return dict(items)


def _is_value_scalar(value: Any) -> bool:
    """Check if a value is a scalar (string, number, bool)."""
    return isinstance(value, (str, int, float, bool)) or value is None


def _coerce_number(value: Any) -> Any:
    """Cast numeric-looking strings to int/float so `measurement` stats work.

    The CPE reports several numbers as strings (e.g. bandwidth "100"). Leave
    non-numeric values untouched.
    """
    if isinstance(value, str):
        text = value.strip()
        try:
            return int(text)
        except ValueError:
            try:
                return float(text)
            except ValueError:
                return value
    return value


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Zyxel sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    if not coordinator.data:
        return

    sensors = []

    # Process all keys in the JSON and create sensors for them
    # We'll use a flat structure for simplicity
    for key, value in _flatten_dict(coordinator.data).items():
        # Skip non-scalar values
        if not _is_value_scalar(value):
            continue

        # Check if this is a known sensor type
        sensor_config = KNOWN_SENSORS.get(key.split(".")[-1], None)

        if sensor_config:
            # Create a configured sensor for known types
            sensors.append(
                ConfiguredZyxelSensor(
                    coordinator,
                    entry,
                    key,
                    sensor_config
                )
            )
        else:
            # Create a generic sensor for unknown types
            sensors.append(
                GenericZyxelSensor(
                    coordinator,
                    entry,
                    key
                )
            )

    # Fixed SCC1/SCC2 slots — created unconditionally so they report
    # `unavailable` (rather than vanishing) when a carrier is not aggregated.
    for slot in range(SCC_SLOTS):
        for field, config in SCC_FIELDS.items():
            sensors.append(ZyxelSCCSensor(coordinator, entry, slot, field, config))

    # Single neighbour-cells sensor (count + per-cell attributes).
    sensors.append(ZyxelNeighbourSensor(coordinator, entry))

    # Whole-aggregation summary (state "B1+B3+B7+B32+n78", carriers in attrs).
    sensors.append(ZyxelCarriersSensor(coordinator, entry))

    # Per-band sensors: preseeded + previously seen (registry) + current.
    band_prefix = f"{entry.entry_id}_band_"
    known: set[str] = set(PRESEED_BANDS)
    registry = er.async_get(hass)
    for reg_entry in er.async_entries_for_config_entry(registry, entry.entry_id):
        uid = reg_entry.unique_id or ""
        if uid.startswith(band_prefix):
            rest = uid[len(band_prefix):]
            for field in BAND_FIELDS:
                if rest.endswith(f"_{field}") and len(rest) > len(field) + 1:
                    known.add(rest[: -len(field) - 1])
    known.update(c["key"] for c in _carriers(coordinator.data))

    def _band_entities(keys) -> list:
        return [
            ZyxelBandSensor(coordinator, entry, key, field, config)
            for key in sorted(keys, key=_band_sort_key)
            for field, config in BAND_FIELDS.items()
        ]

    sensors.extend(_band_entities(known))

    if sensors:
        async_add_entities(sensors)

    @callback
    def _add_new_bands() -> None:
        """Create band sensors the first time a new band is aggregated."""
        new = {c["key"] for c in _carriers(coordinator.data)} - known
        if new:
            _LOGGER.info("New carrier band(s) seen: %s", ", ".join(sorted(new)))
            known.update(new)
            async_add_entities(_band_entities(new))

    entry.async_on_unload(coordinator.async_add_listener(_add_new_bands))


def _get_cellwan_list(data: Any, key: str) -> list:
    """Return a list field (SCC_Info / NBR_Info) from the status payload.

    get_status() nests cellular fields under a "cellular" key
    ({"cellular": {...}, "traffic": {...}}); older/other firmwares may put them
    at the top level. Check both, prefer "cellular".
    """
    if not isinstance(data, dict):
        return []
    cellular = data.get("cellular")
    if isinstance(cellular, dict) and isinstance(cellular.get(key), list):
        return cellular[key]
    value = data.get(key)
    return value if isinstance(value, list) else []


def _cellular(data: Any) -> dict:
    """Return the cellwan_status object (nested under "cellular" or top-level)."""
    if not isinstance(data, dict):
        return {}
    cellular = data.get("cellular")
    return cellular if isinstance(cellular, dict) else data


def _band_label(raw: Any) -> str | None:
    """Normalise a modem band name to "B3" / "n78"; None for junk.

    Accepts "LTE_BC3", "BC3", "NR5G_N78", "N78". The modem reports "N0",
    "-1" or "" when NR is not attached.
    """
    if not isinstance(raw, str):
        return None
    text = raw.strip().upper()
    for prefix in ("LTE_", "NR5G_"):
        if text.startswith(prefix):
            text = text[len(prefix):]
    if text.startswith("BC") and text[2:].isdigit() and int(text[2:]) > 0:
        return f"B{int(text[2:])}"
    if text.startswith("N") and text[1:].isdigit() and int(text[1:]) > 0:
        return f"n{int(text[1:])}"
    return None


def _band_sort_key(key: str) -> tuple:
    """LTE before NR, then by band number, then twins (n78 before n78_2)."""
    base, _, twin = key.partition("_")
    num = int(base[1:]) if base[1:].isdigit() else 999
    return (base[:1] != "B", num, int(twin) if twin.isdigit() else 1)


def _num(value: Any) -> Any:
    """Number or None (modem sends numbers, numeric strings or "")."""
    value = _coerce_number(value)
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def _carriers(data: Any) -> list[dict]:
    """Every carrier currently in use, from ONE cellwan_status payload.

    Order: LTE anchor (PCC), LTE SCCs, then NR (NSA leg, NR SCCs). Built from
    the same poll, so — unlike INTF_CA_COMBINATION, which lags a poll behind —
    band, width and signal always agree. A band seen twice gets key "n78_2".
    """
    cell = _cellular(data)
    if not cell:
        return []
    raw: list[dict] = []

    band = _band_label(cell.get("INTF_Current_Band"))
    if band:
        raw.append({
            "band": band, "role": "anchor",
            "pci": cell.get("INTF_PhyCell_ID"), "rfcn": _num(cell.get("INTF_RFCN")),
            "bw_mhz": _num(cell.get("INTF_Downlink_Bandwidth")),
            "rsrp": _num(cell.get("INTF_RSRP")), "rsrq": _num(cell.get("INTF_RSRQ")),
            "sinr": _num(cell.get("INTF_SINR")), "rssi": _num(cell.get("INTF_RSSI")),
        })

    nsa_band = _band_label(cell.get("NSA_Band"))
    if (
        cell.get("NSA_Enable")
        and nsa_band
        and cell.get("NSA_PhyCellID") not in (None, "", -1, 0, 65535)
    ):
        raw.append({
            "band": nsa_band, "role": "nsa",
            "pci": cell.get("NSA_PhyCellID"), "rfcn": _num(cell.get("NSA_RFCN")),
            "bw_mhz": _num(cell.get("NSA_DL_BW")),
            "rsrp": _num(cell.get("NSA_RSRP")), "rsrq": _num(cell.get("NSA_RSRQ")),
            "sinr": _num(cell.get("NSA_SINR")), "rssi": None,
        })

    for scc in _get_cellwan_list(data, "SCC_Info"):
        if not isinstance(scc, dict) or scc.get("Enable") is False:
            continue
        band = _band_label(scc.get("Band"))
        if not band:
            continue
        raw.append({
            "band": band, "role": "scc",
            "pci": scc.get("PhysicalCellID"), "rfcn": _num(scc.get("RFCN")),
            "bw_mhz": _num(scc.get("DownlinkBandwidth")),
            "rsrp": _num(scc.get("RSRP")), "rsrq": _num(scc.get("RSRQ")),
            "sinr": _num(scc.get("SINR")), "rssi": _num(scc.get("RSSI")),
        })

    # Stable order: LTE first, anchor/NSA before SCCs of the same RAT.
    role_rank = {"anchor": 0, "nsa": 0, "scc": 1}
    raw.sort(key=lambda c: (c["band"][:1] != "B", role_rank[c["role"]]))
    seen: dict[str, int] = {}
    for carrier in raw:
        n = seen[carrier["band"]] = seen.get(carrier["band"], 0) + 1
        carrier["key"] = carrier["band"] if n == 1 else f"{carrier['band']}_{n}"
    return raw


def _build_device_info(entry: ConfigEntry) -> DeviceInfo:
    """Return the shared device info so every entity lands on one device."""
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=f"Zyxel ({entry.data['host']})",
        manufacturer="Zyxel",
        model="",
    )


class AbstractZyxelSensor(CoordinatorEntity, SensorEntity):
    """Base class for Zyxel device sensors."""

    def __init__(self, coordinator, entry: ConfigEntry, key: str):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._key = key
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = _build_device_info(entry)

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if not self.coordinator.last_update_success:
            return False

        # Check if the key exists in the data
        try:
            self._get_value_from_path()
            return True
        except (KeyError, AttributeError):
            return False

    def _get_value_from_path(self) -> Any:
        """Get a value from nested dictionaries using the flattened key."""
        keys = self._key.split(".")
        value = self.coordinator.data
        for k in keys:
            value = value[k]
        return value


class ConfiguredZyxelSensor(AbstractZyxelSensor):
    """Representation of a configured Zyxel sensor."""

    def __init__(self, coordinator, entry: ConfigEntry, key: str, config: dict):
        """Initialize the sensor."""
        super().__init__(coordinator, entry, key)
        self._config = config
        self._attr_name = f"Zyxel {config['name']}"
        self._attr_native_unit_of_measurement = config["unit"]
        self._attr_icon = config["icon"]
        self._attr_device_class = config["device_class"]
        self._attr_state_class = config["state_class"]

    @property
    def state(self):
        """Return the state of the sensor."""
        try:
            value = self._get_value_from_path()
        except (KeyError, AttributeError):
            return None
        if self._config["state_class"] == SensorStateClass.MEASUREMENT:
            return _coerce_number(value)
        return value


class GenericZyxelSensor(AbstractZyxelSensor):
    """Representation of a generic Zyxel sensor."""

    @property
    def name(self):
        """Return the name of the sensor."""
        name_parts = self._key.split(".")
        return f"Zyxel {'.'.join(name_parts)}"

    @property
    def state(self):
        """Return the state of the sensor."""
        try:
            return self._get_value_from_path()
        except (KeyError, AttributeError):
            return None

    @property
    def icon(self):
        """Return the icon."""
        return "mdi:router-wireless"


class ZyxelSCCSensor(CoordinatorEntity, SensorEntity):
    """One field of a fixed Secondary Component Carrier slot (SCC1/SCC2).

    Slots are positional: SCC_Info[slot]. If the carrier is absent the sensor
    reports `unavailable` instead of disappearing, so dashboards stay stable.
    """

    def __init__(self, coordinator, entry: ConfigEntry, slot: int, field: str, config: dict):
        """Initialize the SCC sensor."""
        super().__init__(coordinator)
        self._slot = slot
        self._field = field
        self._config = config
        label = slot + 1
        self._attr_unique_id = f"{entry.entry_id}_SCC{label}_{field}"
        self._attr_name = f"Zyxel SCC{label} {config['name']}"
        self._attr_native_unit_of_measurement = config["unit"]
        self._attr_icon = config["icon"]
        self._attr_device_class = config["device_class"]
        self._attr_state_class = config["state_class"]
        self._attr_device_info = _build_device_info(entry)

    def _slot_data(self) -> dict | None:
        """Return the dict for this SCC slot, or None if not present."""
        scc_list = _get_cellwan_list(self.coordinator.data, "SCC_Info")
        if self._slot < len(scc_list):
            entry = scc_list[self._slot]
            if isinstance(entry, dict):
                return entry
        return None

    @property
    def available(self) -> bool:
        """Available only when the slot exists and carries this field."""
        if not self.coordinator.last_update_success:
            return False
        data = self._slot_data()
        return data is not None and self._field in data

    @property
    def state(self):
        """Return the field value for this slot."""
        data = self._slot_data()
        if data is None or self._field not in data:
            return None
        value = data[self._field]
        if self._config["state_class"] == SensorStateClass.MEASUREMENT:
            return _coerce_number(value)
        return value


class ZyxelNeighbourSensor(CoordinatorEntity, SensorEntity):
    """Aggregate neighbour-cell sensor.

    NBR_Info has a variable length, so the count is the state and the per-cell
    detail lives in attributes rather than in a fluctuating set of entities.
    """

    _attr_icon = "mdi:antenna"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry: ConfigEntry):
        """Initialize the neighbour-cells sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_neighbour_cells"
        self._attr_name = "Zyxel Neighbour Cells"
        self._attr_device_info = _build_device_info(entry)

    def _neighbours(self) -> list:
        """Return the NBR_Info list (empty if missing/malformed)."""
        return _get_cellwan_list(self.coordinator.data, "NBR_Info")

    @property
    def state(self):
        """Return the number of neighbour cells."""
        return len(self._neighbours())

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the per-neighbour detail."""
        cells = []
        for nbr in self._neighbours():
            if isinstance(nbr, dict):
                cells.append({k: nbr.get(k) for k in NBR_ATTR_KEYS})
        return {"cells": cells}


# Fields exposed per band (`Zyxel B3 RSRP`, ...). Keys index _carriers() dicts.
BAND_FIELDS = {
    "rsrp": {"name": "RSRP", "unit": "dBm", "icon": "mdi:signal",
             "device_class": SensorDeviceClass.SIGNAL_STRENGTH},
    "rsrq": {"name": "RSRQ", "unit": "dB", "icon": "mdi:signal",
             "device_class": SensorDeviceClass.SIGNAL_STRENGTH},
    "sinr": {"name": "SINR", "unit": "dB", "icon": "mdi:signal",
             "device_class": SensorDeviceClass.SIGNAL_STRENGTH},
    "bw_mhz": {"name": "Bandwidth", "unit": "MHz", "icon": "mdi:arrow-expand-horizontal",
               "device_class": None},
}


class ZyxelCarriersSensor(CoordinatorEntity, SensorEntity):
    """The whole aggregation in one sensor.

    State: "B1+B3+B7+B32+n78" (twins as "n78×2"). Attributes: per-carrier list
    plus bandwidth totals. The per-carrier list changes every poll (signal),
    so it is kept out of the recorder; only the state/totals are recorded.
    """

    _attr_icon = "mdi:layers-triple"
    _unrecorded_attributes = frozenset({"carriers"})

    def __init__(self, coordinator, entry: ConfigEntry):
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_carriers"
        self._attr_name = "Zyxel Carriers"
        self._attr_device_info = _build_device_info(entry)

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and bool(
            _carriers(self.coordinator.data)
        )

    @property
    def state(self):
        parts: list[str] = []
        counts: dict[str, int] = {}
        for carrier in _carriers(self.coordinator.data):
            if carrier["band"] not in counts:
                parts.append(carrier["band"])
            counts[carrier["band"]] = counts.get(carrier["band"], 0) + 1
        return "+".join(
            band if counts[band] == 1 else f"{band}×{counts[band]}" for band in parts
        ) or None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        carriers = _carriers(self.coordinator.data)
        lte = [c for c in carriers if c["band"].startswith("B")]
        nr = [c for c in carriers if c["band"].startswith("n")]

        def _bw(items):
            return sum(c["bw_mhz"] or 0 for c in items)

        return {
            "carriers": carriers,
            "lte_count": len(lte),
            "nr_count": len(nr),
            "lte_bw_mhz": _bw(lte),
            "nr_bw_mhz": _bw(nr),
            "total_bw_mhz": _bw(carriers),
        }


class ZyxelBandSensor(CoordinatorEntity, SensorEntity):
    """One field of one band (`Zyxel B3 RSRP`); `unavailable` when not aggregated."""

    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry: ConfigEntry, key: str, field: str, config: dict):
        super().__init__(coordinator)
        self._key = key
        self._field = field
        label = key.replace("_", " #")  # "n78_2" -> "n78 #2"
        self._attr_unique_id = f"{entry.entry_id}_band_{key}_{field}"
        self._attr_name = f"Zyxel {label} {config['name']}"
        self._attr_native_unit_of_measurement = config["unit"]
        self._attr_icon = config["icon"]
        self._attr_device_class = config["device_class"]
        self._attr_device_info = _build_device_info(entry)

    def _carrier(self) -> dict | None:
        for carrier in _carriers(self.coordinator.data):
            if carrier["key"] == self._key:
                return carrier
        return None

    @property
    def available(self) -> bool:
        if not self.coordinator.last_update_success:
            return False
        carrier = self._carrier()
        return carrier is not None and carrier.get(self._field) is not None

    @property
    def native_value(self):
        carrier = self._carrier()
        return carrier.get(self._field) if carrier else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        carrier = self._carrier()
        return {"role": carrier["role"], "pci": carrier["pci"]} if carrier else {}
