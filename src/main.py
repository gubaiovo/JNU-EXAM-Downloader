import flet as ft
import requests
import json
import os
import threading
import re
import webbrowser
import platform
import subprocess
from pathlib import Path


SOURCE_CONFIG = {
    "Github": {
        "json_url": "https://raw.githubusercontent.com/gubaiovo/JNU-EXAM/main/directory_structure.json",
        "file_key": "github_raw_url"
    },
    "Gitee": {
        "json_url": "https://gitee.com/gubaiovo/jnu-exam/raw/main/directory_structure.json",
        "file_key": "gitee_raw_url"
    },
    "CloudFlare R2": {
        "json_url": "https://jnuexam.xyz/directory_structure.json",
        "file_key": "cf_url"
    }
}

DEFAULT_SOURCE = "CloudFlare R2"


def main(page: ft.Page):
    page.title = "期末无挂 - JNU-EXAM 下载器"
    page.theme_mode = ft.ThemeMode.SYSTEM
    page.window.width = 1100
    page.window.height = 750
    page.padding = 0 
    page.spacing = 0

    state = {
        "current_source": DEFAULT_SOURCE,
        "json_data": None,
        "all_flat_files": [], 
        "selected_file_info": None,
        "last_downloaded_path": None,
        "is_downloading": False
    }


    def show_snack(msg, is_error=False):
        page.open(ft.SnackBar(
            content=ft.Text(msg), 
            bgcolor=ft.Colors.ERROR if is_error else ft.Colors.PRIMARY
        ))

    def format_size(size):
        if size >= 1024 * 1024: return f"{size / 1024 / 1024:.2f} MB"
        if size >= 1024: return f"{size / 1024:.2f} KB"
        return f"{size} B"

    def sanitize_filename(filename):
        name = re.sub(r'[\\/*?:"<>|]', '_', filename)
        name = "".join(x for x in name if x.isprintable())
        name = name.strip().rstrip(". ")
        return name[:200]

    def get_current_file_url(info):
        if not info: return None
        config = SOURCE_CONFIG.get(state["current_source"], SOURCE_CONFIG[DEFAULT_SOURCE])
        return info.get(config["file_key"])

    def get_default_downloads_dir():
        if platform.system() == "Windows":
            try:
                import winreg
                sub_key = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders"
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub_key) as key:
                    try:
                        path, _ = winreg.QueryValueEx(key, "{374DE290-123F-4565-9164-39C4925E467B}")
                        return Path(path)
                    except FileNotFoundError:
                        print("注册表中未找到下载路径 GUID，尝试默认路径")
            except Exception as e:
                print(f"获取 Windows 下载路径失败: {e}")

        return Path.home() / "Downloads"

    def open_file_in_explorer(path):
        if not path or not os.path.exists(path):
            show_snack("文件不存在", True)
            return

        system_name = platform.system()
        try:
            if system_name == "Windows":
                subprocess.Popen(f'explorer /select,"{path}"')
            elif system_name == "Darwin": 
                subprocess.Popen(["open", "-R", path])
            else: 
                folder = os.path.dirname(path)
                subprocess.Popen(["xdg-open", folder])
        except Exception as e:
            print(f"打开文件夹失败: {e}")
            show_snack(f"无法打开文件夹: {e}", True)

    
    def start_download_task(url, save_path_str):
        if state["is_downloading"]: return
        state["is_downloading"] = True
        
        save_path = Path(save_path_str)
        
        download_btn.disabled = True
        quick_dl_btn.disabled = True 
        browser_dl_btn.disabled = True
        open_folder_btn.visible = False 
        
        download_progress.visible = True
        download_progress.value = 0
        status_text.value = f"正在下载: {save_path.name}..."
        page.update()

        def _task():
            try:
                print(f"下载目标: {save_path}")
                save_path.parent.mkdir(parents=True, exist_ok=True)

                with requests.get(url, stream=True, timeout=60) as r:
                    r.raise_for_status()
                    total = int(r.headers.get('content-length', 0))
                    downloaded = 0
                    with open(save_path, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                downloaded += len(chunk)
                                if total > 0:
                                    download_progress.value = downloaded / total
                                    page.update()
                
                state["last_downloaded_path"] = str(save_path)
                status_text.value = "下载完成"
                show_snack(f"保存成功: {save_path.name}")
                open_folder_btn.visible = True
                
            except Exception as err:
                print(f"下载失败: {err}")
                status_text.value = "下载错误"
                show_snack(str(err), True)
            finally:
                state["is_downloading"] = False
                has_selection = state["selected_file_info"] is not None
                download_btn.disabled = not has_selection
                quick_dl_btn.disabled = not has_selection
                browser_dl_btn.disabled = not has_selection
                page.update()

        threading.Thread(target=_task, daemon=True).start()

    
    def on_save_file_result(e: ft.FilePickerResultEvent):
        if not e.path: return
        info = state["selected_file_info"]
        url = get_current_file_url(info)
        if url:
            start_download_task(url, e.path)

    file_picker = ft.FilePicker(on_result=on_save_file_result)
    page.overlay.append(file_picker)


    source_dropdown = ft.Dropdown(
        width=180,
        label="下载源",
        prefix_icon=ft.Icons.CLOUD_DOWNLOAD_OUTLINED,
        options=[ft.dropdown.Option(k) for k in SOURCE_CONFIG.keys()],
        value=DEFAULT_SOURCE,
        text_size=14,
        content_padding=10,
        border_color=ft.Colors.OUTLINE_VARIANT,
    )

    refresh_btn = ft.IconButton(icon=ft.Icons.REFRESH, tooltip="刷新目录")
    theme_btn = ft.IconButton(icon=ft.Icons.BRIGHTNESS_4, tooltip="切换主题")

    def on_search_change(e):
        query = e.control.value.strip().lower()
        if not query:
            process_tree(state["json_data"])
        else:
            perform_search(query)

    search_field = ft.TextField(
        hint_text="搜索文件...",
        prefix_icon=ft.Icons.SEARCH,
        height=40,
        content_padding=10,
        text_size=14,
        border_radius=20,
        on_change=on_search_change
    )

    tree_view = ft.ListView(expand=True, spacing=0, padding=10, auto_scroll=False)
    
    sidebar_container = ft.Container(
        content=ft.Column([
            ft.Container(content=search_field, padding=10),
            tree_view
        ], spacing=0),
        width=380,
        border=ft.border.only(right=ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT)),
        padding=0
    )

    file_icon = ft.Icon(name=ft.Icons.DESCRIPTION_OUTLINED, size=80, color=ft.Colors.PRIMARY)
    
    file_name_text = ft.Text("请选择文件", size=20, weight=ft.FontWeight.W_600, text_align=ft.TextAlign.CENTER, selectable=True)
    file_path_text = ft.Text(" ", size=13, color=ft.Colors.OUTLINE, text_align=ft.TextAlign.CENTER, selectable=True)
    
    file_size_val = ft.Text("-", size=13, selectable=True)
    file_url_val = ft.Text("-", size=13, selectable=True, color=ft.Colors.BLUE, width=350)

    def save_as_click(e):
        if not state["selected_file_info"]: return
        original_name = state["selected_file_info"]['name']
        safe_name = sanitize_filename(original_name)
        file_picker.save_file(dialog_title="另存为", file_name=safe_name)

    def quick_download_click(e):
        if not state["selected_file_info"]: return
        info = state["selected_file_info"]
        url = get_current_file_url(info)
        if not url: return

        original_name = info['name']
        safe_name = sanitize_filename(original_name)
        
        dl_dir = get_default_downloads_dir()
        save_path = dl_dir / safe_name
        
        start_download_task(url, str(save_path))

    def browser_download_click(e):
        info = state["selected_file_info"]
        url = get_current_file_url(info)
        if url:
            webbrowser.open(url)
            show_snack("已调用系统浏览器打开")

    def open_folder_click(e):
        if state["last_downloaded_path"]:
            open_file_in_explorer(state["last_downloaded_path"])

    quick_dl_btn = ft.FilledButton("快速下载 (默认目录)", icon=ft.Icons.DOWNLOAD_ROUNDED, height=45, disabled=True, on_click=quick_download_click, expand=True)
    download_btn = ft.OutlinedButton("另存为...", icon=ft.Icons.SAVE_AS, height=45, disabled=True, on_click=save_as_click, expand=True)
    browser_dl_btn = ft.OutlinedButton("浏览器", icon=ft.Icons.OPEN_IN_BROWSER, height=45, disabled=True, on_click=browser_download_click, width=120)
    open_folder_btn = ft.TextButton("打开文件所在位置", icon=ft.Icons.FOLDER_OPEN, visible=False, on_click=open_folder_click)

    download_progress = ft.ProgressBar(value=0, visible=False, height=4)
    status_text = ft.Text("就绪", size=12, color=ft.Colors.OUTLINE)

    def info_row(label, content):
        return ft.Row([ft.Text(label, width=40, color=ft.Colors.OUTLINE, size=13), content], alignment=ft.MainAxisAlignment.START)

    details_container = ft.Container(
        expand=True,
        padding=40,
        content=ft.Column(
            controls=[
                ft.Container(height=20),
                ft.Row([file_icon], alignment=ft.MainAxisAlignment.CENTER),
                ft.Container(height=20),
                file_name_text,
                ft.Container(height=5),
                file_path_text,
                ft.Container(height=40),
                ft.Container(
                    padding=20,
                    border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
                    border_radius=8,
                    content=ft.Column([
                        info_row("大小", file_size_val),
                        ft.Divider(height=1, color=ft.Colors.OUTLINE_VARIANT),
                        info_row("链接", file_url_val),
                    ], spacing=15)
                ),
                ft.Container(expand=True), 
                ft.Column([
                    ft.Row([quick_dl_btn], alignment=ft.MainAxisAlignment.CENTER),
                    ft.Container(height=10),
                    ft.Row([download_btn, browser_dl_btn], alignment=ft.MainAxisAlignment.CENTER, spacing=10),
                    ft.Container(height=20),
                    download_progress,
                    ft.Container(height=5),
                    ft.Row([status_text], alignment=ft.MainAxisAlignment.CENTER),
                    ft.Row([open_folder_btn], alignment=ft.MainAxisAlignment.CENTER)
                ])
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER
        )
    )


    def update_details(info):
        state["selected_file_info"] = info
        state["last_downloaded_path"] = None
        open_folder_btn.visible = False
        
        file_name_text.value = info['name']
        file_path_text.value = info['path']
        file_size_val.value = format_size(info['size'])
        
        url = get_current_file_url(info)
        file_url_val.value = url or "N/A"
        
        ext = os.path.splitext(info['name'])[1].lower()
        if ext == '.pdf':
            file_icon.name = ft.Icons.PICTURE_AS_PDF
            file_icon.color = ft.Colors.RED_400
        elif ext in ['.zip', '.rar', '.7z']:
            file_icon.name = ft.Icons.FOLDER_ZIP
            file_icon.color = ft.Colors.AMBER_600
        else:
            file_icon.name = ft.Icons.INSERT_DRIVE_FILE
            file_icon.color = ft.Colors.PRIMARY

        is_downloading = state["is_downloading"]
        download_btn.disabled = is_downloading
        quick_dl_btn.disabled = is_downloading
        browser_dl_btn.disabled = is_downloading
        
        page.update()

    def flatten_files_recursive(node, result_list):
        if 'files' in node:
            result_list.extend(node['files'])
        if 'dirs' in node:
            for d in node['dirs']:
                flatten_files_recursive(d, result_list)

    def perform_search(query):
        tree_view.controls.clear()
        results = [f for f in state["all_flat_files"] if query in f['name'].lower()]
        
        if not results:
            tree_view.controls.append(
                ft.Container(
                    content=ft.Text("未找到匹配文件", color=ft.Colors.OUTLINE),
                    padding=20,
                    alignment=ft.alignment.center
                )
            )
        else:
            for f in results:
                tree_view.controls.append(
                    ft.ListTile(
                        title=ft.Text(f['name'], weight=ft.FontWeight.BOLD),
                        subtitle=ft.Text(f['path'], size=12, color=ft.Colors.OUTLINE),
                        leading=ft.Icon(ft.Icons.INSERT_DRIVE_FILE_OUTLINED, size=18),
                        on_click=lambda e, i=f: update_details(i)
                    )
                )
        page.update()

    def process_tree(data):
        tree_view.controls.clear()
        path_map = {"": tree_view.controls}
        
        all_dirs = sorted(data.get('dirs', []), key=lambda d: d['path'].count('/'))
        for d in all_dirs:
            path = d['path']
            parent = os.path.dirname(path).replace("\\", "/")
            if parent == ".": parent = ""
            
            tile = ft.ExpansionTile(
                title=ft.Text(d['name'], size=14, overflow=ft.TextOverflow.ELLIPSIS, tooltip=d['name']),
                leading=ft.Icon(ft.Icons.FOLDER_ROUNDED, color=ft.Colors.AMBER_700, size=20),
                controls_padding=ft.padding.only(left=20),
                shape=ft.RoundedRectangleBorder(radius=0),
                min_tile_height=40,
                text_color=ft.Colors.ON_SURFACE,
            )
            path_map[path] = tile.controls
            path_map.get(parent, tree_view.controls).append(tile)
            
            if 'files' in d:
                for f in sorted(d['files'], key=lambda x: x['name']):
                    tile.controls.append(create_file_tile(f))

        if 'files' in data:
            for f in sorted(data['files'], key=lambda x: x['name']):
                tree_view.controls.append(create_file_tile(f))
        
        page.update()

    def create_file_tile(f_info):
        return ft.ListTile(
            title=ft.Text(f_info['name'], size=13, overflow=ft.TextOverflow.ELLIPSIS, tooltip=f_info['name']),
            leading=ft.Icon(ft.Icons.INSERT_DRIVE_FILE_OUTLINED, size=18),
            on_click=lambda e: update_details(f_info),
            height=40,
        )

    def load_data(e=None):
        src = state['current_source']
        status_text.value = f"正在从 {src} 更新..."
        download_progress.visible = True
        download_progress.value = None
        search_field.value = ""
        page.update()

        def _task():
            try:
                config = SOURCE_CONFIG.get(src, SOURCE_CONFIG[DEFAULT_SOURCE])
                url = config["json_url"]
                res = requests.get(url, timeout=15)
                res.raise_for_status()
                data = json.loads(res.text)
                state["json_data"] = data
                
                flat_files = []
                flatten_files_recursive(data, flat_files)
                state["all_flat_files"] = flat_files
                
                process_tree(data)
                status_text.value = f"已更新 ({len(flat_files)} 文件)"
                show_snack(f"已从 {src} 刷新目录")
            except Exception as err:
                status_text.value = "更新失败"
                show_snack(str(err), True)
            finally:
                download_progress.visible = False
                page.update()
        threading.Thread(target=_task, daemon=True).start()

    refresh_btn.on_click = load_data
    
    def on_source_change(e):
        state["current_source"] = source_dropdown.value
        show_snack(f"源已切换: {source_dropdown.value}")
        load_data()
    source_dropdown.on_change = on_source_change

    def on_theme_change(e):
        page.theme_mode = ft.ThemeMode.LIGHT if page.theme_mode == ft.ThemeMode.DARK else ft.ThemeMode.DARK
        theme_btn.icon = ft.Icons.BRIGHTNESS_4 if page.theme_mode == ft.ThemeMode.LIGHT else ft.Icons.BRIGHTNESS_7
        page.update()
    theme_btn.on_click = on_theme_change

    header = ft.Container(
        padding=ft.padding.symmetric(horizontal=20, vertical=10),
        border=ft.border.only(bottom=ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT)),
        content=ft.Row([
            ft.Icon(ft.Icons.SCHOOL_ROUNDED, color=ft.Colors.PRIMARY, size=28),
            ft.Text("期末无挂", size=20, weight=ft.FontWeight.BOLD),
            ft.Container(width=20),
            source_dropdown,
            ft.Container(expand=True),
            refresh_btn,
            theme_btn,
        ])
    )

    page.add(ft.Column([
        header,
        ft.Row([sidebar_container, details_container], expand=True, spacing=0)
    ], expand=True, spacing=0))

    page.update()
    load_data()

if __name__ == "__main__":
    ft.app(target=main)