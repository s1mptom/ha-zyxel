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
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from custom_components.ha_zyxel.const import DOMAIN, SCC_SLOTS

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

    if sensors:
        async_add_entities(sensors)


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
        scc_list = (self.coordinator.data or {}).get("SCC_Info")
        if isinstance(scc_list, list) and self._slot < len(scc_list):
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
        nbr = (self.coordinator.data or {}).get("NBR_Info")
        return nbr if isinstance(nbr, list) else []

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
