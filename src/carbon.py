import asyncio
import json
import logging
import sys
import time
import uuid
from dataclasses import asdict, dataclass
from typing import Union

import aiohttp

STATUS = {
    1: "Preparing",
    16: "Preparing",
    21: "Preparing",
    13: "Printing",
    9: "Complete",
    0: "Idle",
    6: "Paused",
}


@dataclass
class Stats:
    nozzle_temp: float = 0.0
    bed_temp: float = 0.0
    enclosure_temp: float = 0.0
    target_nozzle_temp: float = 0.0
    target_bed_temp: float = 0.0
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
    elapsed_time_raw: int = 0
    remaining_time: str = "0"
    remaining_time_raw: int = 0
    total_time: str = "0"
    total_time_raw: int = 0


class CarbonData:
    target: str = None
    url = "ws://{target}:3030/websocket"
    data = Stats()
    error: str = None
    _video: str = "http://{target}:3031/video"
    _connected = asyncio.Lock()
    _log: logging.Logger = None
    _connection: aiohttp.ClientWebSocketResponse

    @property
    def to_dict(self) -> dict:
        return asdict(self.data)

    @property
    def video(self) -> Union[str, None]:
        return self._video.format(target=self.target) if self.connected else None

    @property
    def connected(self) -> bool:
        return self._connected.locked()

    def __init__(self, target: str = None) -> None:
        self.target = target
        asyncio.create_task(self.connect())

    async def connect(self, timeout: int = 0) -> None:
        session = aiohttp.ClientSession()
        tickler = None
        try:
            while not self.target:
                await asyncio.sleep(1)
            self.log(f"Connecting to: {self.url.format(target=self.target)}")
            async with session.ws_connect(
                url=self.url.format(target=self.target)
            ) as self._connection:
                tickler = asyncio.create_task(self.request_info())
                self.log("Connected!")
                await self._connected.acquire()
                self.log("Locked!")
                async for message in self._connection:
                    self.ws_process_message(message)
        except asyncio.CancelledError:
            self.log("Exiting!")
            """closing"""
            return
        except aiohttp.ClientError:
            exc_type, _, _ = sys.exc_info()
            self.log("HTTP error!")
            if self._log:
                self._log.exception(exc_type)
            self.target = None
            await asyncio.sleep(timeout)
            return asyncio.create_task(self.connect(timeout=max(timeout * timeout, 2)))
        except Exception:
            exc_type, _, _ = sys.exc_info()
            self.log("Error!")
            if self._log:
                self._log.exception(exc_type)
        else:
            return asyncio.create_task(self.connect(timeout=max(timeout * timeout, 2)))
        finally:
            self.log("Closing session")
            await session.close()
            self.log("Checking lock...")
            if self._connected.locked():
                self.log("Freeing lock!")
                self._connected.release()
            if tickler is not None and not tickler.done():
                tickler.cancel()

    async def request_info(self) -> None:
        try:
            while True:
                await asyncio.sleep(2)
                await self._connection.send_json(
                    {
                        "Id": "",
                        "Data": {
                            "Cmd": 0,
                            "Data": {},
                            "RequestID": uuid.uuid4().hex,
                            "MainboardID": "",
                            "TimeStamp": int(time.time() * 1000),
                            "From": 1,
                        },
                    }
                )
        except asyncio.CancelledError:
            return "Exiting"

    def ws_process_message(self, message: aiohttp.WSMessage) -> None:
        self.log("Processing a message...")
        if message.type != aiohttp.WSMsgType.TEXT:
            return
        data = json.loads(message.data)
        try:
            self.process_data(data)
            self.log(f"Processed message: {self.to_dict}")
        except AssertionError:
            return

    def process_data(self, data: dict) -> None:
        status: dict = data.get("Status", {})
        print_info: dict = status.get("PrintInfo", {})
        fan_speeds: dict = status.get("CurrentFanSpeed", {})

        assert status or print_info, "No status and print info."

        print_status = int(print_info.get("Status"))
        time = int(print_info.get("TotalTicks", 0))
        bed_temp = int(status.get("TempOfHotbed", 0))
        enclosure_temp = int(status.get("TempOfBox", 0))
        nozzle_temp = int(status.get("TempOfNozzle", 0))
        target_bed_temp = int(status.get("TempTargetHotbed", 0))
        target_nozzle_temp = int(status.get("TempTargetNozzle", 0))
        print_speed = int(print_info.get("PrintSpeedPct", 0))
        current_layer = int(print_info.get("CurrentLayer", 0))
        total_layers = int(print_info.get("TotalLayer", 0))
        elapsed_time = int(print_info.get("CurrentTicks", 0))

        self.data.print_status = STATUS.get(print_status, f"Unknown: {print_status}")
        self.data.progress = round(print_info.get("Progress", 0.0), 1)
        self.data.elapsed_time = time_format(elapsed_time)
        self.data.elapsed_time_raw = elapsed_time
        self.data.remaining_time = time_format(max(0, time - elapsed_time))
        self.data.remaining_time_raw = max(0, time - elapsed_time)
        self.data.total_time = time_format(time)
        self.data.total_time_raw = time
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

    def log(self, message: str):
        if self._log:
            self._log.debug(message)


def time_format(seconds: int) -> str:
    output_string: list = []
    if seconds > 86400:
        output_string.append(f"{seconds//86400}d")
        seconds = seconds % 86400
    if seconds > 3600:
        output_string.append(f"{seconds//3600}h")
        seconds = seconds % 3600
    if seconds > 60:
        output_string.append(f"{seconds//60}m")
        seconds = seconds % 60
    if seconds:
        output_string.append(f"{seconds}s")
    return " ".join(output_string)
