"""The Zyxel integration."""
import asyncio
import logging
from datetime import timedelta

import async_timeout
import requests
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from custom_components.ha_zyxel.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
    DEFAULT_SCAN_INTERVAL,
    ERROR_BACKOFF_INTERVAL,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

# Block excessive nr7101 debug logging
nr7101_logger = logging.getLogger("nr7101.nr7101")
nr7101_logger.setLevel(logging.WARNING)

from nr7101 import nr7101

PLATFORMS = ["sensor", "button"]


def _get_scan_interval(entry: ConfigEntry) -> int:
    """Resolve the poll interval from options, clamped to the safe range."""
    interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    try:
        interval = int(interval)
    except (TypeError, ValueError):
        interval = DEFAULT_SCAN_INTERVAL
    return max(MIN_SCAN_INTERVAL, min(MAX_SCAN_INTERVAL, interval))


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Apply a changed scan interval without reinstalling (keeps one session)."""
    data = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if not data:
        return
    coordinator = data["coordinator"]
    coordinator.update_interval = timedelta(seconds=_get_scan_interval(entry))
    await coordinator.async_request_refresh()


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Zyxel integration from a config entry."""


    host = entry.data[CONF_HOST]
    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]

    try:
        router = await hass.async_add_executor_job(
            nr7101.NR7101, host, username, password
        )
    except Exception as ex:
        _LOGGER.error("Could not connect to Zyxel router: %s", ex)
        raise ConfigEntryNotReady from ex

    def _set_interval(seconds: int) -> None:
        """Adjust the next-poll interval (coordinator reschedules off this)."""
        coordinator.update_interval = timedelta(seconds=seconds)

    async def async_update_data():
        """Fetch data from the router."""
        try:
            async with async_timeout.timeout(15):
                def get_all_data():
                    # router.get_status() polls 8 separate endpoints
                    # (cellwan_status, Traffic_Status, cardpage_status, lan,
                    # lanhosts, wifi_easy_mesh, one_connect, status) even
                    # though every sensor we expose only reads "cellular"
                    # (cellwan_status). Fetch that one OID directly instead
                    # to cut per-poll modem load 8x.
                    #
                    # get_json_object() has no session recovery of its own
                    # (that retry-with-login lives inside get_status()'s
                    # loop), so replicate it here: on a 401 (session expired
                    # / not yet logged in) log in once and retry.
                    try:
                        cellular = router.get_json_object("cellwan_status")
                    except requests.exceptions.HTTPError as ex:
                        if ex.response is None or ex.response.status_code != 401:
                            raise
                        if not router.login():
                            raise UpdateFailed("Router login failed") from ex
                        cellular = router.get_json_object("cellwan_status")

                    if not cellular:
                        raise UpdateFailed("No data received from router")

                    return {"cellular": cellular}

                data = await hass.async_add_executor_job(get_all_data)
            # Success: make sure we're back on the normal (fast) cadence.
            _set_interval(_get_scan_interval(entry))
            return data
        except asyncio.TimeoutError as err:
            router._session_valid = False
            # Back off so we don't hammer a rebooting/unreachable modem.
            _set_interval(ERROR_BACKOFF_INTERVAL)
            raise UpdateFailed("Router data fetch timed out") from err
        except Exception as err:
            router._session_valid = False
            _set_interval(ERROR_BACKOFF_INTERVAL)
            raise UpdateFailed(f"Error communicating with router: {err}") from err

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
        update_method=async_update_data,
        update_interval=timedelta(seconds=_get_scan_interval(entry)),
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "router": router,
    }

    # Re-apply the interval in place when options change (no new login).
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register the SMS send service (idempotent).
    from custom_components.ha_zyxel.services import async_register_services
    await async_register_services(hass)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, platform)
                for platform in PLATFORMS
            ]
        )
    )
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        from custom_components.ha_zyxel.services import async_unregister_services
        async_unregister_services(hass)

    return unload_ok
