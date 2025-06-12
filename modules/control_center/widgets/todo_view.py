# modules/control_center/widgets/todo_view.py
import json
import os
import asyncio
from ignis.widgets import Widget
from ignis.utils import Utils
from gi.repository import GLib, Gtk

TODO_FILE_PATH = os.path.expanduser("~/.config/ignis/todo.json")
TASK_COMPLETE_SOUND_PATH = os.path.expanduser("~/.config/ignis/sounds/task_complete.wav")

class TaskRow(Widget.ListBoxRow):
    def __init__(self, task_data: dict, on_toggle: callable, on_delete: callable):
        super().__init__()
        self.task_data = task_data
        
        check = Gtk.CheckButton(active=task_data.get("done", False), valign="center")
        check.connect("toggled", lambda btn: on_toggle(self.task_data, btn.get_active()))

        label = Widget.Label(label=task_data.get("text", ""), halign="start", hexpand=True, wrap=True)
        
        delete_button = Widget.Button(
            icon_name="user-trash-symbolic",
            on_click=lambda x: on_delete(self.task_data),
            css_classes=["todo-delete-button", "unset"],
            tooltip_text="Usuń zadanie"
        )

        self.set_child(Widget.Box(child=[check, label, delete_button], spacing=10))

        if task_data.get("done", False):
            self.add_css_class("task-done")

class TodoView(Widget.Box):
    __gtype_name__ = "TodoView"

    def __init__(self):
        super().__init__(vertical=True, vexpand=True)
        self.data = {}
        self.main_box = Widget.Box(vertical=True, vexpand=True, css_classes=["spacing-10"], style="padding: 1rem;")
        self.append(self.main_box)
        GLib.idle_add(self._load_and_build_ui)

    def _load_data(self):
        if not os.path.exists(TODO_FILE_PATH):
            default_data = {
                "active_list_name": "Prywatne",
                "lists": [
                    {"name": "Prywatne", "tasks": [
                        {"text": "Zrobić zakupy", "done": False},
                        {"text": "Dokończyć projekt Ignis", "done": True}
                    ]},
                    {"name": "Praca", "tasks": []}
                ]
            }
            self.data = default_data
            self._save_data()
            return
        
        try:
            with open(TODO_FILE_PATH, 'r') as f:
                self.data = json.load(f)
        except (json.JSONDecodeError, IOError):
            self.data = {"active_list_name": "Domyślna", "lists": [{"name": "Domyślna", "tasks": []}]}

    def _save_data(self):
        try:
            os.makedirs(os.path.dirname(TODO_FILE_PATH), exist_ok=True)
            with open(TODO_FILE_PATH, 'w') as f:
                json.dump(self.data, f, indent=4, ensure_ascii=False)
        except IOError as e:
            print(f"Błąd zapisu do pliku todo.json: {e}")
    
    def _load_and_build_ui(self):
        self._load_data()
        self._build_full_ui()
        return False

    def _build_full_ui(self):
        if self.main_box.get_first_child():
            self.main_box.remove(self.main_box.get_first_child())

        ui_container = Widget.Box(vertical=True, vexpand=True, css_classes=["spacing-10"])
        self.main_box.append(ui_container)

        list_names = [lst["name"] for lst in self.data.get("lists", [])]
        self.list_selector = Widget.DropDown(items=list_names, on_selected=self._on_list_selected)
        
        active_list_name = self.data.get("active_list_name", list_names[0] if list_names else "")
        if active_list_name in list_names:
            self.list_selector.set_selected(list_names.index(active_list_name))
        
        header_box = Widget.Box(child=[
            Widget.Label(label="Lista zadań:", hexpand=True, halign="start"),
            self.list_selector
        ], css_classes=["todo-header"])

        self.task_list_box = Widget.ListBox(css_classes=["todo-list"])
        placeholder = Widget.Label(label="Brak zadań na tej liście.", css_classes=["dim-label"])
        self.task_list_box.set_placeholder(placeholder)
        
        self._populate_tasks()

        new_task_entry = Widget.Entry(
            placeholder_text="Dodaj nowe zadanie i wciśnij Enter...",
            on_accept=self._on_add_task,
            css_classes=["todo-entry"]
        )

        ui_container.append(header_box)
        ui_container.append(Widget.Scroll(vexpand=True, child=self.task_list_box))
        ui_container.append(new_task_entry)

    def _populate_tasks(self):
        for row in list(self.task_list_box.rows):
            self.task_list_box.remove(row)

        active_list_name = self.data.get("active_list_name")
        active_list = next((lst for lst in self.data.get('lists', []) if lst.get('name') == active_list_name), None)

        if active_list and active_list.get("tasks"):
            for task in active_list["tasks"]:
                row = TaskRow(task, self._on_task_toggled, self._on_task_delete)
                self.task_list_box.append(row)

    def _on_list_selected(self, dropdown, selected_name):
        self.data["active_list_name"] = selected_name
        self._save_data()
        self._populate_tasks()

    def _on_add_task(self, entry: Widget.Entry):
        text = entry.get_text().strip()
        if not text: return
        
        new_task = {"text": text, "done": False}
        active_list_name = self.data["active_list_name"]
        
        for lst in self.data["lists"]:
            if lst["name"] == active_list_name:
                lst["tasks"].append(new_task)
                break
                
        self._save_data()
        self._populate_tasks()
        entry.set_text("")

    def _on_task_toggled(self, task_data: dict, is_done: bool):
        task_data["done"] = is_done
        
        if is_done and os.path.exists(TASK_COMPLETE_SOUND_PATH):
            command = f"/usr/bin/ffplay -nodisp -autoexit -loglevel quiet {TASK_COMPLETE_SOUND_PATH}"
            # Uruchamiamy naszą nową funkcję asynchroniczną w tle
            asyncio.ensure_future(self._play_sound_async(command))

        self._save_data()
        self._populate_tasks()
    
    # --- NOWOŚĆ: Poprawna obsługa procesu asynchronicznego ---
    async def _play_sound_async(self, command: str):
        """
        Asynchronicznie odtwarza dźwięk i loguje ewentualne błędy.
        """
        try:
            # Czekamy na zakończenie procesu, ale nie blokujemy UI
            result = await Utils.exec_sh_async(command)
            if result.returncode != 0:
                print("--- [SOUND DEBUG] Błąd podczas asynchronicznego odtwarzania dźwięku: ---")
                print(f"--- [SOUND DEBUG] Kod powrotu: {result.returncode}")
                print(f"--- [SOUND DEBUG] STDERR: {result.stderr.strip()}")
        except Exception as e:
            print(f"--- [SOUND DEBUG] Wyjątek podczas odtwarzania dźwięku: {e}")

    def _on_task_delete(self, task_data: dict):
        active_list_name = self.data["active_list_name"]
        for lst in self.data["lists"]:
            if lst["name"] == active_list_name:
                lst["tasks"] = [t for t in lst["tasks"] if t != task_data]
                break
        
        self._save_data()
        self._populate_tasks()