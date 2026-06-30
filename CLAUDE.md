# ha_zyxel — project index

Fork of [zulufoxtrot/ha-zyxel](https://github.com/zulufoxtrot/ha-zyxel) (origin: `s1mptom/ha-zyxel`).
Custom Home Assistant integration for **Zyxel 5G/LTE CPE** (primary target: **NR7302**).
Read-only cellular telemetry — no band scan (`qscan`), no writes except the reboot button.

## What it does
Logs into the modem once, polls `cellwan_status` over the Zyxel DAL API (HTTPS, self-signed)
via the [`nr7101`](https://github.com/pkorpine/nr7101) library, and exposes the fields as HA sensors.

## Data flow
```
config_flow.py  ── user enters host/user/pass ─┐
                                               ▼
__init__.py  ── NR7101(host,user,pass) once ── router (ONE reusable session)
                       │
                       ▼  DataUpdateCoordinator (interval from options)
              router.get_status()  ==  get_json_object("cellwan_status")  → dict
                       │
                       ▼
sensor.py  ── builds entities from the dict every refresh
```

## Files (`custom_components/ha_zyxel/`)
| File | Role |
|------|------|
| `__init__.py` | Entry setup; creates the single `router`; `DataUpdateCoordinator`; `_get_scan_interval()` + options update listener (re-applies interval in place, **no re-login**). |
| `config_flow.py` | Setup form (host/user/pass) **and** `OptionsFlowHandler` (poll interval, 10–300 s). |
| `const.py` | `DOMAIN`, defaults, `DEFAULT/MIN/MAX_SCAN_INTERVAL`, `SCC_SLOTS`. |
| `sensor.py` | All sensors. See breakdown below. |
| `button.py` | Reboot button (the only write action). |
| `translations/*.json` | UI strings for config + options flows. |
| `manifest.json` | Domain, version, `nr7101` requirement (pinned git tag). |

## `sensor.py` map
- `KNOWN_SENSORS` — per-key metadata (name/unit/icon/device_class/state_class) for top-level scalars.
- `_flatten_dict()` — flattens nested dicts to dotted keys; **lists are skipped** (handled explicitly below).
- `_coerce_number()` — casts numeric strings (e.g. bandwidth `"100"`) so `measurement` stats work.
- `ConfiguredZyxelSensor` / `GenericZyxelSensor` — auto-generated from the flattened dict.
- `ZyxelSCCSensor` — fixed **SCC1/SCC2** slots from `SCC_Info[i]`; `unavailable` when the slot is absent.
- `ZyxelNeighbourSensor` — one sensor; state = `len(NBR_Info)`, per-cell detail in attributes.
- `SCC_FIELDS`, `NBR_ATTR_KEYS` — field configs for the two classes above.

## Invariants (do NOT break)
1. **One session.** A single `router` instance is created in `__init__.py` and reused. Never log in per
   poll — the CPE has a small session limit and will start returning 401. The options listener updates
   the interval *in place* (no entry reload) specifically to preserve this.
2. **Read-only.** No `qscan`, no config writes. (Reboot button is the deliberate exception.)
3. **Additive entities.** `unique_id`s are stable; new sensors must not collide with or rename existing
   entity_ids. Same HA device for everything (`_build_device_info`).
4. **Robust to missing data.** Absent keys / variable SCC count / NSA fields in non-NSA mode →
   `unavailable`, never a coordinator crash.

## Spec
Full requirements: `/homeassistant/ha_zyxel_fork_spec.md` on the HA box (HAOS `/config`).

## Test live
Modem at `https://192.168.1.1`. Verify: new sensors populate; interval change applies; **no repeat
logins/401 in the log**; long-term statistics appear for signal sensors.

## Local dev notes
- `python3 -m py_compile custom_components/ha_zyxel/*.py` — quick syntax check (HA not importable locally).
- Linter shows `Import "homeassistant..." could not be resolved` — expected without HA installed; ignore.
- Deploy: copy `custom_components/ha_zyxel/` to HA `/config/custom_components/` and restart HA.
