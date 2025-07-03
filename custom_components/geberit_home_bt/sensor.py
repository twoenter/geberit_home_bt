import logging
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# BLE Characteristics for both Duo Fresh and Mera Classic
CHARACTERISTIC_MAP = {
    "00002a24-0000-1000-8000-00805f9b34fb": "Model Number",
    "00002a25-0000-1000-8000-00805f9b34fb": "Serial Number",
    "00002a26-0000-1000-8000-00805f9b34fb": "Firmware Revision",
    "00002a27-0000-1000-8000-00805f9b34fb": "Hardware Revision",
    "00002a28-0000-1000-8000-00805f9b34fb": "Software Revision",
    "00002a29-0000-1000-8000-00805f9b34fb": "Manufacturer"
}

DEVICE_CLASS_MAP = {
    "Firmware Revision": "firmware",
}


class GeberitStaticSensor(SensorEntity):
    def __init__(
        self, processor, uuid, name, address, serial, model, sw_version=None, hw_version=None, firmware_version=None
    ):
        self._processor = processor
        self._uuid = uuid
        self._address = address
        self._serial = serial  # uniek per apparaat
        self._attr_name = name
        self._attr_unique_id = f"geberit_sensor_{uuid.replace('-', '')}"

        self._attr_device_class = DEVICE_CLASS_MAP.get(name)
        self._attr_unit_of_measurement = UNIT_MAP.get(name)
        self._attr_state_class = STATE_CLASS_MAP.get(name)
        self._model = model
        self._sw_version = sw_version
        self._hw_version = hw_version
        self._firmware_version = firmware_version

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._serial)},
            connections={(dr.CONNECTION_NETWORK_MAC, self._address)},
            manufacturer="Geberit",
            name="Geberit Toilet",
            model=self._model,
            sw_version=self._sw_version,
            hw_version=self._hw_version,
            firmware_version=self._firmware_version,
        )

    async def async_update(self):
        if not self._processor.client or not self._processor.client.is_connected:
            return
        try:
            value = await self._processor.client.read_gatt_char(self._uuid)
            decoded = bytes(value).decode(errors="ignore")
            self._value = decoded
        except Exception as e:
            _LOGGER.warning(f"Failed to read {self._uuid}: {e}")

async def async_setup_entry(hass, config_entry, async_add_entities):
    processor = hass.data[DOMAIN][config_entry.entry_id]
    address = config_entry.data.get("address")
    device_type = config_entry.data.get("device_type", "DuoFresh / Mera")

    characteristic_map = CHARACTERISTIC_MAP

    gatt_data = {}

    if processor.client and processor.client.is_connected:
        for uuid, name in characteristic_map.items():
            try:
                value = await processor.client.read_gatt_char(uuid)
                gatt_data[name] = bytes(value).decode(errors="ignore")
            except Exception as e:
                _LOGGER.warning(f"Failed to read {name} ({uuid}): {e}")

    model_id = gatt_data.get("Model Number", device_type)
    serial = gatt_data.get("Serial Number", address)
    sw_version = gatt_data.get("Software Revision", "")
    hw_version = gatt_data.get("Hardware Revision", "")
    firmware_version = gatt_data.get("Firmware Revision", "")
    manufacturer = gatt_data.get("Manufacturer", "Geberit")

    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        identifiers={(DOMAIN, serial)},
        connections={(dr.CONNECTION_NETWORK_MAC, address)},
        manufacturer=manufacturer,
        name=f"{model_id}",
        model=model_id,
        sw_version=sw_version,
        hw_version=hw_version,
        firmware_version=firmware_version,
        suggested_area="Bathroom",
        via_device=(DOMAIN, address)
    )

    entities = []
    for uuid, name in characteristic_map.items():
        entities.append(
            GeberitStaticSensor(
                processor, uuid, name, address, serial, model_id,
                sw_version=sw_version,
                hw_version=hw_version,
                firmware_version=firmware_version
            )
        )
    async_add_entities(entities)