# Introducing Gaposa LinkIt Hub Integration for Home Assistant

**Bringing Official Gaposa Shades Under Local Control**

We're excited to announce the first Home Assistant integration for the **Gaposa LinkIt Hub** — enabling seamless, local control of motorized roller shades directly within Home Assistant.

## What is Gaposa LinkIt Hub?

Gaposa is a premium Italian manufacturer of motorized roller shade systems. While Gaposa hubs have long been available for home automation, until now there was no direct Home Assistant integration available. Users were limited to workarounds or relied on cloud-based communication — not ideal for those seeking privacy, reliability, and local-first automation.

This integration changes that.

## Why Gaposa LinkIt Over Other Shade Hubs?

**Official Hardware + Better Frequency = Reliable Communication**

Unlike third-party shade control hubs that operate on the 433MHz frequency, official Gaposa hubs use the proprietary **434.15MHz frequency**, offering several advantages:

- 🎯 **Better Signal Integrity**: The dedicated 434.15MHz frequency has less interference from common IoT devices (smart home hubs, wireless doorbells, etc.) that typically broadcast on 433MHz
- 📡 **Optimized Motor Communication**: Gaposa motors are tuned to this specific frequency, ensuring more reliable and responsive commands
- 🔐 **Premium Build Quality**: Official Gaposa hardware is designed and manufactured with reliability as the top priority

## What Can It Do?

✅ **Local Control of Motorized Roller Shades** — Control up to 24 channels of Gaposa shades directly from Home Assistant with zero cloud dependency. All communication happens on your local network.

✅ **Seamless Home Automation Integration** — Create automations to open/close shades based on time, sunset, room occupancy, temperature, or any other Home Assistant trigger. Use them in scenes, scripts, and routines just like any other cover entity.

✅ **Reliable Direct Communication** — Leverages the official 434.15MHz frequency for superior signal stability and motor responsiveness compared to universal third-party hubs, with no intermediary cloud services required.

## How It Works

The integration connects to a **Gaposa LinkIt Hub** via an **IP-to-Serial adapter** (we've tested it with the Global Caché ITach IP2SL). This allows Home Assistant to send commands directly over your local network to the hub, which then communicates with your motorized shades using the proprietary 434.15MHz protocol.

**Key Features:**
- 🏠 **100% Local** — No cloud, no subscriptions, no external dependencies
- ⚙️ **Easy Setup** — Simple config flow makes installation quick and intuitive
- 📱 **Full HA Integration** — Works with automations, scripts, scenes, and dashboards
- 🔒 **Secure** — All communication stays within your local network
- 🧪 **Well-Tested** — Includes comprehensive test suite with 40+ tests

## Getting Started

The integration is available as a **custom repository in HACS**. Installation is straightforward:

1. Add the custom repository to HACS: `https://github.com/max1234-cyber/gaposa_linkit`
2. Search for "Gaposa LinkIt Hub" and install
3. Configure your hub IP address, port, and shade channels
4. Start controlling your shades!

For detailed setup instructions, including how to test your IP-to-Serial adapter connection, see the [full documentation](https://github.com/max1234-cyber/gaposa_linkit/blob/main/README.md).

## Open Source & Community-Driven

This is an **unofficial, community-maintained integration** created to fill the gap in Home Assistant support for official Gaposa products. The project is open source on GitHub and welcomes feedback, bug reports, and contributions from the community.

- 📦 **Repository**: [max1234-cyber/gaposa_linkit](https://github.com/max1234-cyber/gaposa_linkit)
- 🐛 **Report Issues**: [GitHub Issues](https://github.com/max1234-cyber/gaposa_linkit/issues)
- 💬 **Discuss & Share**: [GitHub Discussions](https://github.com/max1234-cyber/gaposa_linkit/discussions)

## Important Note

This integration works exclusively with the **official Gaposa LinkIt Hub** (which has an RJ9 serial port). It is **not compatible** with the Gaposa Rollapp Hub, which lacks the serial port for local communication.

---

**Ready to bring your Gaposa shades into Home Assistant?** Check out the [repository](https://github.com/max1234-cyber/gaposa_linkit) to get started, and don't hesitate to open an issue if you have questions or suggestions!

**Questions? Feedback? Ideas?** We'd love to hear from you. Open a discussion or issue on GitHub — community input drives this project forward.

---

*The Gaposa LinkIt Hub integration is community-maintained and unofficial. Gaposa is not affiliated with or endorsing this project.*
