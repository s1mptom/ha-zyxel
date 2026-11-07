"""Services for the Zyxel integration (SMS send / delete)."""
from __future__ import annotations

import json
import logging

import requests
import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall
import homeassistant.helpers.config_validation as cv

from custom_components.ha_zyxel import sms
from custom_components.ha_zyxel.const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SERVICE_SEND_SMS = "send_sms"
SERVICE_DELETE_SMS = "delete_sms"

# Message State in the unified SMS_Inbox list: 0/1 = received, 2 = sent (outbox).
STATE_SENT = 2
RECEIVED_STATES = (0, 1)

SEND_SMS_SCHEMA = vol.Schema(
    {
        vol.Required("number"): cv.string,
        vol.Required("message"): cv.string,
        # Sent messages sit in the modem's small SMS store; by default we drop
        # them right after a successful send so it never fills up.
        vol.Optional("keep_sent", default=False): cv.boolean,
    }
)

DELETE_SMS_SCHEMA = vol.Schema(
    {
        vol.Optional("scope", default="sent"): vol.In(["sent", "received", "all"]),
    }
)


# --- low-level modem I/O reusing the coordinator's authenticated session ------


def _dal_write(router, method: str, oid: str, params: dict | None = None):
    """Do a DAL write (POST/DELETE) reusing the router session; handle 401 + key rotation.

    The sessionkey rotates on every write — we capture the new one back into the
    router so the coordinator's next poll stays valid. Over HTTPS the modem needs
    no encryption (plaintext).
    """
    body = None
    extra = dict(params or {})
    if method == "POST":
        body = extra.pop("_body", "").encode("utf-8")

    def _do(sessionkey: str):
        url = f"{router.url}/cgi-bin/DAL?oid={oid}&sessionkey={sessionkey}"
        for k, v in extra.items():
            url += f"&{k}={v}"
        rp = dict(router.params)
        headers = dict(rp.pop("headers", {}) or {})
        if method == "POST":
            headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
        resp = requests.request(
            method, url, data=body, headers=headers, timeout=30, **rp
        )
        resp.raise_for_status()
        return resp.json()

    try:
        result = _do(router.sessionkey)
    except requests.exceptions.HTTPError as ex:
        if ex.response is None or ex.response.status_code != 401:
            raise
        if not router.login():
            raise RuntimeError("Zyxel re-login failed") from ex
        result = _do(router.sessionkey)

    if isinstance(result, dict) and result.get("sessionkey"):
        router.sessionkey = result["sessionkey"]
    if not (isinstance(result, dict) and result.get("result") == "ZCFG_SUCCESS"):
        raise RuntimeError(f"Modem rejected {method} {oid}: {result}")
    return result


def _list_messages(router) -> list[dict]:
    """Return the unified SMS list (inbox + sent), each with ObjIndex/State."""
    obj = router.get_json_object("cellwan_sms")
    return (obj or {}).get("SMS_Inbox", []) or []


def _delete_indices(router, indices: list[int]) -> None:
    if not indices:
        return
    idx = ",".join(str(i) for i in indices)
    _dal_write(router, "DELETE", "cellwan_sms", {"objIndex": idx})


def _send_and_maybe_drop(router, payload: dict, keep_sent: bool) -> None:
    """POST the SMS, then (unless keep_sent) delete the resulting sent entries."""
    _dal_write(
        router,
        "POST",
        "cellwan_sms",
        {"timedelay": 1, "_body": json.dumps(payload)},
    )
    if keep_sent:
        return
    # Drop everything currently in the "sent" state (State==2). The user doesn't
    # want sent copies retained, and the store is tiny (~100 slots).
    try:
        sent = [m["ObjIndex"] for m in _list_messages(router) if m.get("State") == STATE_SENT]
        _delete_indices(router, sent)
    except Exception as err:  # noqa: BLE001 - the SMS already went out; cleanup is best-effort
        _LOGGER.warning("SMS sent OK but auto-drop of sent copies failed: %s", err)


# --- service plumbing ---------------------------------------------------------


def _get_router(hass: HomeAssistant):
    for data in hass.data.get(DOMAIN, {}).values():
        if isinstance(data, dict) and data.get("router") is not None:
            return data["router"]
    return None


async def async_register_services(hass: HomeAssistant) -> None:
    """Register integration services once."""

    async def _handle_send_sms(call: ServiceCall) -> None:
        router = _get_router(hass)
        if router is None:
            raise RuntimeError("Zyxel integration is not loaded")
        payload = await hass.async_add_executor_job(
            sms.build_payload, call.data["number"], call.data["message"]
        )
        segments = len(payload["SMS_Content_divData"])
        _LOGGER.info(
            "Sending SMS to %s (%d segment%s, %d chars, UCS2)",
            payload["SMS_To"], segments, "" if segments == 1 else "s",
            payload["SMS_ContentLength"],
        )
        await hass.async_add_executor_job(
            _send_and_maybe_drop, router, payload, call.data["keep_sent"]
        )

    async def _handle_delete_sms(call: ServiceCall) -> None:
        router = _get_router(hass)
        if router is None:
            raise RuntimeError("Zyxel integration is not loaded")
        scope = call.data["scope"]

        def _do():
            msgs = _list_messages(router)
            if scope == "sent":
                idx = [m["ObjIndex"] for m in msgs if m.get("State") == STATE_SENT]
            elif scope == "received":
                idx = [m["ObjIndex"] for m in msgs if m.get("State") in RECEIVED_STATES]
            else:
                idx = [m["ObjIndex"] for m in msgs]
            _delete_indices(router, idx)
            return len(idx)

        deleted = await hass.async_add_executor_job(_do)
        _LOGGER.info("Deleted %d SMS (scope=%s)", deleted, scope)

    if not hass.services.has_service(DOMAIN, SERVICE_SEND_SMS):
        hass.services.async_register(
            DOMAIN, SERVICE_SEND_SMS, _handle_send_sms, schema=SEND_SMS_SCHEMA
        )
    if not hass.services.has_service(DOMAIN, SERVICE_DELETE_SMS):
        hass.services.async_register(
            DOMAIN, SERVICE_DELETE_SMS, _handle_delete_sms, schema=DELETE_SMS_SCHEMA
        )


def async_unregister_services(hass: HomeAssistant) -> None:
    """Remove services when the last entry unloads."""
    if not hass.data.get(DOMAIN):
        hass.services.async_remove(DOMAIN, SERVICE_SEND_SMS)
        hass.services.async_remove(DOMAIN, SERVICE_DELETE_SMS)
