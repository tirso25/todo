#!/usr/bin/env python3
"""
TODO App - Aplicación de tareas para terminal con grupos y calendario
Controles:
  a - Añadir tarea
  e - Editar tarea (incluye opción de fecha)
  d - Eliminar tarea
  g - Crear nuevo grupo
  G - Editar/Eliminar grupo
  c - Modo calendario
  ←/→/↑/↓ - Navegar días (calendario) / tareas y grupos (normal)
  Tab - Cambiar mes (calendario)
  Enter - Ver tareas del día (calendario)
  Espacio - Ir al grupo de la tarea (desde tareas del día)
  t - Ir a hoy (calendario)
  q - Salir
"""

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Footer, Header, Input, Label, Static
from textual.binding import Binding
from textual import on
from dataclasses import dataclass
from typing import Optional
import json
from pathlib import Path
from datetime import datetime, date, timedelta
import calendar

MESES = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
         "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
DIAS_SEMANA = ["Lu", "Ma", "Mi", "Ju", "Vi", "Sá", "Do"]


@dataclass
class Task:
    id: int
    text: str
    done: bool = False
    created_at: str = ""
    group_id: Optional[int] = None
    due_date: Optional[str] = None
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().strftime("%d/%m %H:%M")


@dataclass
class Group:
    id: int
    name: str


class TaskWidget(Static):
    DEFAULT_CSS = """
    TaskWidget {
        width: 100%;
        height: 3;
        padding: 0 1;
        border: solid $primary-background;
        margin-bottom: 1;
        layout: horizontal;
    }
    TaskWidget:hover { background: $boost; }
    TaskWidget.selected {
        border: solid $accent;
        background: $surface-lighten-1;
    }
    TaskWidget .checkbox { width: 4; height: 1; }
    TaskWidget .task-text { width: 1fr; height: 1; }
    TaskWidget .task-date { width: 8; height: 1; text-align: right; color: $warning; }
    TaskWidget .task-time { width: 12; height: 1; text-align: right; color: $text-muted; }
    TaskWidget.done .task-text { text-style: strike; color: $text-muted; }
    TaskWidget.done .checkbox { color: $success; }
    TaskWidget.done .task-date { color: $text-muted; }
    """
    
    def __init__(self, task_data: Task, **kwargs) -> None:
        super().__init__(**kwargs)
        self.task_data = task_data
        self._selected = False
    
    def compose(self) -> ComposeResult:
        checkbox = "☑" if self.task_data.done else "☐"
        yield Label(checkbox, classes="checkbox")
        yield Label(self.task_data.text, classes="task-text")
        date_str = ""
        if self.task_data.due_date:
            try:
                d = datetime.strptime(self.task_data.due_date, "%Y-%m-%d")
                date_str = f"📅 {d.day:02d}/{d.month:02d}"
            except: pass
        yield Label(date_str, classes="task-date")
        yield Label(self.task_data.created_at, classes="task-time")
    
    @property
    def selected(self) -> bool:
        return self._selected
    
    @selected.setter
    def selected(self, value: bool) -> None:
        self._selected = value
        self.set_class(value, "selected")
    
    def toggle_done(self) -> None:
        self.task_data.done = not self.task_data.done
        self.set_class(self.task_data.done, "done")
        self.query_one(".checkbox", Label).update("☑" if self.task_data.done else "☐")
    
    def on_mount(self) -> None:
        if self.task_data.done:
            self.add_class("done")


class InputModal(ModalScreen[Optional[str]]):
    DEFAULT_CSS = """
    InputModal { align: center middle; }
    InputModal > Container {
        width: 60; height: auto; border: thick $primary;
        background: $surface; padding: 1 2;
    }
    InputModal .modal-title { text-align: center; text-style: bold; width: 100%; margin-bottom: 1; }
    InputModal Input { width: 100%; margin-bottom: 1; }
    InputModal .button-row { width: 100%; height: auto; align: center middle; }
    InputModal Button { margin: 0 1; }
    """
    BINDINGS = [Binding("escape", "cancel", show=False)]
    
    def __init__(self, title: str = "", initial_text: str = "", placeholder: str = "", **kwargs) -> None:
        super().__init__(**kwargs)
        self.title_text = title
        self.initial_text = initial_text
        self.placeholder_text = placeholder
    
    def compose(self) -> ComposeResult:
        with Container():
            yield Label(self.title_text, classes="modal-title")
            yield Input(value=self.initial_text, placeholder=self.placeholder_text, id="modal-input")
            with Horizontal(classes="button-row"):
                yield Button("Guardar", variant="primary", id="save")
                yield Button("Cancelar", variant="default", id="cancel")
    
    def on_mount(self) -> None:
        self.query_one("#modal-input", Input).focus()
    
    @on(Button.Pressed, "#save")
    def on_save(self) -> None:
        text = self.query_one("#modal-input", Input).value.strip()
        self.dismiss(text if text else None)
    
    @on(Button.Pressed, "#cancel")
    def on_cancel(self) -> None:
        self.dismiss(None)
    
    @on(Input.Submitted)
    def on_submit(self) -> None:
        self.on_save()
    
    def action_cancel(self) -> None:
        self.dismiss(None)


