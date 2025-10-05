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

COLORS = {
    0: ft.Colors.RED,
    1: ft.Colors.ORANGE,
    2: ft.Colors.YELLOW,
    3: ft.Colors.LIME,
    4: ft.Colors.GREEN,
}
STATUS = {
    "Printing": ft.Colors.RED,
    "Paused": ft.Colors.YELLOW,
    "Pausing": ft.Colors.YELLOW,
    "Resuming": ft.Colors.YELLOW,
    "Idle": ft.Colors.GREY,
    "Preparing": ft.Colors.ORANGE,
    "Complete": ft.Colors.GREEN,
}


class Monitor:
    def __init__(self):
        self.select_ip = ft.TextField(on_submit=self.set_ip)
        self.show_ip = ft.Text(value="None", visible=False)
        self.printer = CarbonData()
        self.printer._log = log

    def process_data(self) -> None:
        data = self.printer.data
        if data.print_status.startswith("Unknown"):
            self._data_layout.visible = False
        else:
            self._data_layout.visible = True
        self.status.value = f"Status: {data.print_status}"
        self.status.color = STATUS.get(data.print_status, ft.Colors.WHITE)
        if data.print_status in [
            "Paused",
            "Preparing",
            "Printing",
            "Pausing",
            "Resuming",
        ]:
            self.layer_progress_text.visible = True
            self.layer_progress.visible = True
            self.progress_text.visible = True
            self.progress.visible = True
            self.time_text.visible = True
            self.fans.visible = True
            self.layer_progress_text.value = (
                f"Layer: {data.current_layer} / {data.total_layers}"
            )
            self.time_text.value = f"Time: {data.remaining_time} / {data.total_time}"
        elif data.print_status == "Complete":
            self.layer_progress_text.visible = True
            self.time_text.visible = True
            self.layer_progress.visible = False
            self.progress_text.visible = False
            self.progress.visible = False
            self.fans.visible = True
            self.layer_progress_text.value = f"Completed {data.total_layers} layers!"
            self.time_text.value = f"Time: {data.elapsed_time}"
        elif data.print_status == "Idle":
            self.layer_progress_text.visible = False
            self.time_text.visible = False
            self.layer_progress.visible = False
            self.progress_text.visible = False
            self.progress.visible = False
            self.fans.visible = False
            self.time_text.visible = False
        else:
            self.layer_progress_text.visible = False
            self.layer_progress.visible = False
            self.progress_text.visible = False
            self.progress.visible = False
            self.fans.visible = False
        self.layer_progress.value = (
            float(data.current_layer / data.total_layers) if data.total_layers else 0.0
        )
        if data.total_layers:
            self.layer_progress.color = COLORS.get(
                int((data.current_layer / data.total_layers * 4.9) % 5),
                ft.Colors.GREEN,
            )
        self.temperatures.value = f"Temperature\nNozzle: {data.nozzle_temp}C / {data.target_nozzle_temp}C\nBed: {data.bed_temp}C / {data.target_bed_temp}C\nBox: {data.enclosure_temp}C"
        self.fans.value = f"Fan Speeds\nModel: {data.model_fan_speed}%\nAux: {data.aux_fan_speed}%\nBox: {data.box_fan_speed}%"
        self.z_offset.value = f"Z-Offset: {data.z_offset}"
        self.progress_text.value = f"Progress: {data.progress}%"
        self.progress.value = data.progress / 100.0
        self.progress.color = COLORS.get(
            int((data.progress / 20.1) % 5), ft.Colors.GREEN
        )
        self._data_layout.update()

    def data_layout(self) -> None:
        data = self.printer.data
        self.status = ft.Text(value=f"Status: {data.print_status}")
        self.layer_progress_text = ft.Text(
            value=f"Layer: {data.current_layer} / {data.total_layers}"
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
            value=f"Temperature\nNozzle: {data.nozzle_temp}C / {data.target_nozzle_temp}C\nBed: {data.bed_temp}C / {data.target_bed_temp}C\nBox: {data.enclosure_temp}C"
        )
        self.fans = ft.Text(
            value=f"Fan Speeds\nModel: {data.model_fan_speed}\nAux: {data.aux_fan_speed}\nBox: {data.box_fan_speed}",
        )
        self.z_offset = ft.Text(value=f"Z-Offset: {data.z_offset}")
        self.progress_text = ft.Text(value=f"Progress: {data.progress}%")
        self.progress = ft.ProgressBar(
            color=ft.Colors.GREEN,
            value=data.progress / 100.0,
        )
        self.time_text = ft.Text(
            value=f"Time: {data.remaining_time} / {data.total_time}"
        )
        self._data_layout = ft.Column(
            controls=[
                self.status,
                self.layer_progress_text,
                self.layer_progress,
                self.progress_text,
                self.progress,
                self.time_text,
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Container(content=self.temperatures),
                            ft.Container(content=self.fans),
                        ],
                        expand=True,
                        alignment=ft.alignment.center,
                    ),
                    expand=True,
                ),
            ],
            visible=False,
            horizontal_alignment=ft.CrossAxisAlignment.START,
        )

    async def update_data(self) -> None:
        while True:
            try:
                while self.printer.data.print_status == "Unknown":
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
        page.window.width = 350
        page.window.height = 400
        page.theme_mode = ft.ThemeMode.DARK
        page.horizontal_alignment = ft.CrossAxisAlignment.START
        page.window.always_on_top = True
        page.window.resizable = False
        self.data_layout()
        layout = ft.Column(
            alignment=ft.alignment.top_center,
            controls=[
                self.select_ip,
                ft.Divider(),
                self._data_layout,
            ],
            expand=True,
        )
        page.add(layout)
        page.update()
        self.page = page
        asyncio.create_task(self.update_data())


async def runner():
    app = Monitor()
    await ft.app_async(target=app.main)


asyncio.run(runner())
