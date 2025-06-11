# modules/control_center/widgets/quick_settings/vpn.py
# WERSJA OSTATECZNA - Oparta w 100% na bindowaniu
import asyncio
from gi.repository import Gtk, GObject, GLib
from ignis.widgets import Widget
from ignis.utils import Utils
from ignis.variable import Variable
from ignis.gobject import IgnisGObject
from ...qs_button import QSButton
from ...menu import Menu
from ignis.services.network import NetworkService, VpnConnection
from .vpn_state import praca_vpn_is_active

network = NetworkService.get_default()

class VpnState(IgnisGObject):
    """
    Pomocnicza klasa agregująca stan z obu źródeł VPN (NM i PracaVPN)
    i wystawiająca właściwości, do których można się bindować.
    """
    __gtype_name__ = 'VpnState'

    def __init__(self):
        super().__init__()
        self._is_active = False
        self._display_label = "VPN"
        
        network.vpn.connect("notify::is-connected", self.update_state)
        praca_vpn_is_active.connect("notify::value", self.update_state)
        self.update_state()

    @GObject.Property
    def is_active(self) -> bool:
        return self._is_active

    @GObject.Property
    def display_label(self) -> str:
        return self._display_label

    def update_state(self, *args):
        is_nm_active = network.vpn.is_connected
        is_praca_active = praca_vpn_is_active.value
        
        new_active_state = is_nm_active or is_praca_active
        if self._is_active != new_active_state:
            self._is_active = new_active_state
            self.notify("is_active")

        new_label = "VPN"
        if new_active_state:
            new_label = network.vpn.active_vpn_id or "Praca VPN"
        
        if self._display_label != new_label:
            self._display_label = new_label
            self.notify("display_label")

class PracaVpnRow(Widget.Box):
    # Ta klasa pozostaje bez zmian
    __gtype_name__ = 'PracaVpnRow'
    def __init__(self):
        super().__init__(css_classes=["network-item"])
        self.label = Widget.Label(label="Praca VPN", halign="start")
        self.switch = Gtk.Switch(valign="center", hexpand=True, halign="end")
        self.append(self.label)
        self.append(self.switch)
        self.switch.connect("state-set", self._on_toggle)
        praca_vpn_is_active.connect("notify::value", self._on_state_change)
        GLib.idle_add(self.update_state)
        self.poll = Utils.Poll(3000, self.update_state)
    def _on_toggle(self, switch, active):
        command = "/usr/bin/sudo /usr/sbin/ipsec up PracaVPN" if active else "/usr/bin/sudo /usr/sbin/ipsec down PracaVPN"
        asyncio.ensure_future(Utils.exec_sh_async(command))
        GLib.timeout_add(1500, lambda: self.update_state() and False)
        return False
    def _on_state_change(self, *args):
        if self.switch.get_active() != praca_vpn_is_active.value:
            self.switch.set_active(praca_vpn_is_active.value)
    def update_state(self, *args):
        try:
            result = Utils.exec_sh("/usr/bin/sudo /usr/sbin/ipsec status PracaVPN")
            is_active_now = "ESTABLISHED" in result.stdout
            if praca_vpn_is_active.value != is_active_now:
                praca_vpn_is_active.value = is_active_now
        except Exception:
            if praca_vpn_is_active.value:
                praca_vpn_is_active.value = False
        return True

class VpnNetworkItem(Widget.Button):
    # Ta klasa pozostaje bez zmian
    def __init__(self, conn: VpnConnection):
        super().__init__(
            css_classes=["network-item", "unset"],
            on_click=lambda x: asyncio.create_task(conn.toggle_connection()),
            child=Widget.Box(child=[
                Widget.Label(label=conn.name, ellipsize="end", max_width_chars=20, halign="start"),
                Widget.Label(label=conn.bind("is_connected", lambda v: "Rozłącz" if v else "Połącz"),
                             css_classes=["connect-label", "unset"], halign="end", hexpand=True),
            ]),
        )

class VpnMenu(Menu):
    # Ta klasa pozostaje bez zmian
    def __init__(self):
        praca_vpn_row = PracaVpnRow()
        connections_box = Widget.Box(vertical=True, child=network.vpn.bind("connections", lambda v: [VpnNetworkItem(i) for i in v]))
        super().__init__(
            name="vpn",
            child=[
                Widget.Box(css_classes=["network-header-box"], child=[
                    Widget.Icon(icon_name="network-vpn-symbolic", pixel_size=28),
                    Widget.Label(label="Połączenia VPN", css_classes=["network-header-label"]),
                ]),
                praca_vpn_row,
                Widget.Separator(),
                connections_box,
                Widget.Separator(),
                Widget.Button(
                    css_classes=["network-item", "unset"],
                    on_click=lambda x: asyncio.create_task(Utils.exec_sh_async("nm-connection-editor")),
                    style="margin-bottom: 0;",
                    child=Widget.Box(child=[
                        Widget.Icon(image="preferences-system-symbolic"),
                        Widget.Label(label="Ustawienia sieci", halign="start"),
                    ]),
                ),
            ],
        )

class VpnButton(QSButton):
    def __init__(self):
        # 1. Tworzymy naszą nową klasę zarządzającą stanem
        self.state = VpnState()
        menu = VpnMenu()
        
        # 2. Bindujemy WŁAŚCIWOŚCI przycisku do właściwości obiektu stanu,
        #    naśladując w 100% wzorzec z `ethernet.py`
        super().__init__(
            label=self.state.bind("display_label"),
            icon_name="network-vpn-symbolic",
            on_activate=lambda x: menu.toggle(),
            on_deactivate=lambda x: menu.toggle(),
            menu=menu,
            active=self.state.bind("is_active")
        )

def vpn_control() -> list[QSButton]:
    return [VpnButton()]