Kincony KC868 TCP integration for Home Assistant (switch-only, TCP control)

Installation

1. Copy the `custom_components/kincony_kc868_tcp/` directory into your Home Assistant `custom_components` folder.
2. Restart Home Assistant.
3. Go to Settings → Devices & Services → Add Integration → search for “Kincony KC868 TCP”.
4. Enter the host/IP (e.g., `192.168.1.103`) and port (default `4196`). The integration scans the device to detect how many relays are available and validates connectivity before creating the entry.
5. The integration creates switches for each detected relay (defaults to 32 if detection fails). Use the integration’s Options to change the number of exposed channels, and rename/disable entities in the UI as needed.

Install using HACS

1. In HACS, go to Integrations → Custom repositories → add `https://github.com/fiLLLip/ha-kincony-kc868-tcp` with category “Integration”.
2. Install “Kincony KC868 TCP” from HACS.
3. Restart Home Assistant.
4. Go to Settings → Devices & Services → Add Integration → search for “Kincony KC868 TCP”.

Notes

- Only switch entities are exposed. If you want light entities, use Home Assistant’s “Switch as Light” helper to wrap a switch as a light.
- YAML configuration is no longer needed or supported; everything is configured through the UI config flow.