class EditTaskModal(ModalScreen[Optional[dict]]):
    DEFAULT_CSS = """
    EditTaskModal { align: center middle; }
    EditTaskModal > Container {
        width: 60; height: auto; border: thick $primary;
        background: $surface; padding: 1 2;
    }
    EditTaskModal .modal-title { text-align: center; text-style: bold; width: 100%; margin-bottom: 1; }
    EditTaskModal .section-label { margin-top: 1; color: $text-muted; }
    EditTaskModal Input { width: 100%; margin-bottom: 1; }
    EditTaskModal .date-row { width: 100%; height: auto; align: left middle; margin-bottom: 1; }
    EditTaskModal .date-display { width: 1fr; padding: 0 1; }
    EditTaskModal .button-row { width: 100%; height: auto; align: center middle; margin-top: 1; }
    EditTaskModal Button { margin: 0 1; }
    """
    BINDINGS = [Binding("escape", "cancel", show=False)]
    
    def __init__(self, task_text: str, current_date: Optional[str] = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.task_text = task_text
        self.selected_date = current_date
    
    def compose(self) -> ComposeResult:
        with Container():
            yield Label("✏️  Editar Tarea", classes="modal-title")
            yield Label("Texto:", classes="section-label")
            yield Input(value=self.task_text, id="task-input")
            yield Label("Fecha:", classes="section-label")
            with Horizontal(classes="date-row"):
                yield Label(self._format_date(self.selected_date), id="date-display", classes="date-display")
                yield Button("📅 Cambiar", id="change-date")
                yield Button("❌ Quitar", id="remove-date")
            with Horizontal(classes="button-row"):
                yield Button("Guardar", variant="primary", id="save")
                yield Button("Cancelar", variant="default", id="cancel")
    
    def _format_date(self, date_str: Optional[str]) -> str:
        if not date_str: return "Sin fecha"
        try:
            d = datetime.strptime(date_str, "%Y-%m-%d")
            return f"📅 {d.day:02d}/{d.month:02d}/{d.year}"
        except: return "Sin fecha"
    
    def on_mount(self) -> None:
        self.query_one("#task-input", Input).focus()
    
    @on(Button.Pressed, "#change-date")
    def on_change_date(self) -> None:
        def on_result(result: Optional[str]) -> None:
            if result is not None:
                self.selected_date = result if result else None
                self.query_one("#date-display", Label).update(self._format_date(self.selected_date))
        self.app.push_screen(DatePickerModal(self.selected_date), on_result)
    
    @on(Button.Pressed, "#remove-date")
    def on_remove_date(self) -> None:
        self.selected_date = None
        self.query_one("#date-display", Label).update("Sin fecha")
    
    @on(Button.Pressed, "#save")
    def on_save(self) -> None:
        text = self.query_one("#task-input", Input).value.strip()
        self.dismiss({"text": text, "date": self.selected_date} if text else None)
    
    @on(Button.Pressed, "#cancel")
    def on_cancel(self) -> None:
        self.dismiss(None)
    
    def action_cancel(self) -> None:
        self.dismiss(None)


class DatePickerModal(ModalScreen[Optional[str]]):
    DEFAULT_CSS = """
    DatePickerModal { align: center middle; }
    DatePickerModal > Container {
        width: 36; height: auto; border: thick $primary;
        background: $surface; padding: 1 2;
    }
    DatePickerModal .modal-title { text-align: center; text-style: bold; width: 100%; margin-bottom: 1; }
    DatePickerModal .calendar-header { width: 100%; text-align: center; margin-bottom: 1; text-style: bold; }
    DatePickerModal .calendar-display { width: 100%; text-align: center; margin-bottom: 1; }
    DatePickerModal .hint { width: 100%; text-align: center; color: $text-muted; margin-bottom: 1; }
    DatePickerModal .button-row { width: 100%; height: auto; align: center middle; }
    DatePickerModal Button { margin: 0 1; }
    """
    BINDINGS = [
        Binding("escape", "cancel", show=False),
        Binding("left", "prev_day", show=False),
        Binding("right", "next_day", show=False),
        Binding("up", "prev_week", show=False),
        Binding("down", "next_week", show=False),
        Binding("tab", "next_month", show=False),
        Binding("shift+tab", "prev_month", show=False),
        Binding("enter", "select_date", show=False),
    ]
    
    def __init__(self, current_date: Optional[str] = None, **kwargs) -> None:
        super().__init__(**kwargs)
        if current_date:
            try: self.selected_date = datetime.strptime(current_date, "%Y-%m-%d").date()
            except: self.selected_date = date.today()
        else:
            self.selected_date = date.today()
    
    def compose(self) -> ComposeResult:
        with Container():
            yield Label("📅 Seleccionar Fecha", classes="modal-title")
            yield Label("", id="month-label", classes="calendar-header")
            yield Static("", id="calendar-display", classes="calendar-display")
            yield Label("←→↑↓: Día | Tab: Mes", classes="hint")
            with Horizontal(classes="button-row"):
                yield Button("Seleccionar", variant="primary", id="select")
                yield Button("Cancelar", variant="default", id="cancel")
    
    def on_mount(self) -> None:
        self.update_display()
    
    def update_display(self) -> None:
        self.query_one("#month-label", Label).update(f"{MESES[self.selected_date.month]} {self.selected_date.year}")
        cal = calendar.Calendar(firstweekday=0)
        today = date.today()
        lines = ["  ".join(DIAS_SEMANA), "─" * 26]
        for week in cal.monthdayscalendar(self.selected_date.year, self.selected_date.month):
            week_str = ""
            for day in week:
                if day == 0:
                    week_str += "    "
                else:
                    current = date(self.selected_date.year, self.selected_date.month, day)
                    if current == self.selected_date:
                        week_str += f"[bold cyan][{day:2d}][/bold cyan]"
                    elif current == today:
                        week_str += f"[bold green] {day:2d} [/bold green]"
                    else:
                        week_str += f" {day:2d} "
            lines.append(week_str)
        self.query_one("#calendar-display", Static).update("\n".join(lines))
    
    def action_prev_day(self) -> None:
        self.selected_date -= timedelta(days=1)
        self.update_display()
    
    def action_next_day(self) -> None:
        self.selected_date += timedelta(days=1)
        self.update_display()
    
    def action_prev_week(self) -> None:
        self.selected_date -= timedelta(days=7)
        self.update_display()
    
    def action_next_week(self) -> None:
        self.selected_date += timedelta(days=7)
        self.update_display()
    
    def action_prev_month(self) -> None:
        y, m = self.selected_date.year, self.selected_date.month - 1
        if m < 1: m, y = 12, y - 1
        self.selected_date = date(y, m, min(self.selected_date.day, calendar.monthrange(y, m)[1]))
        self.update_display()
    
    def action_next_month(self) -> None:
        y, m = self.selected_date.year, self.selected_date.month + 1
        if m > 12: m, y = 1, y + 1
        self.selected_date = date(y, m, min(self.selected_date.day, calendar.monthrange(y, m)[1]))
        self.update_display()
    
    def action_select_date(self) -> None:
        self.dismiss(self.selected_date.strftime("%Y-%m-%d"))
    
    @on(Button.Pressed, "#select")
    def on_select(self) -> None:
        self.action_select_date()
    
    @on(Button.Pressed, "#cancel")
    def on_cancel(self) -> None:
        self.dismiss(None)
    
    def action_cancel(self) -> None:
        self.dismiss(None)


class ConfirmModal(ModalScreen[bool]):
    DEFAULT_CSS = """
    ConfirmModal { align: center middle; }
    ConfirmModal > Container {
        width: 50; height: auto; border: thick $error;
        background: $surface; padding: 1 2;
    }
    ConfirmModal .modal-title { text-align: center; text-style: bold; width: 100%; margin-bottom: 1; }
    ConfirmModal .button-row { width: 100%; height: auto; align: center middle; }
    ConfirmModal Button { margin: 0 1; }
    ConfirmModal Button.selected { border: solid $accent; }
    """
    BINDINGS = [
        Binding("escape", "cancel", show=False),
        Binding("left", "select_yes", show=False),
        Binding("right", "select_no", show=False),
        Binding("h", "select_yes", show=False),
        Binding("l", "select_no", show=False),
        Binding("enter", "confirm", show=False),
        Binding("space", "confirm", show=False),
    ]
    
    def __init__(self, message: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.message = message
        self.selected_yes = True
    
    def compose(self) -> ComposeResult:
        with Container():
            yield Label(self.message, classes="modal-title")
            with Horizontal(classes="button-row"):
                yield Button("Sí", variant="error", id="yes")
                yield Button("No", variant="default", id="no")
    
    def on_mount(self) -> None:
        self.update_selection()
    
    def update_selection(self) -> None:
        yes_btn = self.query_one("#yes", Button)
        no_btn = self.query_one("#no", Button)
        yes_btn.set_class(self.selected_yes, "selected")
        no_btn.set_class(not self.selected_yes, "selected")
    
    def action_select_yes(self) -> None:
        self.selected_yes = True
        self.update_selection()
    
    def action_select_no(self) -> None:
        self.selected_yes = False
        self.update_selection()
    
    def action_confirm(self) -> None:
        self.dismiss(self.selected_yes)
    
    @on(Button.Pressed, "#yes")
    def on_yes(self) -> None:
        self.dismiss(True)
    
    @on(Button.Pressed, "#no")
    def on_no(self) -> None:
        self.dismiss(False)
    
    def action_cancel(self) -> None:
        self.dismiss(False)


class GroupOptionsModal(ModalScreen[str]):
    DEFAULT_CSS = """
    GroupOptionsModal { align: center middle; }
    GroupOptionsModal > Container {
        width: 40; height: auto; border: thick $primary;
        background: $surface; padding: 1 2;
    }
    GroupOptionsModal .modal-title { text-align: center; text-style: bold; width: 100%; margin-bottom: 1; }
    GroupOptionsModal Button { width: 100%; margin: 1 0; }
    GroupOptionsModal Button.selected { border: solid $accent; }
    """
    BINDINGS = [
        Binding("escape", "cancel", show=False),
        Binding("up", "move_up", show=False),
        Binding("down", "move_down", show=False),
        Binding("k", "move_up", show=False),
        Binding("j", "move_down", show=False),
        Binding("enter", "confirm", show=False),
        Binding("space", "confirm", show=False),
    ]
    
    def __init__(self, group_name: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.group_name = group_name
        self.selected_index = 0
        self.options = ["rename", "delete", ""]
    
    def compose(self) -> ComposeResult:
        with Container():
            yield Label(f"Grupo: {self.group_name}", classes="modal-title")
            yield Button("✏️  Renombrar", variant="primary", id="rename")
            yield Button("🗑️  Eliminar grupo y tareas", variant="error", id="delete")
            yield Button("Cancelar", variant="default", id="cancel")
    
    def on_mount(self) -> None:
        self.update_selection()
    
    def update_selection(self) -> None:
        buttons = [("rename", 0), ("delete", 1), ("cancel", 2)]
        for btn_id, idx in buttons:
            try:
                btn = self.query_one(f"#{btn_id}", Button)
                btn.set_class(idx == self.selected_index, "selected")
            except: pass
    
    def action_move_up(self) -> None:
        self.selected_index = (self.selected_index - 1) % 3
        self.update_selection()
    
    def action_move_down(self) -> None:
        self.selected_index = (self.selected_index + 1) % 3
        self.update_selection()
    
    def action_confirm(self) -> None:
        self.dismiss(self.options[self.selected_index])
    
    @on(Button.Pressed, "#rename")
    def on_rename(self) -> None:
        self.dismiss("rename")
    
    @on(Button.Pressed, "#delete")
    def on_delete(self) -> None:
        self.dismiss("delete")
    
    @on(Button.Pressed, "#cancel")
    def on_cancel(self) -> None:
        self.dismiss("")
    
    def action_cancel(self) -> None:
        self.dismiss("")


class DayTasksModal(ModalScreen[Optional[Task]]):
    DEFAULT_CSS = """
    DayTasksModal { align: center middle; }
    DayTasksModal > Container {
        width: 70; height: 20; border: thick $primary;
        background: $surface; padding: 1 2;
    }
    DayTasksModal .modal-title { text-align: center; text-style: bold; width: 100%; margin-bottom: 1; }
    DayTasksModal #tasks-list { width: 100%; height: 1fr; overflow-y: auto; }
    DayTasksModal .task-item {
        width: 100%; height: 3; padding: 0 1;
        border: solid $primary-background; margin-bottom: 1;
    }
    DayTasksModal .task-item:hover { background: $boost; }
    DayTasksModal .task-item.selected { border: solid $accent; background: $surface-lighten-1; }
    DayTasksModal .hint { width: 100%; text-align: center; color: $text-muted; margin-top: 1; }
    DayTasksModal .empty-msg { width: 100%; text-align: center; color: $text-muted; text-style: italic; padding: 2; }
    """
    BINDINGS = [
        Binding("escape", "cancel", show=False),
        Binding("up", "move_up", show=False),
        Binding("down", "move_down", show=False),
        Binding("k", "move_up", show=False),
        Binding("j", "move_down", show=False),
        Binding("space", "go_to_task", show=False),
        Binding("enter", "go_to_task", show=False),
    ]
    
    def __init__(self, tasks: list[tuple[Task, str]], date_str: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.tasks = tasks
        self.date_str = date_str
        self.selected_index = 0
    
    def compose(self) -> ComposeResult:
        with Container():
            yield Label(f"📅 Tareas del {self.date_str}", classes="modal-title")
            yield Container(id="tasks-list")
            yield Label("↑↓ Navegar | Espacio/Enter: Ir al grupo | Esc: Cerrar", classes="hint")
    
    async def on_mount(self) -> None:
        tasks_list = self.query_one("#tasks-list", Container)
        if not self.tasks:
            await tasks_list.mount(Label("No hay tareas para este día", classes="empty-msg"))
        else:
            for i, (task, group_name) in enumerate(self.tasks):
                checkbox = "☑" if task.done else "☐"
                text = f"{checkbox} {task.text}  [{group_name}]"
                item = Static(text, id=f"task-item-{i}", classes="task-item")
                await tasks_list.mount(item)
                if i == 0:
                    item.add_class("selected")
    
    def update_selection(self) -> None:
        for i in range(len(self.tasks)):
            try:
                item = self.query_one(f"#task-item-{i}", Static)
                item.set_class(i == self.selected_index, "selected")
            except: pass
    
    def action_move_up(self) -> None:
        if self.tasks and self.selected_index > 0:
            self.selected_index -= 1
            self.update_selection()
    
    def action_move_down(self) -> None:
        if self.tasks and self.selected_index < len(self.tasks) - 1:
            self.selected_index += 1
            self.update_selection()
    
    def action_go_to_task(self) -> None:
        if self.tasks:
            self.dismiss(self.tasks[self.selected_index][0])
    
    def action_cancel(self) -> None:
        self.dismiss(None)


class SearchResultsScreen(ModalScreen[Optional[Task]]):
    DEFAULT_CSS = """
    SearchResultsScreen { align: center middle; }
    SearchResultsScreen > Container {
        width: 70; height: 20; border: thick $primary;
        background: $surface; padding: 1 2;
    }
    SearchResultsScreen .modal-title { text-align: center; text-style: bold; width: 100%; margin-bottom: 1; }
    SearchResultsScreen #results-list { width: 100%; height: 1fr; overflow-y: auto; }
    SearchResultsScreen .result-item {
        width: 100%; height: 3; padding: 0 1;
        border: solid $primary-background; margin-bottom: 1;
    }
    SearchResultsScreen .result-item:hover { background: $boost; }
    SearchResultsScreen .result-item.selected { border: solid $accent; background: $surface-lighten-1; }
    SearchResultsScreen .hint { width: 100%; text-align: center; color: $text-muted; margin-top: 1; }
    """
    BINDINGS = [
        Binding("escape", "cancel", show=False),
        Binding("up", "move_up", show=False),
        Binding("down", "move_down", show=False),
        Binding("enter", "select_result", show=False),
    ]
    
    def __init__(self, results: list[tuple[Task, str]], search_term: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.results = results
        self.search_term = search_term
        self.selected_index = 0
    
    def compose(self) -> ComposeResult:
        with Container():
            yield Label(f"🔍 Resultados para '{self.search_term}'", classes="modal-title")
            yield Container(id="results-list")
            yield Label("↑↓ Navegar | Enter: Ir al grupo | Esc: Cerrar", classes="hint")
    
    async def on_mount(self) -> None:
        results_list = self.query_one("#results-list", Container)
        for i, (task, group_name) in enumerate(self.results):
            text = f"{task.text}  [{group_name}]"
            item = Static(text, id=f"result-{i}", classes="result-item")
            await results_list.mount(item)
            if i == 0:
                item.add_class("selected")
    
    def update_selection(self) -> None:
        for i in range(len(self.results)):
            try:
                item = self.query_one(f"#result-{i}", Static)
                item.set_class(i == self.selected_index, "selected")
            except: pass
    
    def action_move_up(self) -> None:
        if self.selected_index > 0:
            self.selected_index -= 1
            self.update_selection()
    
    def action_move_down(self) -> None:
        if self.selected_index < len(self.results) - 1:
            self.selected_index += 1
            self.update_selection()
    
    def action_select_result(self) -> None:
        if self.results:
            self.dismiss(self.results[self.selected_index][0])
    
    def action_cancel(self) -> None:
        self.dismiss(None)


class GroupTab(Static):
    DEFAULT_CSS = """
    GroupTab {
        width: auto; height: 3; padding: 0 2; margin: 0 1;
        border: solid $primary-background; content-align: center middle;
    }
    GroupTab:hover { background: $boost; }
    GroupTab.active { border: solid $accent; background: $accent 20%; text-style: bold; }
    """
    
    def __init__(self, group_id: Optional[int], name: str, **kwargs) -> None:
        super().__init__(name, **kwargs)
        self.group_id = group_id
        self._active = False
    
    @property
    def active(self) -> bool:
        return self._active
    
    @active.setter
    def active(self, value: bool) -> None:
        self._active = value
        self.set_class(value, "active")


class TodoApp(App):
    CSS = """
    Screen { background: $background; }
    #main-container { width: 100%; height: 1fr; padding: 0 2; }
    #tabs-container { width: 100%; height: 3; layout: horizontal; padding: 0 1; }
    #task-list { width: 100%; height: 1fr; overflow-y: auto; padding: 1; }
    #calendar-view { width: 100%; height: 1fr; padding: 1; display: none; align: center top; }
    #calendar-view.visible { display: block; }
    #calendar-header { width: 100%; text-align: center; text-style: bold; padding: 1; }
    #calendar-display { width: 100%; text-align: center; padding: 1; }
    #calendar-day-tasks { width: 100%; text-align: center; padding: 1; margin-top: 1; border-top: solid $primary-background; }
    #calendar-hint { width: 100%; text-align: center; color: $text-muted; padding: 1; }
    #empty-message { width: 100%; height: 100%; content-align: center middle; color: $text-muted; text-style: italic; }
    #stats { dock: bottom; width: 100%; height: 1; background: $primary-background; color: $text; padding: 0 2; }
    #completed-separator { width: 100%; height: 1; text-align: center; color: $text-muted; margin: 1 0; }
    """
    
    BINDINGS = [
        Binding("a", "add_task", "Añadir"),
        Binding("e", "edit_task", "Editar"),
        Binding("d", "delete_task", "Eliminar"),
        Binding("g", "new_group", "Nuevo Grupo"),
        Binding("G", "group_options", "Opc. Grupo"),
        Binding("c", "toggle_calendar", "Calendario"),
        Binding("/", "search", "Buscar"),
        Binding("left", "nav_left", show=False),
        Binding("right", "nav_right", show=False),
        Binding("up", "nav_up", show=False),
        Binding("down", "nav_down", show=False),
        Binding("h", "nav_left", show=False),
        Binding("l", "nav_right", show=False),
        Binding("k", "nav_up", show=False),
        Binding("j", "nav_down", show=False),
        Binding("tab", "next_month", show=False),
        Binding("shift+tab", "prev_month", show=False),
        Binding("t", "go_today", show=False),
        Binding("space", "toggle_done", "Completar"),
        Binding("enter", "action_enter", show=False),
        Binding("q", "quit", "Salir"),
    ]
    
    TITLE = "📋 TODO App"
    
    def __init__(self) -> None:
        super().__init__()
        self.tasks: list[Task] = []
        self.groups: list[Group] = []
        self.next_task_id = 1
        self.next_group_id = 1
        self.selected_index = 0
        self.current_group_id: Optional[int] = None
        self.data_file = Path.home() / "todo" / "todo_tasks.json"
        self.data_file.parent.mkdir(exist_ok=True)
        
        self.calendar_mode = False
        self.cal_year = date.today().year
        self.cal_month = date.today().month
        self.cal_day = date.today().day
        
        self.load_data()
    
    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="main-container"):
            yield Horizontal(id="tabs-container")
            yield Container(id="task-list")
            with Container(id="calendar-view"):
                yield Static("", id="calendar-header")
                yield Static("", id="calendar-display")
                yield Static("", id="calendar-day-tasks")
                yield Static("←→↑↓: Navegar | Tab: Mes | t: Hoy | Enter: Ver tareas | c: Volver", id="calendar-hint")
            yield Static("", id="stats")
        yield Footer()
    
    async def on_mount(self) -> None:
        await self.refresh_tabs()
        await self.refresh_view()
        self.update_stats()
    
    async def refresh_tabs(self) -> None:
        tabs = self.query_one("#tabs-container", Horizontal)
        await tabs.remove_children()
        
        if self.calendar_mode:
            tab = GroupTab(None, "📅 Calendario", id="tab-calendar")
            await tabs.mount(tab)
            tab.active = True
        else:
            tab = GroupTab(None, "📋 Sin grupo", id="tab-all")
            await tabs.mount(tab)
            tab.active = (self.current_group_id is None)
            
            for g in self.groups:
                icon = "📂" if self.current_group_id == g.id else "📁"
                t = GroupTab(g.id, f"{icon} {g.name}", id=f"tab-{g.id}")
                await tabs.mount(t)
                t.active = (self.current_group_id == g.id)
    
    def _get_current_tasks(self) -> list[Task]:
        if self.current_group_id is None:
            return [t for t in self.tasks if t.group_id is None]
        return [t for t in self.tasks if t.group_id == self.current_group_id]
    
    def _get_tasks_for_date(self, y: int, m: int, d: int) -> list[tuple[Task, str]]:
        date_str = f"{y:04d}-{m:02d}-{d:02d}"
        result = []
        for t in self.tasks:
            if t.due_date == date_str:
                if t.group_id is None:
                    gname = "Sin grupo"
                else:
                    g = next((x for x in self.groups if x.id == t.group_id), None)
                    gname = g.name if g else "Sin grupo"
                result.append((t, gname))
        return result
    
    async def refresh_view(self) -> None:
        task_list = self.query_one("#task-list", Container)
        calendar_view = self.query_one("#calendar-view", Container)
        
        if self.calendar_mode:
            task_list.styles.display = "none"
            calendar_view.add_class("visible")
            calendar_view.styles.display = "block"
            self.refresh_calendar()
        else:
            task_list.styles.display = "block"
            calendar_view.remove_class("visible")
            calendar_view.styles.display = "none"
            await self._refresh_task_list(task_list)
    
    async def _refresh_task_list(self, task_list: Container) -> None:
        await task_list.remove_children()
        current = self._get_current_tasks()
        pending = [t for t in current if not t.done]
        completed = [t for t in current if t.done]
        
        if not current:
            msg = "No hay tareas. Pulsa 'a' para añadir una."
            await task_list.mount(Label(msg, id="empty-message"))
        else:
            for t in pending:
                w = TaskWidget(t, id=f"task-{t.id}")
                await task_list.mount(w)
            if completed:
                await task_list.mount(Static("── Completadas ──", id="completed-separator"))
                for t in completed:
                    w = TaskWidget(t, id=f"task-{t.id}")
                    await task_list.mount(w)
        
        self._update_selection(pending, completed)
    
    def refresh_calendar(self) -> None:
        self.query_one("#calendar-header", Static).update(f"{MESES[self.cal_month]} {self.cal_year}")
        
        cal = calendar.Calendar(firstweekday=0)
        today = date.today()
        lines = ["  ".join(DIAS_SEMANA), "─" * 26]
        
        for week in cal.monthdayscalendar(self.cal_year, self.cal_month):
            week_str = ""
            for day in week:
                if day == 0:
                    week_str += "    "
                else:
                    current = date(self.cal_year, self.cal_month, day)
                    has_tasks = any(t.due_date == current.strftime("%Y-%m-%d") for t in self.tasks)
                    
                    if day == self.cal_day:
                        week_str += f"[bold cyan][{day:2d}][/bold cyan]"
                    elif current == today:
                        week_str += f"[bold green]•{day:2d} [/bold green]" if has_tasks else f"[bold green] {day:2d} [/bold green]"
                    elif has_tasks:
                        week_str += f"[yellow]•{day:2d} [/yellow]"
                    else:
                        week_str += f" {day:2d} "
            lines.append(week_str)
        
        self.query_one("#calendar-display", Static).update("\n".join(lines))
        
        tasks = self._get_tasks_for_date(self.cal_year, self.cal_month, self.cal_day)
        day_tasks = self.query_one("#calendar-day-tasks", Static)
        
        if tasks:
            lines = [f"📋 {len(tasks)} tarea(s):"]
            for t, gname in tasks[:3]:
                cb = "☑" if t.done else "☐"
                txt = t.text[:30] + "..." if len(t.text) > 30 else t.text
                lines.append(f"  {cb} {txt} [{gname}]")
            if len(tasks) > 3:
                lines.append(f"  ... y {len(tasks) - 3} más")
            day_tasks.update("\n".join(lines))
        else:
            day_tasks.update("No hay tareas para este día")
    
    def _update_selection(self, pending: list, completed: list) -> None:
        all_tasks = pending + completed
        if not all_tasks:
            self.selected_index = 0
            return
        self.selected_index = max(0, min(self.selected_index, len(all_tasks) - 1))
        for i, t in enumerate(all_tasks):
            try:
                w = self.query_one(f"#task-{t.id}", TaskWidget)
                w.selected = (i == self.selected_index)
            except: pass
    
    def _get_ordered_tasks(self) -> list:
        c = self._get_current_tasks()
        return [t for t in c if not t.done] + [t for t in c if t.done]
    
    def update_selection(self) -> None:
        ordered = self._get_ordered_tasks()
        if not ordered: return
        self.selected_index = max(0, min(self.selected_index, len(ordered) - 1))
        for i, t in enumerate(ordered):
            try:
                self.query_one(f"#task-{t.id}", TaskWidget).selected = (i == self.selected_index)
            except: pass
    
    def update_stats(self) -> None:
        if self.calendar_mode:
            tasks = self._get_tasks_for_date(self.cal_year, self.cal_month, self.cal_day)
            total, done = len(tasks), sum(1 for t, _ in tasks if t.done)
            text = f"📅 {self.cal_day}/{self.cal_month}/{self.cal_year} | Tareas: {total} | Completadas: {done}"
        else:
            c = self._get_current_tasks()
            total, done = len(c), sum(1 for t in c if t.done)
            gname = "Sin grupo"
            if self.current_group_id:
                g = next((x for x in self.groups if x.id == self.current_group_id), None)
                gname = g.name if g else "Sin grupo"
            text = f"Total: {total} | Completadas: {done} | Pendientes: {total - done} | Grupo: {gname}"
        self.query_one("#stats", Static).update(text)
    
    def get_selected_widget(self) -> Optional[TaskWidget]:
        ordered = self._get_ordered_tasks()
        if not ordered or self.selected_index >= len(ordered): return None
        try: return self.query_one(f"#task-{ordered[self.selected_index].id}", TaskWidget)
        except: return None
    
    # Navigation
    async def action_nav_left(self) -> None:
        if self.calendar_mode:
            d = date(self.cal_year, self.cal_month, self.cal_day) - timedelta(days=1)
            self.cal_year, self.cal_month, self.cal_day = d.year, d.month, d.day
            self.refresh_calendar()
            self.update_stats()
        else:
            await self._prev_group()
    
    async def action_nav_right(self) -> None:
        if self.calendar_mode:
            d = date(self.cal_year, self.cal_month, self.cal_day) + timedelta(days=1)
            self.cal_year, self.cal_month, self.cal_day = d.year, d.month, d.day
            self.refresh_calendar()
            self.update_stats()
        else:
            await self._next_group()
    
    async def action_nav_up(self) -> None:
        if self.calendar_mode:
            d = date(self.cal_year, self.cal_month, self.cal_day) - timedelta(days=7)
            self.cal_year, self.cal_month, self.cal_day = d.year, d.month, d.day
            self.refresh_calendar()
            self.update_stats()
        else:
            if self._get_ordered_tasks() and self.selected_index > 0:
                self.selected_index -= 1
                self.update_selection()
    
    async def action_nav_down(self) -> None:
        if self.calendar_mode:
            d = date(self.cal_year, self.cal_month, self.cal_day) + timedelta(days=7)
            self.cal_year, self.cal_month, self.cal_day = d.year, d.month, d.day
            self.refresh_calendar()
            self.update_stats()
        else:
            ordered = self._get_ordered_tasks()
            if ordered and self.selected_index < len(ordered) - 1:
                self.selected_index += 1
                self.update_selection()
    
    def action_next_month(self) -> None:
        if self.calendar_mode:
            self.cal_month += 1
            if self.cal_month > 12:
                self.cal_month, self.cal_year = 1, self.cal_year + 1
            self.cal_day = min(self.cal_day, calendar.monthrange(self.cal_year, self.cal_month)[1])
            self.refresh_calendar()
            self.update_stats()
    
    def action_prev_month(self) -> None:
        if self.calendar_mode:
            self.cal_month -= 1
            if self.cal_month < 1:
                self.cal_month, self.cal_year = 12, self.cal_year - 1
            self.cal_day = min(self.cal_day, calendar.monthrange(self.cal_year, self.cal_month)[1])
            self.refresh_calendar()
            self.update_stats()
    
    def action_go_today(self) -> None:
        if self.calendar_mode:
            today = date.today()
            self.cal_year, self.cal_month, self.cal_day = today.year, today.month, today.day
            self.refresh_calendar()
            self.update_stats()
    
    async def _prev_group(self) -> None:
        ids = [None] + [g.id for g in self.groups]
        idx = (ids.index(self.current_group_id) - 1) % len(ids)
        self.current_group_id = ids[idx]
        self.selected_index = 0
        await self.refresh_tabs()
        await self.refresh_view()
        self.update_stats()
    
    async def _next_group(self) -> None:
        ids = [None] + [g.id for g in self.groups]
        idx = (ids.index(self.current_group_id) + 1) % len(ids)
        self.current_group_id = ids[idx]
        self.selected_index = 0
        await self.refresh_tabs()
        await self.refresh_view()
        self.update_stats()
    
    async def action_toggle_calendar(self) -> None:
        self.calendar_mode = not self.calendar_mode
        if self.calendar_mode:
            today = date.today()
            self.cal_year, self.cal_month, self.cal_day = today.year, today.month, today.day
        await self.refresh_tabs()
        await self.refresh_view()
        self.update_stats()
    
    def action_action_enter(self) -> None:
        if self.calendar_mode:
            tasks = self._get_tasks_for_date(self.cal_year, self.cal_month, self.cal_day)
            date_str = f"{self.cal_day}/{self.cal_month}/{self.cal_year}"
            self.push_screen(DayTasksModal(tasks, date_str), lambda t: self._go_to_task(t) if t else None)
        else:
            self.action_toggle_done()
    
    async def action_toggle_done(self) -> None:
        if not self.calendar_mode:
            w = self.get_selected_widget()
            if w:
                w.toggle_done()
                self.update_stats()
                self.save_data()
                await self.refresh_view()
    
    def _go_to_task(self, task: Task) -> None:
        async def nav() -> None:
            self.calendar_mode = False
            self.current_group_id = task.group_id
            self.selected_index = 0
            await self.refresh_tabs()
            await self.refresh_view()
            self.update_stats()
            for i, t in enumerate(self._get_ordered_tasks()):
                if t.id == task.id:
                    self.selected_index = i
                    break
            self.update_selection()
        self.call_later(nav)
    
    # Search
    def action_search(self) -> None:
        def on_input(query: Optional[str]) -> None:
            if not query: return
            results = []
            for t in self.tasks:
                if query.lower() in t.text.lower():
                    gname = "Sin grupo"
                    if t.group_id:
                        g = next((x for x in self.groups if x.id == t.group_id), None)
                        gname = g.name if g else "Sin grupo"
                    results.append((t, gname))
            if not results:
                self.notify(f"No se encontraron tareas para '{query}'")
            elif len(results) == 1:
                self._go_to_task(results[0][0])
            else:
                self.push_screen(SearchResultsScreen(results, query), lambda t: self._go_to_task(t) if t else None)
        self.push_screen(InputModal("🔍 Buscar", placeholder="Buscar tareas..."), on_input)
    
    # Groups
    def action_new_group(self) -> None:
        if self.calendar_mode: return
        async def on_result(name: Optional[str]) -> None:
            if name:
                g = Group(id=self.next_group_id, name=name)
                self.next_group_id += 1
                self.groups.append(g)
                self.current_group_id = g.id
                self.selected_index = 0
                await self.refresh_tabs()
                await self.refresh_view()
                self.update_stats()
                self.save_data()
        self.push_screen(InputModal("Nuevo Grupo", placeholder="Nombre..."), on_result)
    
    def action_group_options(self) -> None:
        if self.calendar_mode or self.current_group_id is None: return
        g = next((x for x in self.groups if x.id == self.current_group_id), None)
        if not g: return
        async def on_opt(opt: str) -> None:
            if opt == "rename":
                def on_name(name: Optional[str]) -> None:
                    if name:
                        g.name = name
                        self.call_later(self._after_rename)
                self.push_screen(InputModal("Renombrar", initial_text=g.name), on_name)
            elif opt == "delete":
                count = len([t for t in self.tasks if t.group_id == g.id])
                async def on_confirm(yes: bool) -> None:
                    if yes:
                        self.tasks = [t for t in self.tasks if t.group_id != g.id]
                        self.groups.remove(g)
                        self.current_group_id = None
                        self.selected_index = 0
                        await self.refresh_tabs()
                        await self.refresh_view()
                        self.update_stats()
                        self.save_data()
                self.push_screen(ConfirmModal(f"¿Eliminar '{g.name}' y sus {count} tareas?"), on_confirm)
        self.push_screen(GroupOptionsModal(g.name), on_opt)
    
    async def _after_rename(self) -> None:
        await self.refresh_tabs()
        self.update_stats()
        self.save_data()
    
    # Tasks
    def action_add_task(self) -> None:
        if self.calendar_mode: return
        async def on_result(text: Optional[str]) -> None:
            if text:
                t = Task(id=self.next_task_id, text=text, group_id=self.current_group_id)
                self.next_task_id += 1
                self.tasks.append(t)
                pending = [x for x in self._get_current_tasks() if not x.done]
                self.selected_index = len(pending) - 1
                await self.refresh_view()
                self.update_stats()
                self.save_data()
        self.push_screen(InputModal("Nueva Tarea", placeholder="Escribe la tarea..."), on_result)
    
    def action_edit_task(self) -> None:
        if self.calendar_mode: return
        w = self.get_selected_widget()
        if not w: return
        t = w.task_data
        async def on_result(result: Optional[dict]) -> None:
            if result:
                t.text = result["text"]
                t.due_date = result["date"]
                self.save_data()
                await self.refresh_view()
        self.push_screen(EditTaskModal(t.text, t.due_date), on_result)
    
    def action_delete_task(self) -> None:
        if self.calendar_mode: return
        ordered = self._get_ordered_tasks()
        if not ordered: return
        t = ordered[self.selected_index]
        async def on_confirm(yes: bool) -> None:
            if yes:
                self.tasks.remove(t)
                if self.selected_index >= len(self._get_ordered_tasks()) and self.selected_index > 0:
                    self.selected_index -= 1
                await self.refresh_view()
                self.update_stats()
                self.save_data()
        txt = t.text[:30] + "..." if len(t.text) > 30 else t.text
        self.push_screen(ConfirmModal(f"¿Eliminar '{txt}'?"), on_confirm)
    
    # Persistence
    def save_data(self) -> None:
        data = {
            "next_task_id": self.next_task_id,
            "next_group_id": self.next_group_id,
            "groups": [{"id": g.id, "name": g.name} for g in self.groups],
            "tasks": [{"id": t.id, "text": t.text, "done": t.done, "created_at": t.created_at,
                       "group_id": t.group_id, "due_date": t.due_date} for t in self.tasks]
        }
        try: self.data_file.write_text(json.dumps(data, ensure_ascii=False, indent=2))
        except: pass
    
    def load_data(self) -> None:
        try:
            if self.data_file.exists():
                data = json.loads(self.data_file.read_text())
                self.next_task_id = data.get("next_task_id", 1)
                self.next_group_id = data.get("next_group_id", 1)
                self.groups = [Group(id=g["id"], name=g["name"]) for g in data.get("groups", [])]
                self.tasks = [Task(id=t["id"], text=t["text"], done=t.get("done", False),
                                   created_at=t.get("created_at", ""), group_id=t.get("group_id"),
                                   due_date=t.get("due_date")) for t in data.get("tasks", [])]
        except:
            self.tasks, self.groups = [], []
            self.next_task_id = self.next_group_id = 1


def main():
    TodoApp().run()


if __name__ == "__main__":
    main()
