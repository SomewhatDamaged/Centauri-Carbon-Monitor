import flet as ft


async def main(page: ft.Page):
    ip_address = None

    async def set_ip(event: ft.ControlEvent) -> None:
        global ip_address
        ip_address = event.control.value

    select_ip = ft.TextField(keyboard_type=ft.KeyboardType.URL, on_submit=set_ip)

    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.title = "Centauri Carbon Monitor"
    page.window.width = 720
    page.window.height = 1080
    page.theme_mode = ft.ThemeMode.DARK

    page.add(select_ip)
    page.update()


ft.app(main)
