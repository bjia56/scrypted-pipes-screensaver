import sys
from typing import Any, AsyncGenerator

import scrypted_sdk
from scrypted_sdk import ScryptedDeviceBase, DeviceProvider, StreamService

import maze


class PipesScreensaverPlugin(ScryptedDeviceBase, StreamService, DeviceProvider):
    def __init__(self, nativeId: str = None) -> None:
        super().__init__(nativeId)

    async def getDevice(self, nativeId: str) -> Any:
        # Management ui v2's PtyComponent expects the plugin device to implement
        # DeviceProvider and return the StreamService device via getDevice.
        return self

    async def connectStream(self, input: AsyncGenerator[Any, Any] = None, options: Any = None) -> Any:
        core = scrypted_sdk.systemManager.getDeviceByName("@scrypted/core")
        termsvc = await core.getDevice("terminalservice")
        termsvc_direct = await scrypted_sdk.sdk.connectRPCObject(termsvc)
        return await termsvc_direct.connectStream(input, {
            'cmd': [sys.executable, maze.__file__, '-s', 'THICK'],
        })


def create_scrypted_plugin():
    return PipesScreensaverPlugin()