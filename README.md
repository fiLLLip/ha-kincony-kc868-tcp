Installation

1. Copy the `custom_components/kincony-sha/` directory into your Home Assistant `custom_components` folder.
2. Restart Home Assistant.
3. Go to Settings → Devices & Services → Add Integration → search for “Kincony Sha”.
4. Enter the host/IP (e.g., `192.168.1.103`) and port (default `4196`). The integration scans the device to detect how many relays are available and validates connectivity before creating the entry.
5. The integration creates switches for each detected relay (defaults to 32 if detection fails). Use the integration’s Options to change the number of exposed channels, and rename/disable entities in the UI as needed.

Notes

- Only switch entities are exposed. If you want light entities, use Home Assistant’s “Switch as Light” helper to wrap a switch as a light.
- YAML configuration is no longer needed or supported; everything is configured through the UI config flow.
