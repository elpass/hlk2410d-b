"""Constants for the HLK-LD2410D-B integration."""

DOMAIN = "hlk2410d_b"

# ── BLE UUIDs ──
SERVICE_UUID = "0000fff0-0000-1000-8000-00805f9b34fb"
NOTIFY_UUID = "0000fff1-0000-1000-8000-00805f9b34fb"
WRITE_UUID = "0000fff2-0000-1000-8000-00805f9b34fb"

# ── Frame markers ──
FRAME_HEADER = bytes([0xFD, 0xFC, 0xFB, 0xFA])
FRAME_FOOTER = bytes([0x04, 0x03, 0x02, 0x01])

# ── Protocol command words (little-endian 16-bit) ──
CMD_ENABLE_CONFIG = 0x00FF
CMD_END_CONFIG = 0x00FE
CMD_READ_SENSOR_CONFIG = 0x0008
CMD_CONFIG_SENSOR_PARAM = 0x0007
CMD_AUTO_THRESHOLD_GEN = 0x0009
CMD_AUTO_THRESHOLD_PROGRESS = 0x000A
CMD_SAVE_PARAMS = 0x00FD
CMD_RESTART_MODULE = 0x00A3
CMD_SET_SENSITIVITY = 0x00C4
CMD_READ_SENSITIVITY = 0x00D4

# ── Parameter IDs ──
PARAM_MAX_DISTANCE = 0x0001
PARAM_TARGET_DELAY = 0x0004

# ── Default values ──
DEFAULT_MAX_DISTANCE_M = 1.0       # display metres; internal raw = 10
DEFAULT_TARGET_DELAY_S = 10        # seconds
DEFAULT_SENSITIVITY = 3            # 1-5
DEFAULT_GATE_COEFF = 2             # index 2 → module value 5

# ── Gate coefficient mapping  index(1-5) → module value ──
GATE_COEFF_MAP = {1: 1, 2: 5, 3: 10, 4: 15, 5: 20}
GATE_COEFF_REVERSE = {1: 1, 5: 2, 10: 3, 15: 4, 20: 5}

# ── Value ranges ──
MAX_DISTANCE_MIN_RAW = 7          # 0.7 m
MAX_DISTANCE_MAX_RAW = 100        # 10.0 m
TARGET_DELAY_MIN = 0
TARGET_DELAY_MAX = 65535

# ── Device discovery ──
DEVICE_NAME_PATTERN = "HLK-2410D-B"

# ── Operating modes ──
MODE_NORMAL = "normal"
MODE_CONFIG = "config"

# ── Entity keys ──
KEY_MAX_DISTANCE = "max_distance"
KEY_TARGET_DELAY = "target_delay"
KEY_SENSITIVITY = "sensitivity"
KEY_GATE_COEFF = "gate_coeff"
KEY_TARGET_DISTANCE = "target_distance"
KEY_DIAGNOSTIC = "diagnostic"
KEY_BTN_READ = "btn_read"
KEY_BTN_SET = "btn_set"
KEY_BTN_RESTART = "btn_restart"

# ── Timeouts (seconds) ──
BLE_COMMAND_TIMEOUT = 5.0
AUTO_THRESHOLD_POLL_INTERVAL = 2.0

# ── Config-entry data keys ──
CONF_ADDRESS = "address"
CONF_NAME = "name"