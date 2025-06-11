# modules/side_panel_left/widgets/system_info_view.py
import shutil 
import os 
import asyncio
import re
from gi.repository import GLib
from ignis.widgets import Widget
from ignis.services.fetch import FetchService
from ignis.utils import Utils
import psutil

fetch_service = FetchService.get_default()

amd_gpu_temp_path_cache: str | None = None

class SystemInfoView(Widget.Scroll):
    __gtype_name__ = "SystemInfoView"

    def __init__(self):
        # ... Inicjalizacja bez zmian ...
        self.content_box = Widget.Box(
            vertical=True, spacing=18, css_classes=["system-info-view-content"],
            margin_top=15, margin_bottom=15, margin_start=10, margin_end=10
        )
        super().__init__(child=self.content_box, vexpand=True, hexpand=True, css_classes=["system-info-view-scroll"])
        
        # ... Etykiety statyczne bez zmian ...
        self.os_label_value = Widget.Label(halign="start", selectable=True)
        self.kernel_label_value = Widget.Label(halign="start", selectable=True)
        self.cpu_label_value = Widget.Label(halign="start", ellipsize="end", selectable=True)
        self.gpu_label_value = Widget.Label(halign="start", ellipsize="end", selectable=True)
        self.desktop_label_value = Widget.Label(halign="start", selectable=True)
        self.gtk_theme_label_value = Widget.Label(halign="start", selectable=True)
        self.icon_theme_label_value = Widget.Label(halign="start", selectable=True)
        
        # ... Etykiety dynamiczne bez zmian ...
        self.cpu_temp_label = Widget.Label(label="CPU Temp: N/A", halign="start")
        self.gpu_temp_label = Widget.Label(label="GPU Temp: Ładowanie...", halign="start")
        self.ram_usage_label = Widget.Label(label="RAM: Ładowanie...", halign="start")
        self.cpu_usage_label = Widget.Label(label="CPU Usage: Ładowanie...", halign="start")
        self.gpu_usage_label = Widget.Label(label="GPU Usage: N/A (TODO)", halign="start")
        
        # Etykiety dla sieci lokalnej i VPN
        self.ip_address_label = Widget.Label(label="Ładowanie...", halign="start", selectable=True)
        self.dns_servers_label = Widget.Label(label="Ładowanie...", halign="start", selectable=True, wrap=True, max_width_chars=40, ellipsize="end")
        self.vpn_ip_label_value = Widget.Label(label="Ładowanie...", halign="start", selectable=True)
        self.vpn_section_box = self._create_section_box("Połączenie VPN")
        
        self.disk_info_box = Widget.Box(vertical=True, spacing=5)

        self._build_static_ui_layout()
        
        GLib.idle_add(self._find_amd_gpu_temp_path_async_wrapper)
        GLib.idle_add(self.update_all_info) 
        self.refresh_poll = Utils.Poll(2500, self.update_dynamic_info)
        psutil.cpu_percent(interval=None)

    def _create_info_row(self, grid: Widget.Grid, row_index: int, label_text: str, value_widget: Widget.Label):
        # ... Bez zmian ...
        label = Widget.Label(label=label_text, halign="end", css_classes=["info-label"])
        grid.attach(label, 0, row_index, 1, 1)
        grid.attach(value_widget, 1, row_index, 1, 1)

    def _build_static_ui_layout(self):
        # ... Budowanie UI z sekcją VPN (bez zmian) ...
        hw_info_section = self._create_section_box("Informacje o systemie i sprzęcie")
        hw_info_grid = Widget.Grid(column_spacing=10, row_spacing=5, css_classes=["info-grid"])
        self._create_info_row(hw_info_grid, 0, "System:", self.os_label_value)
        self._create_info_row(hw_info_grid, 1, "Kernel:", self.kernel_label_value)
        self._create_info_row(hw_info_grid, 2, "Pulpit:", self.desktop_label_value)
        self._create_info_row(hw_info_grid, 3, "CPU:", self.cpu_label_value)
        self._create_info_row(hw_info_grid, 4, "GPU:", self.gpu_label_value)
        self._create_info_row(hw_info_grid, 5, "Motyw GTK:", self.gtk_theme_label_value)
        self._create_info_row(hw_info_grid, 6, "Motyw Ikon:", self.icon_theme_label_value)
        hw_info_section.append(hw_info_grid)
        self.content_box.append(hw_info_section)

        vpn_grid = Widget.Grid(column_spacing=10, row_spacing=5, css_classes=["info-grid"])
        self._create_info_row(vpn_grid, 0, "Adres IP (VPN):", self.vpn_ip_label_value)
        self.vpn_section_box.append(vpn_grid)
        self.vpn_section_box.props.visible = False
        self.content_box.append(self.vpn_section_box)

        network_section = self._create_section_box("Informacje o sieci lokalnej")
        network_grid = Widget.Grid(column_spacing=10, row_spacing=5, css_classes=["info-grid"])
        self._create_info_row(network_grid, 0, "Adres IP:", self.ip_address_label)
        self._create_info_row(network_grid, 1, "Serwer DNS:", self.dns_servers_label)
        network_section.append(network_grid)
        self.content_box.append(network_section)
        
        temp_section = self._create_section_box("Temperatury")
        temp_grid = Widget.Grid(column_spacing=10, row_spacing=5, css_classes=["info-grid"])
        self._create_info_row(temp_grid, 0, "CPU:", self.cpu_temp_label)
        self._create_info_row(temp_grid, 1, "GPU:", self.gpu_temp_label)
        temp_section.append(temp_grid)
        self.content_box.append(temp_section)

        usage_section = self._create_section_box("Użycie zasobów")
        usage_grid = Widget.Grid(column_spacing=10, row_spacing=5, css_classes=["info-grid"])
        self._create_info_row(usage_grid, 0, "RAM:", self.ram_usage_label)
        self._create_info_row(usage_grid, 1, "CPU:", self.cpu_usage_label)
        self._create_info_row(usage_grid, 2, "GPU:", self.gpu_usage_label)
        usage_section.append(usage_grid)
        self.content_box.append(usage_section)

        disk_section = self._create_section_box("Miejsce na dysku")
        disk_section.append(self.disk_info_box) 
        self.content_box.append(disk_section)

    def update_all_info(self):
        # ... Statyczne info i GPU bez zmian ...
        self.os_label_value.label = fetch_service.os_name or "N/A"
        self.kernel_label_value.label = fetch_service.kernel or "N/A"
        self.desktop_label_value.label = fetch_service.current_desktop or "N/A"
        self.cpu_label_value.label = fetch_service.cpu or "N/A"
        self.gtk_theme_label_value.label = fetch_service.gtk_theme or "N/A"
        self.icon_theme_label_value.label = fetch_service.icon_theme or "N/A"
        
       # <-- NOWOŚĆ: Pobranie i sparsowanie nazwy GPU -->
        try:
            result = Utils.exec_sh("lspci | grep VGA")
            if result.returncode == 0 and result.stdout:
                # Parsowanie, aby uzyskać czystą nazwę
                name_part = result.stdout.strip().split(': ', 2)[-1]
                # Dalsze czyszczenie, aby usunąć np. [GeForce RTX 3060] i zostawić samą nazwę
                if ']' in name_part:
                    name_part = name_part.split(']', 1)[0].split('[',1)[-1]
                self.gpu_label_value.label = name_part.strip()
            else:
                self.gpu_label_value.label = "N/A"
        except Exception:
            self.gpu_label_value.label = "Błąd odczytu"

        self.update_dynamic_info()
        return False

    def _update_network_info(self):
        # <-- ZMIANA: Implementacja oparta o tablicę routingu -->
        local_ip_str = "Brak połączenia"
        vpn_ip_str = ""
        dns_str = "Brak połączenia"

        try:
            # --- Wykrywanie aktywnego połączenia (VPN lub lokalne) ---
            route_result = Utils.exec_sh("ip route get 8.8.8.8")
            if route_result.returncode == 0 and route_result.stdout:
                route_line = route_result.stdout.strip()
                # Używamy wyrażeń regularnych do bezpiecznego wyciągnięcia danych
                dev_match = re.search(r'dev\s+([^\s]+)', route_line)
                src_match = re.search(r'src\s+([^\s]+)', route_line)
                
                if dev_match and src_match:
                    interface = dev_match.group(1)
                    active_ip = src_match.group(1)
                    
                    # Sprawdzamy, czy interfejs jest typowy dla VPN
                    if any(vpn_if in interface for vpn_if in ["tun", "ppp", "wg", "ipsec"]):
                        vpn_ip_str = active_ip
                        # Jeśli mamy VPN, poszukajmy też "prawdziwego" lokalnego IP
                        local_ip_res = Utils.exec_sh("ip -4 -o addr show scope global | grep -v -E 'tun|ppp|wg|ipsec' | awk '{print $4}' | head -n 1")
                        if local_ip_res.returncode == 0 and local_ip_res.stdout:
                            local_ip_str = local_ip_res.stdout.strip()
                        else:
                            local_ip_str = "N/A"
                    else:
                        local_ip_str = active_ip
            
            # --- Serwery DNS ---
            dns_result = Utils.exec_sh("resolvectl status | grep 'Current DNS Server' | awk '{print $4}' | head -n 1")
            if dns_result.returncode == 0 and dns_result.stdout:
                dns_str = dns_result.stdout.strip().split('\n')[0]
            elif local_ip_str != "Brak połączenia":
                dns_str = "N/A"

        except Exception:
            local_ip_str = "Błąd odczytu"
            dns_str = "Błąd odczytu"
            vpn_ip_str = ""

        # Aktualizacja etykiet
        self.ip_address_label.label = local_ip_str
        self.dns_servers_label.label = dns_str
            
        if vpn_ip_str:
            self.vpn_ip_label_value.label = vpn_ip_str
            self.vpn_section_box.props.visible = True
        else:
            self.vpn_section_box.props.visible = False

    def update_dynamic_info(self, poll_instance=None):
        # ... Reszta bez zmian ...
        cpu_temp = fetch_service.cpu_temp
        self.cpu_temp_label.label = f"{cpu_temp}°C" if cpu_temp is not None else "N/A"
        
        mem_total_val = fetch_service.mem_total 
        mem_used_val = fetch_service.mem_used   
        if mem_total_val is not None and mem_total_val > 0 and mem_used_val is not None:
            ram_total_gb = mem_total_val / (1024 * 1024) 
            ram_used_gb = mem_used_val / (1024 * 1024)
            ram_percent = (mem_used_val / mem_total_val * 100)
            self.ram_usage_label.label = f"{ram_used_gb:.1f} GB / {ram_total_gb:.1f} GB ({ram_percent:.0f}%)"
        else:
            self.ram_usage_label.label = "RAM: N/A"

        try:
            cpu_usage = psutil.cpu_percent(interval=None) 
            self.cpu_usage_label.label = f"{cpu_usage:.1f}%"
        except Exception as e:
            self.cpu_usage_label.label = "CPU Usage: Błąd"

        asyncio.ensure_future(self._update_gpu_info_async())
        self._update_network_info()
        self._update_disk_usage()
        return True

    #
    # --- PONIŻEJ TEJ LINII KOD POZOSTAJE BEZ ZMIAN ---
    #
    
    async def _update_gpu_info_async(self):
        global amd_gpu_temp_path_cache
        gpu_temp_val = None
        gpu_usage_val_str = "N/A"
        try:
            command_str = 'nvidia-smi --query-gpu=temperature.gpu,utilization.gpu --format=csv,noheader,nounits'
            process_result: Utils.AsyncCompletedProcess = await Utils.exec_sh_async(command_str)
            if process_result and process_result.returncode == 0 and process_result.stdout:
                output_line = process_result.stdout.strip()
                parts = output_line.split(',')
                if len(parts) == 2:
                    temp_str = parts[0].strip()
                    usage_str = parts[1].strip()
                    if temp_str.isdigit():
                        gpu_temp_val = int(temp_str)
                    if usage_str.isdigit():
                        gpu_usage_val_str = f"{usage_str}%"
        except (FileNotFoundError, Exception):
            pass

        if gpu_temp_val is None and amd_gpu_temp_path_cache:
            try:
                if os.path.exists(amd_gpu_temp_path_cache):
                    with open(amd_gpu_temp_path_cache, 'r') as f:
                        temp_millic = int(f.read().strip())
                        gpu_temp_val = round(temp_millic / 1000)
            except Exception:
                pass
        
        def update_gpu_labels_in_gtk_thread():
            self.gpu_temp_label.label = f"{gpu_temp_val}°C" if gpu_temp_val is not None else "N/A"
            self.gpu_usage_label.label = gpu_usage_val_str
            return False
        GLib.idle_add(update_gpu_labels_in_gtk_thread)

    def _find_amd_gpu_temp_path_async_wrapper(self):
        asyncio.ensure_future(self._find_amd_gpu_temp_path())
        return False

    async def _find_amd_gpu_temp_path(self):
        global amd_gpu_temp_path_cache
        if amd_gpu_temp_path_cache:
            return
        common_paths = ['/sys/class/drm/card0/device/hwmon/hwmon0/temp1_input', '/sys/class/drm/card1/device/hwmon/hwmon1/temp1_input']
        for path in common_paths:
            if os.path.exists(path) and os.path.isfile(path):
                amd_gpu_temp_path_cache = path
                asyncio.ensure_future(self._update_gpu_info_async()) 
                return

    def _update_disk_usage(self):
        children_to_remove = [child for child in self.disk_info_box.child]
        for child_widget in children_to_remove:
            self.disk_info_box.remove(child_widget)

        disks_to_show = {"Dysk 1 (Kingston)": "/", "Dysk 2 (Samsung)": "/run/media/kamil-pc/Dane"}
        no_disk_data_added = True
        for display_name, path in disks_to_show.items():
            try:
                if os.path.exists(path) and os.path.ismount(path):
                    usage = shutil.disk_usage(path)
                    free_gb = usage.free / (1024**3)
                    total_gb = usage.total / (1024**3)
                    info_str = f"{free_gb:.1f} GB wolne z {total_gb:.1f} GB"
                    disk_entry_box = Widget.Box(spacing=5)
                    disk_entry_box.append(Widget.Label(label=display_name + ":", halign="start", css_classes=["info-label", "disk-label"]))
                    disk_entry_box.append(Widget.Label(label=info_str, halign="start", selectable=True, hexpand=True, ellipsize="end", css_classes=["disk-value"]))
                    self.disk_info_box.append(disk_entry_box)
                    no_disk_data_added = False
                else:
                    disk_entry_box = Widget.Box(spacing=5)
                    disk_entry_box.append(Widget.Label(label=display_name + ":", halign="start", css_classes=["info-label", "disk-label"]))
                    disk_entry_box.append(Widget.Label(label="N/A (ścieżka nieprawidłowa lub niezamontowana)", halign="start", css_classes=["error-text"]))
                    self.disk_info_box.append(disk_entry_box)
                    no_disk_data_added = False 
            except Exception as e:
                disk_entry_box = Widget.Box(spacing=5)
                disk_entry_box.append(Widget.Label(label=display_name + ":", halign="start", css_classes=["info-label", "disk-label"]))
                disk_entry_box.append(Widget.Label(label="Błąd odczytu", halign="start", css_classes=["error-text"]))
                self.disk_info_box.append(disk_entry_box)
        
        if no_disk_data_added and not list(self.disk_info_box.child):
             self.disk_info_box.append(Widget.Label(label="Nie zdefiniowano dysków do monitorowania.", halign="start"))

    def _create_section_box(self, title: str) -> Widget.Box:
        title_label = Widget.Label(label=title, halign="start", css_classes=["h2", "section-title"])
        section_box = Widget.Box(vertical=True, spacing=5, css_classes=["info-section"])
        section_box.append(title_label)
        section_box.append(Widget.Separator(margin_top=3, margin_bottom=6))
        return section_box