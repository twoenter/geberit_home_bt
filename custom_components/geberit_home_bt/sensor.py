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


import logging
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

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
        self, processor, uuid, name, address, serial, model, value=None,
        sw_version=None, hw_version=None, device_type=None
    ):
        self._processor = processor
        self._uuid = uuid
        self._address = address
        self._serial = serial
        self._model = model
        self._sw_version = sw_version
        self._hw_version = hw_version
        self._device_type = device_type
        self._attr_native_value = value

        self._attr_name = name
        self._attr_unique_id = f"geberit_sensor_{serial}_{uuid.replace('-', '')}"

        # Optional: classify the sensor as diagnostic
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

        # Optional: assign device class if known (e.g. firmware)
        self._attr_device_class = DEVICE_CLASS_MAP.get(name)

    @property
    def native_value(self):
        return self._attr_native_value

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers = {(DOMAIN, self._serial)},
            connections = {(dr.CONNECTION_NETWORK_MAC, self._address)},
            manufacturer = "Geberit",
            name = self._device_type or self._model,
            model = self._model,
            sw_version = self._sw_version,
            hw_version = self._hw_version,
        )

    async def async_update(self):
        if not self._processor.client or not self._processor.client.is_connected:
            return
        try:
            value = await self._processor.client.read_gatt_char(self._uuid)
            decoded = bytes(value).decode(errors="ignore")
            self._attr_native_value = decoded
        except Exception as e:
            _LOGGER.warning(f"Failed to read {self._uuid}: {e}")







async def async_setup_entry(hass, config_entry, async_add_entities):
    processor = hass.data[DOMAIN][config_entry.entry_id]
    address = config_entry.data.get("address")
    device_type = config_entry.data.get("device_type", "Geberit Duo Fresh")

    gatt_data = {}

    # Probeer alle gedefinieerde BLE-characteristics op te halen
    if processor.client and processor.client.is_connected:
        for uuid, name in CHARACTERISTIC_MAP.items():
            try:
                value = await processor.client.read_gatt_char(uuid)
                decoded = bytes(value).decode(errors="ignore")
                gatt_data[name] = decoded
            except Exception as e:
                _LOGGER.warning(f"Failed to read {name} ({uuid}): {e}")
    else:
        _LOGGER.warning("BLE client is not connected during setup. Sensors may initialize with empty values.")

    # Bepaal apparaat-informatie met fallbacks
    model_id = gatt_data.get("Model Number", device_type)
    serial = gatt_data.get("Serial Number") or address or "unknown_serial"
    sw_version = gatt_data.get("Software Revision", "0")
    hw_version = gatt_data.get("Hardware Revision", "0")

    entities = []
    for uuid, name in CHARACTERISTIC_MAP.items():
        value = gatt_data.get(name)  # Kan ook None zijn
        sensor = GeberitStaticSensor(
            processor=processor,
            uuid=uuid,
            name=name,
            address=address,
            serial=serial,
            model=model_id,
            value=value,
            sw_version=sw_version,
            hw_version=hw_version,
            device_type=device_type
        )
        entities.append(sensor)

    async_add_entities(entities)
