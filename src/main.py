import asyncio
import logging
import logging.handlers
from typing import Union

import flet as ft

from carbon import CarbonData

log = logging.getLogger("Carbon")
log.setLevel(logging.INFO)
fhandler = logging.handlers.RotatingFileHandler(  # type: ignore
    filename="carbon.log",
    encoding="utf-8",
    mode="a",
    maxBytes=10**7,
    backupCount=5,
)
fmt = logging.Formatter(
    "%(asctime)s %(levelname)s %(module)s %(funcName)s %(lineno)d: %(message)s",
    datefmt="[%d/%m/%Y %H:%M]",
)
fhandler.setFormatter(fmt)
log.addHandler(fhandler)


class Monitor:
    def __init__(self):
        self.select_ip = ft.TextField(on_submit=self.set_ip)
        self.show_ip = ft.Text(value="None", visible=False)
        self.printer = CarbonData()
        self.printer._log = log

    def process_data(self) -> None:
        data = self.printer.data
        self.status.value = f"Status: {data.print_status}"
        self.layer_progress_text.value = (
            f"Layer: {data.current_layer}/{data.total_layers}"
        )
        self.layer_progress.value = (
            float(data.current_layer / data.total_layers) if data.total_layers else 0.0
        )
        self.temperatures.value = f"Temperature\nNozzle: {data.nozzle_temp}C/{data.target_nozzle_temp}C\nBed: {data.bed_temp}C/{data.target_bed_temp}C\nBox: {data.enclosure_temp}C"
        self.fans.value = f"Fan Speeds\nModel: {data.model_fan_speed}%\nAux: {data.aux_fan_speed}%\nBox: {data.box_fan_speed}%"
        self.z_offset.value = f"Z-Offset: {data.z_offset}"
        self.progress_text.value = f"Progress: {data.progress}%"
        self.progress.value = data.progress / 100.0
        self.time_text.value = f"Time remaining: {data.remaining_time}"
        self.time.value = (
            float(data.elapsed_time_raw / data.total_time_raw)
            if data.total_time_raw
            else 0
        )
        self._data_layout.update()

    def data_layout(self) -> None:
        data = self.printer.data
        self.status = ft.Text(value=f"Status: {data.print_status}")
        self.layer_progress_text = ft.Text(
            value=f"Layer: {data.current_layer}/{data.total_layers}"
        )
        self.layer_progress = ft.ProgressBar(
            color=ft.Colors.GREEN,
            value=(
                float(data.current_layer / data.total_layers)
                if data.total_layers
                else 0.0
            ),
        )
        self.temperatures = ft.Text(
            value=f"Temperature\nNozzle: {data.nozzle_temp}C/{data.target_nozzle_temp}C\nBed: {data.bed_temp}C/{data.target_bed_temp}C\nBox: {data.enclosure_temp}C"
        )
        self.fans = ft.Text(
            value=f"Fan Speeds\nModel: {data.model_fan_speed}\nAux: {data.aux_fan_speed}\nBox: {data.box_fan_speed}"
        )
        self.z_offset = ft.Text(value=f"Z-Offset: {data.z_offset}")
        self.progress_text = ft.Text(value=f"Progress: {data.progress}%")
        self.progress = ft.ProgressBar(
            color=ft.Colors.GREEN,
            value=data.progress / 100.0,
        )
        self.time_text = ft.Text(value=f"Time remaining: {data.remaining_time}")
        self.time = ft.ProgressBar(
            color=ft.Colors.GREEN,
            value=(
                float(data.elapsed_time_raw / data.total_time_raw)
                if data.total_time_raw
                else 0.0
            ),
        )
        self._data_layout = ft.Column(
            controls=[
                self.status,
                self.layer_progress_text,
                self.layer_progress,
                self.progress_text,
                self.progress,
                self.time_text,
                self.time,
                self.temperatures,
                self.fans,
            ],
            visible=False,
        )

    async def update_data(self) -> None:
        while True:
            try:
                while not self.printer.connected:
                    if self._data_layout.visible:
                        self._data_layout.visible = False
                        self._data_layout.update()
                    await asyncio.sleep(0.5)
                if not self._data_layout.visible:
                    self._data_layout.visible = True
                    self._data_layout.update()
                self.process_data()
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                return

    target: Union[str, None] = None

    async def set_ip(self, event: ft.ControlEvent) -> None:
        self.select_ip.tooltip = event.control.value
        self.select_ip.value = event.control.value
        self.printer.target = event.control.value
        self.select_ip.update()

    async def main(self, page: ft.Page):
        page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        page.title = "Centauri Carbon Monitor"
        page.window.width = 400
        page.window.height = 500
        page.theme_mode = ft.ThemeMode.DARK
        self.data_layout()

        page.add(self.select_ip)
        page.add(ft.Divider())
        self.data_layout()
        page.add(self._data_layout)
        page.update()
        self.page = page
        asyncio.create_task(self.update_data())


async def runner():
    app = Monitor()
    await ft.app_async(target=app.main)


asyncio.run(runner())
