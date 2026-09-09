English | [简体中文](https://github.com/elpass/hlk2410d-b/blob/main/README_CN.md)
# LD2410D-B BLE Integration

A Home Assistant integration for the HiLink LD2410D-B Bluetooth motion sensor.

## Overview

This integration provides support for the **HLK-2410D-B** Bluetooth motion detection sensors in Home Assistant. These sensors detect both moving and static targets, providing distance and energy measurements for advanced motion detection automation.

## Features

- **Motion Detection**: Real-time detection of moving targets (MOTION sensor)
- **Occupancy Detection**: Static occupancy detection (OCCUPANCY sensor)
- **Distance Measurement**: Moving and static target distance in centimeters
- **Energy Levels**: Target energy readings for both motion and static detection
- **Gate-based Configuration**: 9 configurable detection gates for motion and static detection
- **Bluetooth Discovery**: Automatic device discovery via Bluetooth
- **Local Push**: Real-time updates via local Bluetooth connection

## Supported Models

- **HLK-2410D-B** - New D-series model with Bluetooth

## Installation

### Manual Installation

1. Clone or download this repository
2. Copy the entire folder to your Home Assistant `custom_components` directory:
   ```
   <config>/custom_components/hlk2410d_b/
   ```
3. Restart Home Assistant
4. Go to Settings → Devices & Services → Create Automation
5. Search for "2410" and follow the setup wizard

### HACS Installation

To be added to HACS once published.

## Configuration

The integration uses Bluetooth discovery. Simply add your device through the Home Assistant UI:

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for **2410**
4. Select your device from the discovered list
5. Complete the configuration flow

## Entities

### Sensors
- **Target Distance** - Distance to target (cm)

## Requirements

- **Home Assistant** 2024.1.0 or later
- **Bluetooth Adapter** on your Home Assistant device
- **LD2410D-B sensor** with Bluetooth capability

## Dependencies

- `bleak>=0.21.0`
- `bleak-retry-connector>=2.0.0`
- `bluetooth_adapters` (Home Assistant component / ESP32 C3+ (bluetooth proxy) is Recommend)

## Troubleshooting

### Device Not Found
- Ensure the sensor is powered and in Bluetooth pairing mode
- Check that your Home Assistant device has Bluetooth capability
- Try moving closer to the device or Add an ESP32 Bluetooth Proxy
- Restart Home Assistant

### Connection Issues
- Verify the Bluetooth signal strength
- Clear nearby Bluetooth interference or Add an ESP32 Bluetooth Proxy
- Restart the sensor device
- Check Home Assistant logs for detailed errors

## Development

### Directory Structure
```
hlk2410d_b/
├── __init__.py           # Integration setup and main logic
├── binary_sensor.py      # Binary sensor entities
├── config_flow.py        # Configuration UI flow
├── const.py              # Constants and device names
├── coordinator.py        # Data update coordinator
├── manifest.json         # Integration metadata
├── sensor.py             # Sensor entities
└── strings.json          # Localization strings
```

## License

Licensed under the same terms as Home Assistant (Apache 2.0)

## Support

For issues, questions, or feature requests, please visit:
- [GitHub Issues](https://github.com/elpass/hlk2410d-b/issues)

## Credits

- Original integration: [@megarushing](https://github.com/megarushing/ha-ld2410)
- Home Assistant Bluetooth Framework

## Disclaimer

This is a community-maintained integration and is not affiliated with HiLink or Home Assistant official integrations.

