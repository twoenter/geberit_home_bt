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
            errors=errors
        )
