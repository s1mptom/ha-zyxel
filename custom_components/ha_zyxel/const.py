DOMAIN = "ha_zyxel"
DEFAULT_NAME = "Zyxel Device"
DEFAULT_HOST = "https://192.168.1.1"
DEFAULT_USERNAME = "admin"

CONF_HOST = "host"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"

# Polling interval (seconds). Note: the CPE refreshes and caches cellwan_status
# internally roughly every 1-2s, so polling faster than that only repeats
# values while adding load. The single session is reused, so a short interval
# does NOT cause re-logins. Since the coordinator now fetches only the single
# cellwan_status OID per poll (not all 8 nr7101 endpoints), 1s is safe.
CONF_SCAN_INTERVAL = "scan_interval"
DEFAULT_SCAN_INTERVAL = 10
MIN_SCAN_INTERVAL = 1
MAX_SCAN_INTERVAL = 300

# On a failed poll (modem rebooting / unreachable) back off to this interval
# instead of hammering it every few seconds. Restored to the normal interval on
# the first successful poll.
ERROR_BACKOFF_INTERVAL = 60

# Number of fixed Secondary Component Carrier slots to expose (SCC1..SCC4).
# SCC_Info lists every secondary carrier (LTE and NR) — 3 LTE SCCs are real
# (e.g. BC1+BC3+BC7+BC32 + n78), so 2 slots silently dropped one. Missing
# slots report `unavailable`.
SCC_SLOTS = 4

# Per-band sensors (`Zyxel B3 RSRP`, `Zyxel n78 SINR`, ...). Unlike the
# positional SCC slots, a band sensor always means the same carrier, so its
# history is meaningful. These bands are created up front so dashboards can
# reference them even before they are first aggregated; any other band is
# added on the fly the first time it shows up (and recreated from the entity
# registry on later starts). A band aggregated twice (n78 NSA + n78 SCC)
# gets a `_2` twin.
PRESEED_BANDS = (
    "B1", "B3", "B7", "B8", "B20", "B28", "B32",
    "n1", "n28", "n78", "n78_2",
)
