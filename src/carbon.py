import asyncio
import json
from dataclasses import asdict, dataclass

import aiohttp

STATUS = {
    1: "Preparing",
    16: "Preparing",
    21: "Preparing",
    13: "Printing",
    9: "Complete",
    0: "Idle",
}


@dataclass
class Stats:
    nozzle_temp: float = 0.0
    bed_temp: float = 0.0
    enclosure_temp: float = 0.0
    target_nozzle_temp: float = 0.0
    target_bed_temp: float = 0.0
    target_enclosure_temp: float = 0.0
    z_offset: float = 0.0
    model_fan_speed: int = 0
    aux_fan_speed: int = 0
    box_fan_speed: int = 0
    progress: float = 0.0
    print_status: str = "Unknown"
    current_layer: int = 0
    total_layers: int = 0
    print_speed: str = "0%"
    elapsed_time: str = "0"
    remaining_time: str = "0"


class CarbonData:
    target: str = None
    url = "ws://{self.target}:3030/websocket"
    data = Stats()
    error: str = None
    _video: str = "http://{self.target}:3031/video"

    @getattr
    def to_dict(self) -> dict:
        return asdict(self.data)

    @getattr
    def video(self) -> str:
        return self._video.format()

    def __init__(self, target: str = None) -> None:
        self.target = target
        asyncio.create_task(self.connect())

    async def connect(self, timeout: int = 0) -> None:
        session = aiohttp.ClientSession()
        try:
            while not self.target:
                await asyncio.sleep(5)
            connection = session.ws_connect(url=self.url.format())
            async for message in connection:
                self.ws_process_message(message)
        except asyncio.CancelledError:
            """closing"""
            return
        except aiohttp.client_exceptions:
            await asyncio.sleep(timeout)
            return asyncio.create_task(self.connect(timeout=max(timeout * timeout, 2)))
        except Exception as e:
            self.error = e
        finally:
            await session.close()

    def ws_process_message(self, message: aiohttp.WSMessage) -> None:
        if message.type != aiohttp.WSMsgType.TEXT:
            return
        data = json.loads(message.data)
        try:
            self.process_data(data)
        except AssertionError:
            return

    def process_data(self, data: dict) -> None:
        status: dict = data.get("Status", {})
        print_info: dict = status.get("PrintInfo", {})
        fan_speeds: dict = status.get("CurrentFanSpeed", {})

        assert status or print_info, "No status and print info."

        print_status = print_info.get("Status")
        time = int(print_info.get("TotalTicks", 0))
        bed_temp = int(status.get("TempOfHotbed", 0))
        enclosure_temp = int(status.get("TempOfBox", 0))
        nozzle_temp = int(status.get("TempOfNozzle", 0))
        target_bed_temp = int(status.get("TempTargetHotbed", 0))
        target_nozzle_temp = int(status.get("TempTargetNozzle", 0))
        print_speed = int(print_info.get("PrintSpeedPct", 0))
        current_layer = int(print_info.get("CurrentLayer", 0))
        total_layers = int(print_info.get("TotalLayer", 0))

        self.data.print_status = STATUS.get(print_status, f"Unknown: {print_status}")
        self.data.progress = round(print_info.get("Progress", 0.0), 1)
        self.data.elapsed_time = time_format(int(print_info.get("CurrentTicks", "0")))
        self.data.remaining_time = time_format(max(0, time - self.data.elapsed_time))
        self.data.aux_fan_speed = fan_speeds.get("AuxiliaryFan", 0)
        self.data.box_fan_speed = fan_speeds.get("BoxFan", 0)
        self.data.model_fan_speed = fan_speeds.get("ModelFan", 0)
        self.data.z_offset = round(
            status.get("ZOffset", self.data.z_offset if self.data.z_offset else 0), 3
        )
        self.data.bed_temp = bed_temp if bed_temp else self.data.bed_temp
        self.data.enclosure_temp = (
            enclosure_temp if enclosure_temp else self.data.enclosure_temp
        )
        self.data.nozzle_temp = nozzle_temp if nozzle_temp else self.data.nozzle_temp
        self.data.target_bed_temp = (
            target_bed_temp if target_bed_temp else self.data.target_bed_temp
        )
        self.data.target_nozzle_temp = (
            target_nozzle_temp if target_nozzle_temp else self.data.target_nozzle_temp
        )
        self.data.print_speed = (
            f"{print_speed}%" if print_speed else self.data.print_speed
        )
        self.data.current_layer = (
            current_layer if current_layer else self.data.current_layer
        )
        self.data.total_layers = (
            total_layers if total_layers else self.data.total_layers
        )


def time_format(seconds: int) -> str:
    output_string: list = []
    if seconds > 86400:
        output_string.append(f"{seconds%86400}d")
        seconds = seconds // 86400
    if seconds > 3600:
        output_string.append(f"{seconds%3600}h")
        seconds = seconds // 3600
    if seconds > 60:
        output_string.append(f"{seconds%60}m")
        seconds = seconds // 60
    if seconds:
        output_string.append(f"{seconds}s")
    return " ".join(output_string)
