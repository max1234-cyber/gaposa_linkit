# Gaposa LinkIt Hub

[![hacs-custom](https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge)](https://hacs.xyz/docs/faq/custom_repositories)

An unofficial Home Assistant integration for the **Gaposa LinkIt Hub** that enables local control of motorized roller shades via serial communication. Connect over your local network using an IP-to-Serial adapter, or directly via a USB-to-Serial adapter. Control your shades directly without [...]

## ⚠️ Important: LinkIt Hub Only

**This integration works ONLY with the Gaposa LinkIt Hub.** It does NOT work with the Gaposa Rollapp Hub because the Rollapp Hub does not have an RJ9 serial port for local communication. Make sure [...]

## Features

- **Local Control**: Communicate directly with your Gaposa LinkIt Hub over your local network using IP-based serial adapters, or via a directly attached USB-to-Serial adapter
- **Multiple Shades**: Support for up to 24 channels (3 banks × 8 channels)
- **Simple Configuration**: Easy-to-use config flow for setup and reconfiguration
- **Flexible Connectivity**: Choose between IP (network) or USB (direct) connection during setup
- **No Cloud Dependency**: All communication happens locally on your network
- **Cover Platform**: Full support for Home Assistant's cover entities (open, close, stop)
- **Optimistic State**: Instant feedback in the UI with optimistic state updates

## Requirements

This integration requires:
- A **Gaposa LinkIt Hub** (NOT the Rollapp Hub - must have RJ9 serial port)
- A **serial adapter** to connect the hub to Home Assistant:
  - **IP-to-Serial adapter** for network communication
    - **Tested with**: Global Caché ITach IP2SL
    - Your adapter must be configured according to the [Gaposa LinkIt documentation](https://www.gaposa.it/eng/linkit/)
  - **USB-to-Serial adapter** for direct connection to your Home Assistant host
    - Any standard USB-to-Serial adapter with the correct serial port exposed (e.g. `/dev/ttyUSB0` on Linux, `COM3` on Windows)
- **Home Assistant 2025.1.0** or later
- For IP mode: local network access to the IP-to-Serial adapter

## Installation

### Via HACS (Custom Repository)

This integration is available as a **custom repository** in HACS:

1. Open HACS in Home Assistant
2. Go to **Integrations**
3. Click the three-dot menu (⋮) and select **Custom repositories**
4. Paste this URL: `https://github.com/max1234-cyber/gaposa_linkit`
5. Select **Integration** as the category
6. Search for "Gaposa LinkIt Hub" and install
7. Restart Home Assistant

### Manual Installation

1. Download the [latest release](https://github.com/max1234-cyber/gaposa_linkit/releases)
2. Copy the `gaposa_linkit` folder to your Home Assistant `config/custom_components/` directory
3. Restart Home Assistant

## Configuration

### Testing Your IP-to-Serial Adapter

Before configuring the integration, verify your IP-to-Serial adapter (e.g., Global Caché ITach IP2SL) is working correctly by testing it directly from your Home Assistant host or another machine [...]

#### Prerequisites
- `netcat` (nc) command-line utility installed
- Network connectivity to your adapter's IP address and port

#### Test Commands

Replace `local_ip_address_to_ip2sl_adapter` with your adapter's IP and `port` with your configured port (default: 4999).

**Open cover on channel 2:**
```bash
(printf '\x67\x00\x02\xdd\xb8'; sleep 5) | nc -v -w 5 local_ip_address_to_ip2sl_adapter port
```

**Close cover on channel 2:**
```bash
(printf '\x67\x00\x02\xee\x8b'; sleep 5) | nc -v -w 5 local_ip_address_to_ip2sl_adapter port
```

**Example with IP 192.168.1.100 and port 4999:**
```bash
# Open
(printf '\x67\x00\x02\xdd\xb8'; sleep 5) | nc -v -w 5 192.168.1.100 4999

# Close
(printf '\x67\x00\x02\xee\x8b'; sleep 5) | nc -v -w 5 192.168.1.100 4999
```

If these commands work and your shades respond, your adapter is correctly configured and ready for use with this integration.

### Getting Your Shade Channel Numbers

Before configuring the integration, you need to identify which channels correspond to your paired shades:

1. Open the **Gaposa Rollapp** mobile app
2. Go to **Settings** tab
3. Select **Integration**
4. Note the channel number for each of your paired shades

### Adding the Integration

1. In Home Assistant, go to **Settings** → **Devices & Services** → **Integrations**
2. Click **Create Integration** and search for "Gaposa LinkIt Hub"
3. Select your **Connection Type**:
   - **IP** – for network-attached IP-to-Serial adapters (e.g. Global Caché iTach IP2SL)
   - **USB** – for a USB-to-Serial adapter directly connected to your Home Assistant host
4. Enter the connection-specific details:
   - *IP mode*: **Hub IP Address or Hostname**, **Port** (default: `4999`), and **Timeout** (default: `3` seconds)
   - *USB mode*: **Serial Port** path (e.g. `/dev/ttyUSB0` on Linux, `COM3` on Windows) and **Timeout** (default: `3` seconds)
5. Select the **Channels** for your shades (1–24)
6. Click **Submit**

### Finding Your USB Serial Port

If you are using a USB-to-Serial adapter, plug it into the Home Assistant host first and then identify the exposed serial device:

- **Home Assistant UI**: Go to **Settings** → **System** → **Hardware** → **All Hardware** and look for a newly detected serial device such as `/dev/ttyUSB0` or `/dev/ttyACM0`
- **Linux shell**: Run `ls /dev/ttyUSB* /dev/ttyACM*` before and after plugging in the adapter to see which device appeared
- **Linux kernel log**: Run `dmesg | tail` right after connecting the adapter to see which serial port was assigned

Use the detected device path as the **Serial Port** value when configuring the integration.

### Reconfiguration

You can reconfigure the integration at any time:

1. Go to **Settings** → **Devices & Services** → **Integrations**
2. Find your Gaposa LinkIt Hub integration
3. Click the three-dot menu and select **Reconfigure**

## Usage

Once configured, your shades will appear as **Cover** entities in Home Assistant. You can:

- **Open** the shade: Full-up position
- **Close** the shade: Full-down position
- **Stop** the shade: Pause at current position
- **Tune each channel** from its device page using configuration entities for travel time and custom-position support

Use these in automations, scripts, scenes, and the Home Assistant UI just like any other cover entity.

### Example Automation

```yaml
automation:
  - alias: "Close shades at sunset"
    trigger:
      sun: event_type: sunset
    action:
      service: cover.close_cover
      target:
        entity_id: cover.gaposa_shade_channel_1
```

## Important Notes

### Shade Pairing

Shade pairing must be done directly via the **Gaposa Rollapp** mobile application. Since pairing is a one-time operation that requires physical interaction with the shades, it is intentionally no[...]

### Adapter Configuration

Ensure your IP-to-Serial adapter is properly configured according to the [Gaposa LinkIt documentation](https://www.gaposa.it/eng/linkit/). The adapter must be set to:
- TCP server mode on the port you configure (default: 4999)
- Proper baud rate and serial settings for your LinkIt Hub

### Limitations

- **IP-based communication**: Connect via a network IP-to-Serial adapter (e.g. Global Caché iTach IP2SL)
- **USB-based communication**: Connect via a USB-to-Serial adapter directly attached to your Home Assistant host
- **Read-only feedback**: Current shade position is not reported by the LinkIt Hub; state is optimistically assumed after commands are sent

## Troubleshooting

### Shades not responding

1. Verify your serial adapter is powered on and connected to the LinkIt Hub
2. Check the adapter's IP address and port are correct
3. Ensure your Home Assistant can reach the adapter's IP address
4. Verify the channel numbers match those shown in the Gaposa Rollapp
5. Test connectivity using the netcat commands shown in the [Testing Your IP-to-Serial Adapter](#testing-your-ip-to-serial-adapter) section

### Connection timeouts

1. Check network connectivity between Home Assistant and the serial adapter using ping
2. Verify firewall rules allow communication on your configured port
3. Restart the adapter and try reconfiguring the integration

### Wrong channels assigned

1. Re-check the channel numbers in the Gaposa Rollapp **Settings** → **Integration** tab
2. Use the integration's **Reconfigure** option to update the channel list

## Support & Feedback

- **Found a bug?** Please open an [issue on GitHub](https://github.com/max1234-cyber/gaposa_linkit/issues)
- **Have an improvement idea?** Contributions and feedback are welcome!
- **Questions?** Feel free to open a discussion on the repository

## Credits

This integration is an unofficial project to bring local control of Gaposa LinkIt Hubs to Home Assistant.

## License

This project is licensed under the [Apache License 2.0](LICENSE).

---

**⚠️ Disclaimer**: This is an unofficial integration. Gaposa is not affiliated with or endorsing this project. Use at your own risk. Always test shade movements carefully before using in auto[...]
