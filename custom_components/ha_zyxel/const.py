DOMAIN = "ha_zyxel"
DEFAULT_NAME = "Zyxel Device"
DEFAULT_HOST = "https://192.168.1.1"
DEFAULT_USERNAME = "admin"

CONF_HOST = "host"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"

# Polling interval (seconds). The hard floor protects the CPE management SoC:
# it refreshes/caches cellwan_status internally every ~1-2s, so polling faster
# only repeats values, adds load and bloats the statistics DB.
CONF_SCAN_INTERVAL = "scan_interval"
DEFAULT_SCAN_INTERVAL = 30
MIN_SCAN_INTERVAL = 10
MAX_SCAN_INTERVAL = 300

# Number of fixed Secondary Component Carrier slots to expose (SCC1, SCC2).
# Real devices report <= 2; extra carriers (if any) are ignored, missing ones
# report `unavailable`.
SCC_SLOTS = 2
