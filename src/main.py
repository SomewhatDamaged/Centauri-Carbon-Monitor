from typing import Union

import flet as ft


class Monitor:
    def __init__(self):
        self.select_ip = ft.TextField(
            keyboard_type=ft.KeyboardType.URL, on_submit=self.set_ip
        )
        self.show_ip = ft.Text(value="None", visible=False)

    ip_address: Union[str, None] = None

    async def set_ip(self, event: ft.ControlEvent) -> None:
        self.ip_address = event.control.value
        self.show_ip.value = self.ip_address
        self.show_ip.visible = True
        self.update()

    async def main(self, page: ft.Page):
        page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        page.title = "Centauri Carbon Monitor"
        page.window.width = 720
        page.window.height = 1080
        page.theme_mode = ft.ThemeMode.DARK

        page.add(self.select_ip)
        page.add(self.show_ip)
        self.page = page
        self.update()

    def update(self) -> None:
        self.page.update()


app = Monitor()
ft.app(target=app.main)
