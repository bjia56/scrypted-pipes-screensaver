import os
import platform
import shutil
from typing import Any, AsyncGenerator
import urllib.request
import zipfile

import scrypted_sdk
from scrypted_sdk import ScryptedDeviceBase, DeviceProvider, StreamService, Callable


MAZE_PATH = os.path.join(os.path.dirname(__file__), 'maze.py')

COSMO_PYTHON_VERSION = "3.13.1"
COSMO_PYTHON_TAG = "cpython-v3.13.1-build.1"
COSMO_PYTHON = f"https://github.com/bjia56/portable-python/releases/download/{COSMO_PYTHON_TAG}/python-{COSMO_PYTHON_VERSION}-cosmo-unknown.zip"
DOWNLOAD_CACHE_BUST = f"{platform.system()}-{platform.machine()}-20241223-1"

APE_ARM64 = "https://cosmo.zip/pub/cosmos/bin/ape-arm64.elf"
APE_X86_64 = "https://cosmo.zip/pub/cosmos/bin/ape-x86_64.elf"
APE_MACOS_X86_64 = "https://cosmo.zip/pub/cosmos/bin/ape-x86_64.macho"

FILES_PATH = os.path.join(os.environ['SCRYPTED_PLUGIN_VOLUME'], 'files')
CACHEBUST_PATH = os.path.join(FILES_PATH, 'cachebust')


def extract_zip(tmp, fullpath):
    print("Extracting", tmp, "to", fullpath)
    with zipfile.ZipFile(tmp, 'r') as z:
        z.extractall(fullpath)


class PipesScreensaverPlugin(ScryptedDeviceBase, StreamService, DeviceProvider):
    def __init__(self, nativeId: str = None) -> None:
        super().__init__(nativeId)

        if self.shouldDownloadPython():
            shutil.rmtree(FILES_PATH, ignore_errors=True)

        self.downloadFile(COSMO_PYTHON, 'py', extract_zip)
        self.exe = os.path.join(os.environ['SCRYPTED_PLUGIN_VOLUME'], 'files', 'py', f"python-{COSMO_PYTHON_VERSION}-cosmo-unknown", 'bin', 'python.com')

        if platform.system() != 'Windows':
            download = None
            if platform.system() == 'Linux':
                if platform.machine() == 'aarch64':
                    download = APE_ARM64
                elif platform.machine() == 'x86_64':
                    download = APE_X86_64
            elif platform.system() == 'Darwin':
                if platform.machine() == 'x86_64':
                    download = APE_MACOS_X86_64

            if download:
                filename = os.path.basename(download)
                self.downloadFile(download, filename)
                os.chmod(os.path.join(FILES_PATH, filename), 0o755)
                self.ape = os.path.join(FILES_PATH, filename)
            else:
                self.ape = None
                os.chmod(self.exe, 0o755)
        else:
            self.ape = None

    def shouldDownloadPython(self) -> bool:
        try:
            if not os.path.exists(CACHEBUST_PATH):
                return True
            with open(CACHEBUST_PATH, 'r') as f:
                return f.read() != DOWNLOAD_CACHE_BUST
        except:
            return True

    def downloadFile(self, url: str, filename: str, extract: Callable[[str, str], None] = None) -> str:
        try:
            fullpath = os.path.join(FILES_PATH, filename)
            if os.path.exists(fullpath):
                return fullpath
            tmp = fullpath + '.tmp'
            print("Creating directory for", tmp)
            os.makedirs(os.path.dirname(fullpath), exist_ok=True)
            print("Downloading", url)
            response = urllib.request.urlopen(url)
            if response.getcode() < 200 or response.getcode() >= 300:
                raise Exception(f"Error downloading")
            read = 0
            with open(tmp, "wb") as f:
                while True:
                    data = response.read(1024 * 1024)
                    if not data:
                        break
                    read += len(data)
                    print("Downloaded", read, "bytes")
                    f.write(data)
            if extract:
                extract(tmp, fullpath)
                os.remove(tmp)
            else:
                os.rename(tmp, fullpath)
            with open(CACHEBUST_PATH, 'w') as f:
                f.write(DOWNLOAD_CACHE_BUST)
            return fullpath
        except:
            print("Error downloading", url)
            import traceback
            traceback.print_exc()
            raise


    async def getDevice(self, nativeId: str) -> Any:
        # Management ui v2's PtyComponent expects the plugin device to implement
        # DeviceProvider and return the StreamService device via getDevice.
        return self

    async def connectStream(self, input: AsyncGenerator[Any, Any] = None, options: Any = None) -> Any:
        core = scrypted_sdk.systemManager.getDeviceByName("@scrypted/core")
        termsvc = await core.getDevice("terminalservice")
        termsvc_direct = await scrypted_sdk.sdk.connectRPCObject(termsvc)
        if self.ape:
            return await termsvc_direct.connectStream(input, {
                'cmd': [self.ape, self.exe, MAZE_PATH, '-s', 'THICK'],
            })
        return await termsvc_direct.connectStream(input, {
            'cmd': [self.exe, MAZE_PATH, '-s', 'THICK'],
        })


def create_scrypted_plugin():
    return PipesScreensaverPlugin()