DOMAIN = "ha_zyxel"
DEFAULT_NAME = "Zyxel Device"
DEFAULT_HOST = "https://192.168.1.1"
DEFAULT_USERNAME = "admin"

CONF_HOST = "host"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"

# Polling interval (seconds). Floor is 5s by request. Note: the CPE refreshes
# and caches cellwan_status internally roughly every 1-2s, so polling faster
# than that only repeats values while adding load and growing the statistics DB.
# The single session is reused, so a short interval does NOT cause re-logins.
CONF_SCAN_INTERVAL = "scan_interval"
DEFAULT_SCAN_INTERVAL = 5
MIN_SCAN_INTERVAL = 5
MAX_SCAN_INTERVAL = 300

# Number of fixed Secondary Component Carrier slots to expose (SCC1, SCC2).
# Real devices report <= 2; extra carriers (if any) are ignored, missing ones
# report `unavailable`.
SCC_SLOTS = 2
