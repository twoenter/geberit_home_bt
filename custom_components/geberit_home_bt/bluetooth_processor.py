import logging
import asyncio
from bleak import BleakClient
from .const import WRITE_HANDLE

_LOGGER = logging.getLogger(__name__)

class BluetoothProcessor:
    def __init__(self, address, device_type="Geberit Toilet"):
        self.address = address
        self.device_type = device_type
        self.client = None
        self.data = None
        self.polling_task = None
        self.watchdog_task = None
        self._char_cache = {}
        self._excluded_chars = set()

    async def connect(self):
        if self.client and self.client.is_connected:
            _LOGGER.debug(f"Already connected to {self.device_type} at {self.address}")
            return

        _LOGGER.debug(f"Connecting to {self.device_type} at {self.address}...")

        self.client = BleakClient(self.address)

        try:
            await self.client.connect()
            _LOGGER.info(f"Connected to {self.device_type} at {self.address}")

            for char in self.client.services.characteristics.values():
                _LOGGER.debug(f"Characteristic found. UUID: {char.uuid}, handle: {char.handle}, properties: {char.properties}")
                if "notify" in char.properties or "indicate" in char.properties:
                    try:
                        await self.client.start_notify(char.handle, self._notification_handler)
                        _LOGGER.info(f"Enabling notify on characteristic: {char.uuid} (handle: {char.handle})")
                    except Exception as e:
                        _LOGGER.warning(f"Failed to start notify on {char.uuid}: {e}")

            # Pas polling-interval aan op basis van type
            interval = 1.0 
            await self.poll_characteristics(interval)

        except asyncio.CancelledError:
            _LOGGER.warning("Connection attempt cancelled.")
            raise
        except Exception as e:
            _LOGGER.warning(f"Initial connection failed: {e}")

    async def disconnect(self):
        if self.polling_task:
            self.polling_task.cancel()
            self.polling_task = None
        if self.client and self.client.is_connected:
            await self.client.disconnect()
            _LOGGER.info(f"Disconnected from {self.device_type} at {self.address}")

    async def start_watchdog(self, retry_interval: float = 5.0):
        async def monitor():
            while True:
                if not self.client or not self.client.is_connected:
                    _LOGGER.info(f"Not connected to {self.device_type}. Attempting to connect...")
                    await self.connect()
                await asyncio.sleep(retry_interval)

        self.watchdog_task = asyncio.create_task(monitor())

    async def write_command(self, value: bytes):
        if self.client and self.client.is_connected:
            await self.client.write_gatt_char(WRITE_HANDLE, value, response=False)
        else:
            _LOGGER.error("Client is not connected; cannot write command")

    def _notification_handler(self, handle, data):
        self.data = data
        _LOGGER.info(f"Notification received from {self.device_type}. Handle: {handle}, value: {data.hex()}")

    async def read_notify(self):
        _LOGGER.debug(f"read_notify() called, returning: {self.data.hex() if self.data else 'None'}")
        return self.data or b""

    async def poll_characteristics(self, interval: float = 0.1):
        if self.polling_task:
            self.polling_task.cancel()

        if not self.client or not self.client.is_connected:
            _LOGGER.warning("Cannot poll characteristics: not connected")
            return

        async def poll():
            while True:
                for char in self.client.services.characteristics.values():
                    key = f"{char.uuid}:{char.handle}"
                    if key in self._excluded_chars:
                        continue
                    if "read" in char.properties:
                        try:
                            value = await self.client.read_gatt_char(char.handle)
                            prev = self._char_cache.get(key)
                            if prev != value:
                                _LOGGER.info(f"[{self.device_type}] State changed. UUID: {char.uuid}, handle: {char.handle}, value: {value.hex()}")
                                self._char_cache[key] = value
                        except Exception as e:
                            if "NotPermitted" in str(e):
                                self._excluded_chars.add(key)
                                _LOGGER.warning(f"Excluded UUID {char.uuid} (handle {char.handle}) due to permission error: {e}")
                            else:
                                _LOGGER.warning(f"Failed to read characteristic {char.uuid} (handle {char.handle}): {e}")
                await asyncio.sleep(interval)

        self.polling_task = asyncio.create_task(poll())
