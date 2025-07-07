from homeassistant import config_entries
import voluptuous as vol
import re
from .const import DOMAIN

MAC_REGEX = re.compile(r"^([0-9A-Fa-f]{2}:){5}([0-9A-Fa-f]{2})$")

DEVICE_TYPES = ["Geberit Mera Classic", "Geberit Duo Fresh"]

class GeberitConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            mac = user_input.get("address", "").strip()
            device_type = user_input.get("device_type")

            if not MAC_REGEX.match(mac):
                errors["address"] = "invalid_mac"
            elif device_type not in DEVICE_TYPES:
                errors["device_type"] = "invalid_type"
            else:
                return self.async_create_entry(
                    title=device_type,
                    data={
                        "address": mac,
                        "device_type": device_type,
                    }
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("address"): str,
                vol.Required("device_type", default="Geberit Duo Fresh"): vol.In(DEVICE_TYPES)
            }),
            errors=errors,
            description_placeholders={
                "mac_help": "e.g. AA:BB:CC:DD:EE:FF",
                "type_help": "Select your Geberit device type"
            },
        )

    async def async_step_bluetooth(self, discovery_info):
        """Handle a flow initialized by a bluetooth discovery."""
        address = discovery_info.get("address")
        device_type = "Geberit Toilet"  # Of bepaal type op basis van discovery_info

        # Controleer of er al een entry bestaat voor dit adres
        await self.async_set_unique_id(address)
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=f"Geberit ({address})",
            data={
                "address": address,
                "device_type": device_type,
            }
        )
