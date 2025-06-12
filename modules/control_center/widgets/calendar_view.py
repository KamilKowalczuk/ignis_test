# modules/control_center/widgets/calendar_view.py
# WERSJA OSTATECZNA
import datetime
import re
from ignis.widgets import Widget
from ignis.utils import Utils
from gi.repository import GLib

class CalendarView(Widget.Box):
    __gtype_name__ = "CalendarView"

    def __init__(self):
        super().__init__(
            vertical=True,
            vexpand=True,
            css_classes=["spacing-10"],
            style="padding: 1rem;"
        )

        self.calendar = Widget.Calendar(css_classes=["calendar"])
        self.calendar.connect("next-month", self.refresh_events)
        self.calendar.connect("prev-month", self.refresh_events)

        self.upcoming_events_box = Widget.Box(
            vertical=True,
            css_classes=["spacing-5"],
            child=[
                Widget.Label(label="Nadchodzące wydarzenia:", halign="start"),
                Widget.Separator(style="margin-top: 0.25rem; margin-bottom: 0.5rem;"),
                Widget.Box(vertical=True, name="events-list-container")
            ]
        )
        
        self.append(self.calendar)
        self.append(self.upcoming_events_box)
        
        GLib.idle_add(self.refresh_events)
        Utils.Poll(300000, self.refresh_events)

    def refresh_events(self, *args):
        Utils.ThreadTask(self._fetch_and_parse_events, self._update_ui).run()

    def _fetch_and_parse_events(self):
        try:
            # --- POPRAWKA 1: Używamy prostych, domyślnych znaczników, które działają ---
            command = "khal list --format \"{start};{end};{title};{calendar}\" now 90d"
            result = Utils.exec_sh(command)
            
            if result.returncode != 0:
                print(f"Błąd podczas wykonywania komendy khal:\n{result.stderr}")
                return None

            if not result.stdout.strip():
                return []

            parsed_events = []
            for line in result.stdout.strip().split('\n'):
                # Pomijamy linie, które są nagłówkami dat khal (np. "Today", "Tomorrow")
                if not line.strip() or re.match(r'^[A-Za-z]', line):
                    continue
                
                parts = line.split(';')
                if len(parts) != 4: continue
                
                start_str, end_str, title, calendar_name = parts
                
                try:
                    # --- POPRAWKA 2: Używamy strptime z formatem, który zwraca khal ---
                    event_start_time = datetime.datetime.strptime(start_str, "%d/%m/%Y %H:%M")
                    parsed_events.append({
                        "start_time": event_start_time,
                        "title": title,
                    })
                except ValueError as e:
                    print(f"Pominięto linię z powodu błędu parsowania daty: {e} | Linia: '{line}'")
                    continue
            
            return parsed_events

        except Exception as e:
            print(f"Wystąpił nieoczekiwany błąd podczas pobierania wydarzeń: {e}")
            return None
            
    def _update_ui(self, parsed_events: list[dict] | None):
        if parsed_events is None:
            return
        GLib.idle_add(self._render_ui_updates, parsed_events)

    def _render_ui_updates(self, parsed_events: list[dict]):
        dt = self.calendar.get_date()
        current_year = dt.get_year()
        current_month = dt.get_month()
        
        for day in range(1, 32):
            self.calendar.unmark_day(day)
        
        days_in_current_month_to_mark = {
            event['start_time'].day
            for event in parsed_events
            if event['start_time'].year == current_year and event['start_time'].month == current_month
        }
        for day in days_in_current_month_to_mark:
            self.calendar.mark_day(day)

        events_list_container = self.upcoming_events_box.get_last_child()
        
        for child in list(events_list_container.child):
            events_list_container.remove(child)

        now = datetime.datetime.now()
        future_events = sorted(
            [e for e in parsed_events if e['start_time'] >= now],
            key=lambda e: e['start_time']
        )

        if not future_events:
            events_list_container.append(Widget.Label(label="Brak nadchodzących wydarzeń.", css_classes=["dim-label"]))
            return

        for event in future_events[:5]:
            # Używamy polskiego locale, które ustawiliśmy wcześniej
            date_formatted = event['start_time'].strftime('%a, %d %b')
            time_formatted = event['start_time'].strftime('%H:%M')
            label_str = f"<b>{date_formatted}, {time_formatted}</b> - {event['title']}"
            event_widget = Widget.Label(label=label_str, halign="start", use_markup=True, css_classes=["calendar-event-item"])
            events_list_container.append(event_widget)
        
        return False