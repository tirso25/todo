#!/usr/bin/env python3
"""
TODO App - Aplicación de tareas para terminal con grupos, calendario, etiquetas y filtros
Controles principales:
  a - Añadir tarea (no disponible en grupo General)
  e - Editar tarea (texto, fecha, grupo, comentarios, etiquetas)
  d - Eliminar tarea
  f - Filtrar tareas (por fecha, etiquetas y estado)
  o - Ordenar tareas (alfabético, fecha, prioridad)
  / - Buscar tareas por texto
  i - Ver tareas de hoy
  Ctrl+Z - Deshacer última acción
  Ctrl+Y - Rehacer acción deshecha
  Espacio - Marcar/Desmarcar tarea como completada
  q - Salir

Gestión de grupos:
  g - Crear nuevo grupo
  G - Editar/Eliminar grupo (no disponible en General ni Sin grupo)
  ←/→ o h/l - Navegar entre grupos
  Tab: General → Sin grupo → Grupos personalizados

Grupos especiales:
  📚 General - Muestra TODAS las tareas (sin permitir crear nuevas)
  📋 Sin grupo - Tareas sin grupo asignado

Gestión de etiquetas:
  T - Gestionar etiquetas globales (crear, editar, eliminar)
  (Las etiquetas se asignan desde la edición de tareas)

Gestión de comentarios:
  💬 Comentarios con enlaces (URLs)
  🔗 Icono indica comentarios con enlaces
  Enter - Abrir enlace del comentario seleccionado

Modo calendario:
  c - Activar/Desactivar modo calendario
  ←/→/↑/↓ - Navegar días
  n/p - Mes siguiente/anterior
  t - Ir a hoy
  Enter - Ver tareas del día seleccionado
  Espacio - Ir al grupo de la tarea (desde vista de tareas del día)

Navegación de tareas:
  ↑/↓ o k/j - Navegar entre tareas
  Enter - Marcar/Desmarcar como completada (modo normal)

Filtros disponibles:
  📅 Fecha - Múltiples fechas (Sin fecha o fechas específicas)
  🏷️ Etiquetas - Múltiples etiquetas (modo AND)
  ✅ Estado - Pendientes y/o Completadas
  ⭐ Prioridad - Sin prioridad, Baja, Media, Alta

Ordenación disponible:
  🔤 Alfabético - A→Z o Z→A
  📅 Fecha - Más próximas o más lejanas primero
  ⭐ Prioridad - Alta→Baja o Baja→Alta
  (Se pueden combinar múltiples criterios)

Sistema de Deshacer/Rehacer:
  • Ctrl+Z - Deshacer última acción (hasta 50 acciones)
  • Ctrl+Y - Rehacer acción deshecha
  • Funciona con: crear, editar, eliminar tareas/grupos/etiquetas
  • Restaura estado completo (tareas, grupos, etiquetas, selección)
  • Se limpia al hacer una nueva acción tras deshacer

Características:
  • Auto-guardado cada 10 segundos (silencioso)
  • Guardado automático al salir
  • Recordatorios de tareas que vencen hoy
  • Comentarios en tareas con enlaces opcionales
  • Hasta 2 etiquetas visibles por tarea
  • Visualización de fecha de vencimiento
  • Contador de comentarios y enlaces
  • Separación visual de tareas completadas
  • Estadísticas en tiempo real
  • Búsqueda global de tareas
  • Sistema completo de deshacer/rehacer
  • Tema Dracula por defecto
"""

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Footer, Header, Input, Label, Static
from textual.binding import Binding
from textual import on
from dataclasses import dataclass
from typing import Optional
from threading import Lock
import json
from pathlib import Path
from datetime import datetime, date, timedelta
import calendar
import webbrowser
import pyperclip 
from PIL import Image 
import tkinter as tk
from tkinter import filedialog
import shutil
from rich_pixels import Pixels
from rich.console import Console
import subprocess
import shutil
import platform
from pathlib import Path
from PIL import Image
import os
from rich_pixels import Pixels

MESES = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
DIAS_SEMANA = ["Lu", "Ma", "Mi", "Ju", "Vi", "Sá", "Do"]

@dataclass
class Comment:
    id: int
    text: str
    url: Optional[str] = None
    image_path: Optional[str] = None
    created_at: str = ""
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().strftime("%d/%m %H:%M")

@dataclass
class Subtask:
    id: int
    text: str
    done: bool = False
    created_at: str = ""
    due_date: Optional[str] = None
    comments: list = None
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().strftime("%d/%m %H:%M")
        if self.comments is None:
            self.comments = []

@dataclass
class Tag:
    id: int
    name: str
    
    def __post_init__(self):
        self.name = self.name[:30]

@dataclass
class Task:
    id: int
    text: str
    done: bool = False
    created_at: str = ""
    group_id: Optional[int] = None
    due_date: Optional[str] = None
    comments: list = None
    tags: list = None
    priority: int = 0
    subtasks: list = None
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().strftime("%d/%m %H:%M")
        if self.comments is None:
            self.comments = []
        if self.tags is None:
            self.tags = []
        if self.subtasks is None:
            self.subtasks = []

@dataclass
class Group:
    id: int
    name: str

class SubtasksModal(ModalScreen[list]):
    DEFAULT_CSS = """
    SubtasksModal { align: center middle; }
    SubtasksModal > Container {
        width: 80; height: 30; border: thick $primary;
        background: $surface; padding: 1 2;
    }
    SubtasksModal .modal-title { text-align: center; text-style: bold; width: 100%; height: 1; margin-bottom: 1; }
    SubtasksModal #subtasks-list { width: 100%; height: 16; overflow-y: auto; border: solid $primary-background; padding: 1; }
    SubtasksModal .subtask-item {
        width: 100%; height: 3; padding: 0 1;
        border: solid $primary-background; margin-bottom: 1;
        layout: horizontal;
    }
    SubtasksModal .subtask-item:hover { background: $boost; }
    SubtasksModal .subtask-item.selected { border: solid $accent; background: $surface-lighten-1; }
    SubtasksModal .subtask-item.done .subtask-text { text-style: strike; color: $text-muted; }
    SubtasksModal .subtask-checkbox { width: 4; height: 1; }
    SubtasksModal .subtask-text { width: 1fr; height: 1; }
    SubtasksModal .subtask-comments { width: 5; height: 1; text-align: right; color: $primary; }
    SubtasksModal .subtask-date { width: 10; height: 1; text-align: right; color: $warning; }
    SubtasksModal .empty-msg { width: 100%; text-align: center; color: $text-muted; text-style: italic; padding: 2; }
    SubtasksModal .hint { width: 100%; height: auto; text-align: center; color: $text-muted; margin: 1 0; padding: 0 2; }
    SubtasksModal .button-row { width: 100%; height: 3; align: center middle; }
    SubtasksModal Button { margin: 0 1; }
    """
    BINDINGS = [
        Binding("escape", "close", show=False),
        Binding("up", "move_up", show=False),
        Binding("down", "move_down", show=False),
        Binding("k", "move_up", show=False),
        Binding("j", "move_down", show=False),
        Binding("a", "add_subtask", show=False),
        Binding("e", "edit_subtask", show=False),
        Binding("d", "delete_subtask", show=False),
        Binding("space", "toggle_subtask", show=False),
        Binding("D", "set_date", show=False),
    ]
    
    def __init__(self, subtasks: list, next_subtask_id: int, next_comment_id: int, **kwargs) -> None:
        super().__init__(**kwargs)
        self.subtasks = [Subtask(id=s.id, text=s.text, done=s.done, 
                                created_at=s.created_at, due_date=s.due_date,
                                comments=s.comments if hasattr(s, 'comments') else []) 
                        for s in subtasks]
        self.next_subtask_id = next_subtask_id
        self.next_comment_id = next_comment_id
        self.selected_index = 0 if subtasks else -1
    
    def compose(self) -> ComposeResult:
        with Container():
            yield Label("📋 Subtareas", classes="modal-title")
            yield Container(id="subtasks-list")
            yield Label(
                "↑↓/k/j: Navegar | a: Añadir | e: Editar | d: Eliminar\n"
                "Espacio: Completar | D: Fecha | Esc: Cerrar",
                classes="hint"
            )
            with Horizontal(classes="button-row"):
                yield Button("➕ Añadir", variant="primary", id="add")
                yield Button("✏️ Editar", variant="default", id="edit")
                yield Button("🗑️ Eliminar", variant="error", id="delete")
    
    async def on_mount(self) -> None:
        await self.refresh_subtasks_list()
    
    async def refresh_subtasks_list(self) -> None:
        subtasks_list = self.query_one("#subtasks-list", Container)
        await subtasks_list.remove_children()
        
        if not self.subtasks:
            await subtasks_list.mount(Label("No hay subtareas. Pulsa 'a' para añadir una.", classes="empty-msg"))
            self.selected_index = -1
        else:
            for i, subtask in enumerate(self.subtasks):
                item = Horizontal(id=f"subtask-{i}", classes="subtask-item")
                await subtasks_list.mount(item)
                
                checkbox = "☑" if subtask.done else "☐"
                await item.mount(Label(checkbox, classes="subtask-checkbox"))
                
                await item.mount(Label(subtask.text, classes="subtask-text"))
                
                comments_str = f"💬{len(subtask.comments)}" if subtask.comments else ""
                await item.mount(Label(comments_str, classes="subtask-comments"))
                
                date_str = ""
                if subtask.due_date:
                    try:
                        d = datetime.strptime(subtask.due_date, "%Y-%m-%d")
                        date_str = f"📅 {d.day:02d}/{d.month:02d}"
                    except: pass
                await item.mount(Label(date_str, classes="subtask-date"))
                
                if subtask.done:
                    item.add_class("done")
                
                if i == self.selected_index:
                    item.add_class("selected")
            
            self.scroll_to_selected()
    
    def scroll_to_selected(self) -> None:
        if self.selected_index >= 0:
            try:
                item = self.query_one(f"#subtask-{self.selected_index}", Horizontal)
                item.scroll_visible()
            except: pass
    
    def update_selection(self) -> None:
        for i in range(len(self.subtasks)):
            try:
                item = self.query_one(f"#subtask-{i}", Horizontal)
                item.set_class(i == self.selected_index, "selected")
            except: pass
        self.scroll_to_selected()
    
    def action_move_up(self) -> None:
        if self.subtasks and self.selected_index > 0:
            self.selected_index -= 1
            self.update_selection()
    
    def action_move_down(self) -> None:
        if self.subtasks and self.selected_index < len(self.subtasks) - 1:
            self.selected_index += 1
            self.update_selection()
    
    def action_add_subtask(self) -> None:
        def on_result(text: Optional[str]) -> None:
            if text:
                subtask = Subtask(id=self.next_subtask_id, text=text)
                self.next_subtask_id += 1
                self.subtasks.append(subtask)
                self.selected_index = len(self.subtasks) - 1
                self.call_later(self.refresh_subtasks_list)
        self.app.push_screen(InputModal("📋 Nueva Subtarea", placeholder="Descripción..."), on_result)
    
    def action_edit_subtask(self) -> None:
        if not self.subtasks or self.selected_index < 0:
            return
        subtask = self.subtasks[self.selected_index]
        
        next_comment_id = self.next_comment_id
        if subtask.comments:
            next_comment_id = max(c.id for c in subtask.comments) + 1
        
        def on_result(result: Optional[dict]) -> None:
            if result:
                subtask.text = result["text"]
                subtask.comments = result.get("comments", [])
                if subtask.comments:
                    self.next_comment_id = max(c.id for c in subtask.comments) + 1
                self.call_later(self.refresh_subtasks_list)
        
        self.app.push_screen(
            EditSubtaskModal(subtask.text, subtask.comments, next_comment_id),
            on_result
        )
    
    def action_delete_subtask(self) -> None:
        if not self.subtasks or self.selected_index < 0:
            return
        subtask = self.subtasks[self.selected_index]
        txt = subtask.text[:30] + "..." if len(subtask.text) > 30 else subtask.text
        def on_confirm(yes: bool) -> None:
            if yes:
                self.subtasks.pop(self.selected_index)
                if self.selected_index >= len(self.subtasks) and self.selected_index > 0:
                    self.selected_index -= 1
                if not self.subtasks:
                    self.selected_index = -1
                self.call_later(self.refresh_subtasks_list)
        self.app.push_screen(ConfirmModal(f"¿Eliminar subtarea '{txt}'?"), on_confirm)
    
    def action_toggle_subtask(self) -> None:
        if not self.subtasks or self.selected_index < 0:
            return
        subtask = self.subtasks[self.selected_index]
        subtask.done = not subtask.done
        self.call_later(self.refresh_subtasks_list)
    
    def action_set_date(self) -> None:
        if not self.subtasks or self.selected_index < 0:
            return
        subtask = self.subtasks[self.selected_index]
        def on_result(date_str: Optional[str]) -> None:
            if date_str is not None:
                subtask.due_date = date_str if date_str else None
                self.call_later(self.refresh_subtasks_list)
        self.app.push_screen(DatePickerModal(subtask.due_date), on_result)
    
    @on(Button.Pressed, "#add")
    def on_add(self) -> None:
        self.action_add_subtask()
    
    @on(Button.Pressed, "#edit")
    def on_edit(self) -> None:
        self.action_edit_subtask()
    
    @on(Button.Pressed, "#delete")
    def on_delete(self) -> None:
        self.action_delete_subtask()
    
    def action_close(self) -> None:
        self.dismiss(self.subtasks)

class UnscheduledItemsModal(ModalScreen[Optional[dict]]):
    DEFAULT_CSS = """
    UnscheduledItemsModal { align: center middle; }
    UnscheduledItemsModal > Container {
        width: 80; height: 32; border: thick $primary;
        background: $surface; padding: 1 2;
    }
    UnscheduledItemsModal .modal-title { text-align: center; text-style: bold; width: 100%; height: 1; margin-bottom: 1; }
    UnscheduledItemsModal .info-text { width: 100%; text-align: center; color: $text-muted; margin-bottom: 1; }
    UnscheduledItemsModal .section-header { 
        width: 100%; 
        text-align: left; 
        text-style: bold; 
        color: $accent;
        margin: 1 0;
        padding: 0 1;
    }
    UnscheduledItemsModal #items-list { width: 100%; height: 18; overflow-y: auto; border: solid $primary-background; padding: 1; }
    UnscheduledItemsModal .item {
        width: 100%; height: 3; padding: 0 1;
        border: solid $primary-background; margin-bottom: 1;
    }
    UnscheduledItemsModal .item:hover { background: $boost; }
    UnscheduledItemsModal .item.selected { border: solid $accent; background: $surface-lighten-1; }
    UnscheduledItemsModal .item.checked { color: $success; }
    UnscheduledItemsModal .empty-msg { width: 100%; text-align: center; color: $text-muted; text-style: italic; padding: 2; }
    UnscheduledItemsModal .hint { width: 100%; height: 1; text-align: center; color: $text-muted; margin: 1 0; }
    UnscheduledItemsModal .button-row { width: 100%; height: 3; align: center middle; }
    UnscheduledItemsModal Button { margin: 0 1; }
    """
    BINDINGS = [
        Binding("escape", "cancel", show=False),
        Binding("up", "move_up", show=False),
        Binding("down", "move_down", show=False),
        Binding("k", "move_up", show=False),
        Binding("j", "move_down", show=False),
        Binding("space", "toggle_item", show=False),
        Binding("enter", "save", show=False),
    ]
    
    def __init__(self, tasks: list[Task], all_groups: list[Group], **kwargs) -> None:
        super().__init__(**kwargs)
        self.all_groups = all_groups
        
        self.items = []
        
        for task in tasks:
            if task.due_date is None and not task.done:
                group_name = self._get_group_name(task.group_id)
                self.items.append(("task", task.id, None, task.text, group_name))
            
            for subtask in task.subtasks:
                if subtask.due_date is None and not subtask.done:
                    self.items.append(("subtask", task.id, subtask.id, subtask.text, task.text))
        
        self.selected_item_ids = []
        self.selected_index = 0 if self.items else -1
    
    def _get_group_name(self, group_id: Optional[int]) -> str:
        if group_id is None:
            return "Sin grupo"
        group = next((g for g in self.all_groups if g.id == group_id), None)
        return group.name if group else "Sin grupo"
    
    def compose(self) -> ComposeResult:
        with Container():
            yield Label("📅 Asignar fecha desde calendario", classes="modal-title")
            yield Label("Selecciona tareas y/o subtareas para asignarles la fecha del calendario", classes="info-text")
            yield Container(id="items-list")
            yield Label("↑↓ Navegar | Espacio: Marcar/Desmarcar | Enter: Asignar fecha | Esc: Cancelar", classes="hint")
            with Horizontal(classes="button-row"):
                yield Button("Asignar fecha", variant="primary", id="save")
                yield Button("Cancelar", variant="default", id="cancel")
    
    async def on_mount(self) -> None:
        await self.refresh_list()
    
    async def refresh_list(self) -> None:
        items_list = self.query_one("#items-list", Container)
        await items_list.remove_children()
        
        if not self.items:
            await items_list.mount(Label("No hay tareas ni subtareas sin fecha pendientes", classes="empty-msg"))
            self.selected_index = -1
            return
        
        tasks_items = [item for item in self.items if item[0] == "task"]
        subtasks_items = [item for item in self.items if item[0] == "subtask"]
        
        current_index = 0
        
        if tasks_items:
            await items_list.mount(Static("📋 Tareas:", classes="section-header"))
            for item_type, task_id, subtask_id, text, parent_text in tasks_items:
                checked = "☑" if (item_type, task_id, subtask_id) in self.selected_item_ids else "☐"
                text_display = text[:35] + "..." if len(text) > 35 else text
                padding = " " * max(1, 50 - len(text_display) - len(parent_text))
                display_text = f"{checked}  {text_display}{padding}📁 {parent_text}"
                
                item = Static(display_text, id=f"item-{current_index}", classes="item")
                await items_list.mount(item)
                if (item_type, task_id, subtask_id) in self.selected_item_ids:
                    item.add_class("checked")
                if current_index == self.selected_index:
                    item.add_class("selected")
                current_index += 1
        
        if subtasks_items:
            await items_list.mount(Static("📝 Subtareas:", classes="section-header"))
            for item_type, task_id, subtask_id, text, parent_text in subtasks_items:
                checked = "☑" if (item_type, task_id, subtask_id) in self.selected_item_ids else "☐"
                text_display = text[:35] + "..." if len(text) > 35 else text
                parent_display = parent_text[:20] + "..." if len(parent_text) > 20 else parent_text
                padding = " " * max(1, 40 - len(text_display) - len(parent_display))
                display_text = f"{checked}  ↳ {text_display}{padding}🔗 {parent_display}"
                
                item = Static(display_text, id=f"item-{current_index}", classes="item")
                await items_list.mount(item)
                if (item_type, task_id, subtask_id) in self.selected_item_ids:
                    item.add_class("checked")
                if current_index == self.selected_index:
                    item.add_class("selected")
                current_index += 1
        
        self.scroll_to_selected()
    
    def scroll_to_selected(self) -> None:
        if self.selected_index >= 0:
            try:
                item = self.query_one(f"#item-{self.selected_index}", Static)
                item.scroll_visible()
            except: pass
    
    def update_selection(self) -> None:
        for i in range(len(self.items)):
            try:
                item = self.query_one(f"#item-{i}", Static)
                item.set_class(i == self.selected_index, "selected")
            except: pass
        self.scroll_to_selected()
    
    def action_move_up(self) -> None:
        if self.items and self.selected_index > 0:
            self.selected_index -= 1
            self.update_selection()
    
    def action_move_down(self) -> None:
        if self.items and self.selected_index < len(self.items) - 1:
            self.selected_index += 1
            self.update_selection()
    
    def action_toggle_item(self) -> None:
        if not self.items or self.selected_index < 0:
            return
        item_type, task_id, subtask_id, text, parent_text = self.items[self.selected_index]
        item_id = (item_type, task_id, subtask_id)
        if item_id in self.selected_item_ids:
            self.selected_item_ids.remove(item_id)
        else:
            self.selected_item_ids.append(item_id)
        self.call_later(self.refresh_list)
    
    def action_save(self) -> None:
        if not self.selected_item_ids:
            self.dismiss(None)
            return
        
        task_ids = [task_id for item_type, task_id, subtask_id in self.selected_item_ids if item_type == "task"]
        subtask_selections = [(task_id, subtask_id) for item_type, task_id, subtask_id in self.selected_item_ids if item_type == "subtask"]
        
        self.dismiss({
            "task_ids": task_ids,
            "subtask_selections": subtask_selections
        })
    
    @on(Button.Pressed, "#save")
    def on_save_btn(self) -> None:
        self.action_save()
    
    @on(Button.Pressed, "#cancel")
    def on_cancel_btn(self) -> None:
        self.dismiss(None)
    
    def action_cancel(self) -> None:
        self.dismiss(None)
        
class DayItemsModal(ModalScreen[Optional[tuple]]):
    DEFAULT_CSS = """
    DayItemsModal { align: center middle; }
    DayItemsModal > Container {
        width: 80; height: 26; border: thick $primary;
        background: $surface; padding: 1 2;
    }
    DayItemsModal .modal-title { text-align: center; text-style: bold; width: 100%; margin-bottom: 1; }
    DayItemsModal .section-header { 
        width: 100%; 
        text-align: left; 
        text-style: bold; 
        color: $accent;
        margin: 1 0;
        padding: 0 1;
    }
    DayItemsModal #items-list { width: 100%; height: 1fr; overflow-y: auto; }
    DayItemsModal .item {
        width: 100%; height: 3; padding: 0 1;
        border: solid $primary-background; margin-bottom: 1;
        layout: horizontal;
    }
    DayItemsModal .item:hover { background: $boost; }
    DayItemsModal .item.selected { border: solid $accent; background: $surface-lighten-1; }
    DayItemsModal .item-main { width: 1fr; height: 1; }
    DayItemsModal .item-info { width: auto; height: 1; text-align: right; color: $text-muted; }
    DayItemsModal .hint { width: 100%; text-align: center; color: $text-muted; margin-top: 1; }
    DayItemsModal .empty-msg { width: 100%; text-align: center; color: $text-muted; text-style: italic; padding: 2; }
    """
    BINDINGS = [
        Binding("escape", "cancel", show=False),
        Binding("up", "move_up", show=False),
        Binding("down", "move_down", show=False),
        Binding("k", "move_up", show=False),
        Binding("j", "move_down", show=False),
        Binding("space", "go_to_item", show=False),
        Binding("enter", "go_to_item", show=False),
    ]
    
    def __init__(self, tasks: list[tuple], subtasks: list[tuple], date_str: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.tasks = tasks
        self.subtasks = subtasks
        self.date_str = date_str
        self.all_items = []
        
        for task, group_name in tasks:
            self.all_items.append(("task", task, group_name))
        for subtask, parent_task, group_name in subtasks:
            self.all_items.append(("subtask", (subtask, parent_task), group_name))
        
        self.selected_index = 0 if self.all_items else -1
    
    def compose(self) -> ComposeResult:
        with Container():
            yield Label(f"📅 {self.date_str}", classes="modal-title")
            yield Container(id="items-list")
            yield Label("↑↓ Navegar | Espacio/Enter: Ir a la tarea | Esc: Cerrar", classes="hint")
    
    async def on_mount(self) -> None:
        items_list = self.query_one("#items-list", Container)
        
        if not self.all_items:
            await items_list.mount(Label("No hay tareas ni subtareas para este día", classes="empty-msg"))
            return
        
        current_index = 0
        
        if self.tasks:
            await items_list.mount(Static("📋 Tareas:", classes="section-header"))
            for task, group_name in self.tasks:
                checkbox = "☑" if task.done else "☐"
                item = Horizontal(id=f"item-{current_index}", classes="item")
                await items_list.mount(item)
                
                await item.mount(Label(f"{checkbox} {task.text}", classes="item-main"))
                await item.mount(Label(f"📁 {group_name}", classes="item-info"))
                
                if current_index == self.selected_index:
                    item.add_class("selected")
                current_index += 1
        
        if self.subtasks:
            await items_list.mount(Static("📝 Subtareas:", classes="section-header"))
            for subtask, parent_task, group_name in self.subtasks:
                checkbox = "☑" if subtask.done else "☐"
                parent_text = parent_task.text[:25] + "..." if len(parent_task.text) > 25 else parent_task.text
                item = Horizontal(id=f"item-{current_index}", classes="item")
                await items_list.mount(item)
                
                await item.mount(Label(f"{checkbox} ↳ {subtask.text}", classes="item-main"))
                await item.mount(Label(f"🔗 {parent_text}", classes="item-info"))
                
                if current_index == self.selected_index:
                    item.add_class("selected")
                current_index += 1
    
    def update_selection(self) -> None:
        for i in range(len(self.all_items)):
            try:
                item = self.query_one(f"#item-{i}", Horizontal)
                item.set_class(i == self.selected_index, "selected")
            except: pass
    
    def action_move_up(self) -> None:
        if self.all_items and self.selected_index > 0:
            self.selected_index -= 1
            self.update_selection()
    
    def action_move_down(self) -> None:
        if self.all_items and self.selected_index < len(self.all_items) - 1:
            self.selected_index += 1
            self.update_selection()
    
    def action_go_to_item(self) -> None:
        if self.all_items and self.selected_index >= 0:
            item_type, item_obj, info = self.all_items[self.selected_index]
            if item_type == "task":
                self.dismiss(("task", item_obj))
            else:
                subtask, parent_task = item_obj
                self.dismiss(("subtask", parent_task))
    
    def action_cancel(self) -> None:
        self.dismiss(None)

class SubtaskReminderModal(ModalScreen[bool]):
    DEFAULT_CSS = """
    SubtaskReminderModal { align: center middle; }
    SubtaskReminderModal > Container {
        width: 50; height: auto; max-height: 20; border: thick $warning;
        background: $surface; padding: 1 2;
    }
    SubtaskReminderModal .modal-title { 
        text-align: center; text-style: bold; 
        width: 100%; height: auto;
        color: $warning;
        margin-bottom: 1;
    }
    SubtaskReminderModal .subtask-info {
        width: 100%; height: auto;
        padding: 1;
        background: $surface-lighten-1;
        border: solid $primary-background;
        margin-bottom: 1;
    }
    SubtaskReminderModal .subtask-text { 
        width: 100%; height: auto;
        text-align: center;
        margin: 0 0 1 0;
    }
    SubtaskReminderModal .parent-info {
        width: 100%; height: auto;
        text-align: center;
        color: $text-muted;
        margin-bottom: 0;
    }
    SubtaskReminderModal .button-row { 
        width: 100%; height: auto; 
        align: center middle;
        margin-top: 1;
    }
    SubtaskReminderModal Button { margin: 0 1; }
    """
    
    BINDINGS = [
        Binding("escape", "close", show=False),
        Binding("enter", "close", show=False),
        Binding("space", "close", show=False),
    ]
    
    def __init__(self, subtask: Subtask, parent_text: str, group_name: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.subtask_data = subtask
        self.parent_text = parent_text
        self.group_name = group_name
    
    def compose(self) -> ComposeResult:
        with Container():
            yield Label("⏰ Recordatorio de Subtarea", classes="modal-title")
            with Container(classes="subtask-info"):
                yield Label("La siguiente subtarea vence HOY:", classes="parent-info")
                yield Label(f"↳ {self.subtask_data.text}", classes="subtask-text")
                yield Label(f"🔗 Tarea: {self.parent_text}", classes="parent-info")
                yield Label(f"📁 Grupo: {self.group_name}", classes="parent-info")
            with Horizontal(classes="button-row"):
                yield Button("Entendido", variant="primary", id="ok")
    
    @on(Button.Pressed, "#ok")
    def on_ok(self) -> None:
        self.dismiss(True)
    
    def action_close(self) -> None:
        self.dismiss(True)
    
    def on_key(self, event) -> None:
        if event.key not in ["escape", "enter", "space"]:
            event.prevent_default()
            event.stop()

class ImageViewerModal(ModalScreen[bool]):
    DEFAULT_CSS = """
    ImageViewerModal { align: center middle; }
    ImageViewerModal > Container {
        width: 95%; 
        height: 95%; 
        border: thick $primary;
        background: $surface; 
        padding: 1;
    }
    ImageViewerModal .modal-title { 
        text-align: center; 
        text-style: bold; 
        width: 100%; 
        margin-bottom: 1; 
    }
    ImageViewerModal #image-container { 
        width: 100%; 
        height: 1fr; 
        overflow: auto;
        border: solid $primary-background;
        padding: 1;
        align: center middle;
        content-align: center middle;
    }
    ImageViewerModal .info-text {
        width: 100%;
        text-align: center;
        color: $text-muted;
        margin-top: 1;
    }
    ImageViewerModal .button-row { 
        width: 100%; 
        height: auto; 
        align: center middle; 
        margin-top: 1;
    }
    ImageViewerModal Button { margin: 0 1; }
    """
    
    BINDINGS = [
        Binding("escape", "close", show=False),
        Binding("q", "close", show=False),
        Binding("o", "open_external", "Abrir externa", show=True),
    ]
    
    def __init__(self, image_path: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.image_path = image_path
    
    def compose(self) -> ComposeResult:
        with Container():
            yield Label(f"📷 {Path(self.image_path).name}", classes="modal-title")
            yield Static(id="image-container")
            yield Static("", id="info-text", classes="info-text")
            with Horizontal(classes="button-row"):
                yield Button("📂 Abrir externa", variant="default", id="open")
                yield Button("Cerrar", variant="primary", id="close")
    
    def on_mount(self) -> None:
        image_static = self.query_one("#image-container", Static)
        info_static = self.query_one("#info-text", Static)
        
        term = os.environ.get('TERM', '').lower()
        term_program = os.environ.get('TERM_PROGRAM', '').lower()
        
        if 'kitty' in term or term_program == 'kitty':
            if self._try_kitty_protocol(image_static):
                info_static.update("✨ Kitty Protocol (calidad perfecta)")
                return
        
        if term_program == 'iterm.app':
            if self._try_iterm2_protocol(image_static):
                info_static.update("✨ iTerm2 Protocol (calidad perfecta)")
                return
        
        if self._terminal_supports_sixel():
            if self._try_sixel(image_static):
                info_static.update("✨ Sixel Protocol (alta calidad)")
                return
        
        if self._try_chafa(image_static):
            info_static.update("✨ Chafa (alta calidad)")
            return
        
        if self._try_rich_pixels(image_static):
            info_static.update("🎨 Vista previa básica (Presiona 'o' para alta calidad)")
            return
        
        image_static.update(
            f"📷 {Path(self.image_path).name}\n\n"
            f"Presiona 'o' o el botón 'Abrir externa'\n"
            f"para ver la imagen\n\n"
            f"Ruta: {self.image_path}"
        )
        info_static.update("ℹ️ Vista previa no disponible")
    
    def _terminal_supports_sixel(self) -> bool:
        term = os.environ.get('TERM', '').lower()
        return any(x in term for x in ['mlterm', 'mintty']) or \
               ('xterm' in term and shutil.which('img2sixel'))
    
    def _try_kitty_protocol(self, widget: Static) -> bool:
        try:
            from base64 import b64encode
            
            img = Image.open(self.image_path)
            max_size = (800, 600)
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            import io
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            img_data = buffer.getvalue()
            
            b64_data = b64encode(img_data).decode('ascii')
            kitty_cmd = f"\033_Ga=T,f=100;{b64_data}\033\\"
            
            from rich.text import Text
            widget.update(Text.from_ansi(kitty_cmd))
            return True
            
        except Exception:
            return False
    
    def _try_iterm2_protocol(self, widget: Static) -> bool:
        try:
            from base64 import b64encode
            
            with open(self.image_path, 'rb') as f:
                img_data = f.read()
            
            b64_data = b64encode(img_data).decode('ascii')
            iterm_cmd = f"\033]1337;File=inline=1:{b64_data}\007"
            
            from rich.text import Text
            widget.update(Text.from_ansi(iterm_cmd))
            return True
            
        except Exception:
            return False
    
    def _try_sixel(self, widget: Static) -> bool:
        if not shutil.which('img2sixel'):
            return False
        
        try:
            terminal_size = shutil.get_terminal_size()
            width = min(800, (terminal_size.columns - 10) * 8)
            
            result = subprocess.run(
                ['img2sixel', '-w', str(width), self.image_path],
                capture_output=True,
                timeout=10
            )
            
            if result.returncode == 0:
                from rich.text import Text
                widget.update(Text.from_ansi(result.stdout.decode('utf-8', errors='ignore')))
                return True
                
        except Exception:
            pass
        
        return False
    
    def _try_chafa(self, widget: Static) -> bool:
        if not shutil.which('chafa'):
            return False
        
        try:
            terminal_size = shutil.get_terminal_size()
            width = min(100, terminal_size.columns - 10)
            height = min(50, terminal_size.lines - 15)
            
            result = subprocess.run(
                [
                    'chafa',
                    '--size', f'{width}x{height}',
                    '--format', 'symbols',
                    '--symbols', 'all',
                    '--color-space', 'rgb',
                    '--dither', 'none',
                    '--optimize', '9',
                    self.image_path
                ],
                capture_output=True,
                text=True,
                timeout=10,
                encoding='utf-8'
            )
            
            if result.returncode == 0 and result.stdout:
                from rich.text import Text
                widget.update(Text.from_ansi(result.stdout))
                return True
        except Exception:
            pass
        
        return False
    
    def _try_rich_pixels(self, widget: Static) -> bool:
        try:
            terminal_size = shutil.get_terminal_size()

            target_width = min(60, terminal_size.columns - 20)
            target_height = min(30, terminal_size.lines - 10)
            
            pixels = Pixels.from_image_path(
                self.image_path,
                resize=(target_width, target_height)
            )
            
            widget.update(pixels)
            return True
            
        except Exception as e:
            return False
    
    def action_open_external(self) -> None:
        self._open_external()
    
    @on(Button.Pressed, "#open")
    def on_open_btn(self) -> None:
        self._open_external()
    
    def _open_external(self) -> None:
        system = platform.system()
        
        try:
            if system == 'Windows':
                subprocess.Popen(['start', '', self.image_path], shell=True)
                self.app.notify("📂 Abriendo imagen...", severity="information")
                
            elif system == 'Darwin':
                try:
                    subprocess.Popen(['open', self.image_path], 
                                   stderr=subprocess.PIPE)
                    self.app.notify("📂 Abriendo imagen...", severity="information")
                except:
                    self._open_with_ranger()
                
            elif system == 'Linux':
                if self._try_gui_viewer():
                    self.app.notify("📂 Abriendo imagen...", severity="information")
                else:
                    self._open_with_ranger()
            
        except Exception as e:
            self.app.notify(f"❌ Error: {str(e)}", severity="error")
            self._open_with_ranger()
    
    def _try_gui_viewer(self) -> bool:
        viewers = ['xdg-open', 'eog', 'feh', 'gwenview', 'display', 'gthumb', 'ristretto']
        
        for viewer in viewers:
            if shutil.which(viewer):
                try:
                    subprocess.Popen(
                        [viewer, self.image_path],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                    return True
                except:
                    continue
        
        return False
    
    def _open_with_ranger(self) -> None:
        if shutil.which('ranger'):
            try:
                self.app.notify("📁 Abriendo con Ranger...", severity="information")
                
                self.app.exit()
                
                subprocess.run(['ranger', '--selectfile', self.image_path])
                
            except Exception as e:
                print(f"Error al abrir Ranger: {e}")
        else:
            self.app.notify(
                "⚠️ No hay visor gráfico ni Ranger disponible",
                severity="warning",
                timeout=3
            )
            self.app.notify(
                f"📁 Ruta: {self.image_path}",
                severity="information",
                timeout=10
            )
    
    @on(Button.Pressed, "#close")
    def on_close_btn(self) -> None:
        self.dismiss(True)
    
    def action_close(self) -> None:
        self.dismiss(True)

class EditSubtaskModal(ModalScreen[Optional[dict]]):
    DEFAULT_CSS = """
    EditSubtaskModal { align: center middle; }
    EditSubtaskModal > Container {
        width: 78; height: auto; max-height: 90%; border: thick $primary;
        background: $surface; padding: 1 2; overflow-y: auto;
    }
    EditSubtaskModal .modal-title { text-align: center; text-style: bold; width: 100%; margin-bottom: 1; }
    EditSubtaskModal .section-label { margin-top: 1; color: $text-muted; }
    EditSubtaskModal Input { width: 100%; margin-bottom: 1; }
    EditSubtaskModal .comments-row { width: 100%; height: auto; align: left middle; margin-bottom: 1; }
    EditSubtaskModal .comments-display { width: 1fr; padding: 0 1; }
    EditSubtaskModal .button-row { width: 100%; height: auto; align: center middle; margin-top: 1; }
    EditSubtaskModal Button { margin: 0 1; }
    """
    BINDINGS = [Binding("escape", "cancel", show=False)]
    
    def __init__(self, subtask_text: str, comments: list[Comment] = None, 
                 next_comment_id: int = 1, **kwargs) -> None:
        super().__init__(**kwargs)
        self.subtask_text = subtask_text
        self.comments = comments or []
        self.next_comment_id = next_comment_id
    
    def compose(self) -> ComposeResult:
        with Container():
            yield Label("✏️ Editar Subtarea", classes="modal-title")
            yield Label("Texto:", classes="section-label")
            yield Input(value=self.subtask_text, id="subtask-input")
            yield Label("Comentarios:", classes="section-label")
            with Horizontal(classes="comments-row"):
                yield Label(self._format_comments(), id="comments-display", classes="comments-display")
                yield Button("💬 Gestionar", id="manage-comments")
            with Horizontal(classes="button-row"):
                yield Button("Guardar", variant="primary", id="save")
                yield Button("Cancelar", variant="default", id="cancel")
    
    def _format_comments(self) -> str:
        count = len(self.comments)
        if count == 0:
            return "Sin comentarios"
        elif count == 1:
            return "💬 1 comentario"
        else:
            return f"💬 {count} comentarios"
    
    def on_mount(self) -> None:
        self.query_one("#subtask-input", Input).focus()
    
    @on(Button.Pressed, "#manage-comments")
    def on_manage_comments(self) -> None:
        def on_result(updated_comments: list[Comment]) -> None:
            self.comments = updated_comments
            if self.comments:
                self.next_comment_id = max(c.id for c in self.comments) + 1
            self.query_one("#comments-display", Label).update(self._format_comments())
        self.app.push_screen(CommentsModal(self.comments, self.next_comment_id), on_result)
    
    @on(Button.Pressed, "#save")
    def on_save(self) -> None:
        text = self.query_one("#subtask-input", Input).value.strip()
        if not text:
            self.app.notify("El texto de la subtarea no puede estar vacío", severity="warning")
            return
        
        self.dismiss({
            "text": text,
            "comments": self.comments
        })
    
    @on(Button.Pressed, "#cancel")
    def on_cancel(self) -> None:
        self.dismiss(None)
    
    @on(Input.Submitted)
    def on_submit(self) -> None:
        self.on_save()
    
    def action_cancel(self) -> None:
        self.dismiss(None)

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
    TaskWidget .priority { width: 3; height: 1; }
    TaskWidget .urgent-indicator {
        width: 3; 
        height: 1; 
        color: $warning;
        text-style: bold;
    }
    TaskWidget .task-text { width: 1fr; height: 1; }
    TaskWidget .tag { background: #90EE90; color: #000000; }
    TaskWidget .tag-separator { width: 1; }
    TaskWidget .task-subtasks { width: 6; height: 1; text-align: right; color: $accent; }
    TaskWidget .task-links { width: 3; height: 1; text-align: right; color: $accent; }
    TaskWidget .task-images { width: 3; height: 1; text-align: right; color: $primary; }
    TaskWidget .task-comments { width: 5; height: 1; text-align: right; color: $primary; }
    TaskWidget .task-group { width: 20; height: 1; text-align: right; color: $text-muted; }
    TaskWidget .task-date { width: 8; height: 1; text-align: right; color: $warning; }
    TaskWidget .task-time { width: 12; height: 1; text-align: right; color: $text-muted; }
    TaskWidget.done .task-text { text-style: strike; color: $text-muted; }
    TaskWidget.done .checkbox { color: $success; }
    TaskWidget.done .task-date { color: $text-muted; }
    TaskWidget.done .task-comments { color: $text-muted; }
    TaskWidget.done .task-links { color: $text-muted; }
    TaskWidget.done .task-images { color: $text-muted; }
    TaskWidget.done .task-subtasks { color: $text-muted; }
    TaskWidget.done .task-group { color: $text-muted; }
    TaskWidget.done .priority { color: $text-muted; }
    """
    
    def __init__(self, task_data: Task, all_tags: list[Tag] = None, all_groups: list[Group] = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.task_data = task_data
        self.all_tags = all_tags or []
        self.all_groups = all_groups or []
        self._selected = False
    
    def compose(self) -> ComposeResult:
        checkbox = "☑" if self.task_data.done else "☐"
        yield Label(checkbox, classes="checkbox")
        
        priority_icons = {
            0: "  ",
            1: "[green]■[/green]",
            2: "[yellow]■[/yellow]",
            3: "[red]■[/red]"
        }
        priority_icon = priority_icons.get(self.task_data.priority, "  ")
        yield Label(priority_icon, classes="priority")
        
        urgent_icon = ""
        if not self.task_data.done and self.task_data.due_date:
            try:
                due_date = datetime.strptime(self.task_data.due_date, "%Y-%m-%d").date()
                if due_date == date.today():
                    urgent_icon = "⚠️ "
            except: pass
        yield Label(urgent_icon, classes="urgent-indicator")
        
        yield Label(self.task_data.text, classes="task-text")
        
        if self.task_data.tags:
            for tag_id in self.task_data.tags:
                tag = next((t for t in self.all_tags if t.id == tag_id), None)
                if tag:
                    tag_name = tag.name[:10] if len(tag.name) > 10 else tag.name
                    yield Label(f" {tag_name} ", classes="tag")
                    yield Label(" ", classes="tag-separator")
        
        if self.task_data.subtasks:
            done_count = sum(1 for s in self.task_data.subtasks if s.done)
            total_count = len(self.task_data.subtasks)
            subtasks_str = f"📋{done_count}/{total_count}"
        else:
            subtasks_str = ""
        yield Label(subtasks_str, classes="task-subtasks")
        
        links_count = sum(1 for c in self.task_data.comments if c.url)
        links_str = f"🔗{links_count}" if links_count > 0 else ""
        yield Label(links_str, classes="task-links")
        
        images_count = sum(1 for c in self.task_data.comments if c.image_path)
        images_str = f"📷{images_count}" if images_count > 0 else ""
        yield Label(images_str, classes="task-images")
        
        comments_str = f"💬{len(self.task_data.comments)}" if self.task_data.comments else ""
        yield Label(comments_str, classes="task-comments")
        
        group_str = self._format_group_name()
        yield Label(group_str, classes="task-group")
        
        date_str = ""
        if self.task_data.due_date:
            try:
                d = datetime.strptime(self.task_data.due_date, "%Y-%m-%d")
                date_str = f"📅 {d.day:02d}/{d.month:02d}"
            except: pass
        yield Label(date_str, classes="task-date")
        yield Label(self.task_data.created_at, classes="task-time")
    
    def _format_group_name(self) -> str:
        if self.task_data.group_id is None:
            return "Grupo: Sin grupo "
        
        group = next((g for g in self.all_groups if g.id == self.task_data.group_id), None)
        if group:
            group_name = group.name[:12] if len(group.name) > 12 else group.name
            return f"Grupo: {group_name} "
        return "Grupo: Sin grupo "
    
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

class PriorityPickerModal(ModalScreen[Optional[int]]):
    DEFAULT_CSS = """
    PriorityPickerModal { align: center middle; }
    PriorityPickerModal > Container {
        width: 40; height: auto; border: thick $primary;
        background: $surface; padding: 1 2;
    }
    PriorityPickerModal .modal-title { text-align: center; text-style: bold; width: 100%; height: 1; margin-bottom: 1; }
    PriorityPickerModal #priority-list { width: 100%; height: auto; padding: 1; }
    PriorityPickerModal .priority-item {
        width: 100%; height: 3; padding: 0 1;
        border: solid $primary-background; margin-bottom: 1;
        content-align: center middle;
    }
    PriorityPickerModal .priority-item:hover { background: $boost; }
    PriorityPickerModal .priority-item.selected { border: solid $accent; background: $surface-lighten-1; }
    PriorityPickerModal .hint { width: 100%; height: 1; text-align: center; color: $text-muted; margin: 1 0; }
    PriorityPickerModal .button-row { width: 100%; height: 3; align: center middle; }
    PriorityPickerModal Button { margin: 0 1; }
    """
    BINDINGS = [
        Binding("escape", "cancel", show=False),
        Binding("up", "move_up", show=False),
        Binding("down", "move_down", show=False),
        Binding("k", "move_up", show=False),
        Binding("j", "move_down", show=False),
        Binding("enter", "select", show=False),
    ]
    
    def __init__(self, current_priority: int = 0, **kwargs) -> None:
        super().__init__(**kwargs)
        self.current_priority = current_priority
        self.selected_index = current_priority
    
    def compose(self) -> ComposeResult:
        with Container():
            yield Label("⭐ Seleccionar Prioridad", classes="modal-title")
            yield Container(id="priority-list")
            yield Label("↑↓ Navegar | Enter: Seleccionar | Esc: Cancelar", classes="hint")
            with Horizontal(classes="button-row"):
                yield Button("Seleccionar", variant="primary", id="select")
                yield Button("Cancelar", variant="default", id="cancel")
    
    async def on_mount(self) -> None:
        await self.refresh_list()
    
    async def refresh_list(self) -> None:
        priority_list = self.query_one("#priority-list", Container)
        await priority_list.remove_children()
        
        priorities = [
            ("   Sin prioridad", 0),
            ("[green]■[/green]  Baja", 1),
            ("[yellow]■[/yellow]  Media", 2),
            ("[red]■[/red]  Alta", 3)
        ]
        
        for i, (text, value) in enumerate(priorities):
            item = Static(text, id=f"priority-{i}", classes="priority-item")
            await priority_list.mount(item)
            if i == self.selected_index:
                item.add_class("selected")
    
    def scroll_to_selected(self) -> None:
        if self.selected_index >= 0:
            try:
                item = self.query_one(f"#priority-{self.selected_index}", Static)
                item.scroll_visible()
            except: pass
    
    def update_selection(self) -> None:
        for i in range(4):
            try:
                item = self.query_one(f"#priority-{i}", Static)
                item.set_class(i == self.selected_index, "selected")
            except: pass
        self.scroll_to_selected()
    
    def action_move_up(self) -> None:
        if self.selected_index > 0:
            self.selected_index -= 1
            self.update_selection()
    
    def action_move_down(self) -> None:
        if self.selected_index < 3:
            self.selected_index += 1
            self.update_selection()
    
    def action_select(self) -> None:
        self.dismiss(self.selected_index)
    
    @on(Button.Pressed, "#select")
    def on_select_btn(self) -> None:
        self.action_select()
    
    @on(Button.Pressed, "#cancel")
    def on_cancel_btn(self) -> None:
        self.dismiss(None)
    
    def action_cancel(self) -> None:
        self.dismiss(None)

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

class ReminderModal(ModalScreen[bool]):
    DEFAULT_CSS = """
    ReminderModal { align: center middle; }
    ReminderModal > Container {
        width: 50; height: auto; max-height: 20; border: thick $warning;
        background: $surface; padding: 1 2;
    }
    ReminderModal .modal-title { 
        text-align: center; text-style: bold; 
        width: 100%; height: auto;
        color: $warning;
        margin-bottom: 1;
    }
    ReminderModal .task-info {
        width: 100%; height: auto;
        padding: 1;
        background: $surface-lighten-1;
        border: solid $primary-background;
        margin-bottom: 1;
    }
    ReminderModal .task-text { 
        width: 100%; height: auto;
        text-align: center;
        margin: 0 0 1 0;
    }
    ReminderModal .group-info {
        width: 100%; height: auto;
        text-align: center;
        color: $text-muted;
        margin-bottom: 0;
    }
    ReminderModal .button-row { 
        width: 100%; height: auto; 
        align: center middle;
        margin-top: 1;
    }
    ReminderModal Button { margin: 0 1; }
    """
    
    BINDINGS = [
        Binding("escape", "close", show=False),
        Binding("enter", "close", show=False),
        Binding("space", "close", show=False),
    ]
    
    def __init__(self, task: Task, group_name: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.task_data = task
        self.group_name = group_name
    
    def compose(self) -> ComposeResult:
        with Container():
            yield Label("⏰ Recordatorio de Tarea", classes="modal-title")
            with Container(classes="task-info"):
                yield Label("La siguiente tarea vence HOY:", classes="group-info")
                yield Label(self.task_data.text, classes="task-text")
                yield Label(f"📁 Grupo: {self.group_name}", classes="group-info")
            with Horizontal(classes="button-row"):
                yield Button("Entendido", variant="primary", id="ok")
    
    @on(Button.Pressed, "#ok")
    def on_ok(self) -> None:
        self.dismiss(True)
    
    def action_close(self) -> None:
        self.dismiss(True)
    
    def on_key(self, event) -> None:
        if event.key not in ["escape", "enter", "space"]:
            event.prevent_default()
            event.stop()

class GroupPickerModal(ModalScreen[Optional[int]]):
    DEFAULT_CSS = """
    GroupPickerModal { align: center middle; }
    GroupPickerModal > Container {
        width: 50; height: auto; max-height: 20; border: thick $primary;
        background: $surface; padding: 1 2;
    }
    GroupPickerModal .modal-title { text-align: center; text-style: bold; width: 100%; margin-bottom: 1; }
    GroupPickerModal #groups-list { width: 100%; height: auto; max-height: 12; overflow-y: auto; }
    GroupPickerModal .group-item {
        width: 100%; height: 3; padding: 0 1;
        border: solid $primary-background; margin-bottom: 1;
        content-align: left middle;
    }
    GroupPickerModal .group-item:hover { background: $boost; }
    GroupPickerModal .group-item.selected { border: solid $accent; background: $surface-lighten-1; }
    GroupPickerModal .hint { width: 100%; text-align: center; color: $text-muted; margin-top: 1; }
    """
    BINDINGS = [
        Binding("escape", "cancel", show=False),
        Binding("up", "move_up", show=False),
        Binding("down", "move_down", show=False),
        Binding("k", "move_up", show=False),
        Binding("j", "move_down", show=False),
        Binding("enter", "select_group", show=False),
    ]
    
    def __init__(self, groups: list[Group], current_group_id: Optional[int] = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.groups = groups
        self.current_group_id = current_group_id
        self.options: list[Optional[int]] = [None] + [g.id for g in groups]
        if current_group_id is None:
            self.selected_index = 0
        else:
            try:
                self.selected_index = self.options.index(current_group_id)
            except ValueError:
                self.selected_index = 0
    
    def compose(self) -> ComposeResult:
        with Container():
            yield Label("📁 Seleccionar Grupo", classes="modal-title")
            yield Container(id="groups-list")
            yield Label("↑↓ Navegar | Enter: Seleccionar | Esc: Cancelar", classes="hint")
    
    async def on_mount(self) -> None:
        groups_list = self.query_one("#groups-list", Container)
        
        item = Static("📋 Sin grupo", id="group-item-0", classes="group-item")
        await groups_list.mount(item)
        if self.selected_index == 0:
            item.add_class("selected")
        
        for i, group in enumerate(self.groups):
            item = Static(f"📁 {group.name}", id=f"group-item-{i+1}", classes="group-item")
            await groups_list.mount(item)
            if self.selected_index == i + 1:
                item.add_class("selected")
    
    def update_selection(self) -> None:
        for i in range(len(self.options)):
            try:
                item = self.query_one(f"#group-item-{i}", Static)
                item.set_class(i == self.selected_index, "selected")
            except: pass
    
    def action_move_up(self) -> None:
        if self.selected_index > 0:
            self.selected_index -= 1
            self.update_selection()
    
    def action_move_down(self) -> None:
        if self.selected_index < len(self.options) - 1:
            self.selected_index += 1
            self.update_selection()
    
    def action_select_group(self) -> None:
        self.dismiss(self.options[self.selected_index])
    
    def action_cancel(self) -> None:
        self.dismiss(self.current_group_id)

class CommentEditModal(ModalScreen[Optional[dict]]):
    DEFAULT_CSS = """
    CommentEditModal { align: center middle; }
    CommentEditModal > Container {
        width: 78; height: 30; border: thick $primary;
        background: $surface; padding: 1 2;
    }
    CommentEditModal .modal-title { text-align: center; text-style: bold; width: 100%; margin-bottom: 1; }
    CommentEditModal .section-label { margin-top: 1; margin-bottom: 0; color: $text-muted; }
    CommentEditModal Input { width: 100%; margin-bottom: 1; }
    CommentEditModal .image-info { 
        width: 100%; 
        padding: 1; 
        background: $surface-lighten-1;
        border: solid $primary-background;
        margin-bottom: 1;
        color: $success;
    }
    CommentEditModal .button-row { width: 100%; height: auto; align: center middle; margin-top: 1; }
    CommentEditModal .image-button-row { 
        width: 100%; 
        height: auto; 
        align: left middle; 
        margin-bottom: 1;
        layout: horizontal;
    }
    CommentEditModal Button { margin: 0 1; }
    """
    BINDINGS = [Binding("escape", "cancel", show=False)]
    
    def __init__(self, title: str = "💬 Comentario", initial_text: str = "", 
                 initial_url: str = "", initial_image: str = "", **kwargs) -> None:
        super().__init__(**kwargs)
        self.title_text = title
        self.initial_text = initial_text
        self.initial_url = initial_url or ""
        self.current_image_path = initial_image or ""
        self.images_dir = Path.home() / "todo" / "images"
        self.images_dir.mkdir(exist_ok=True, parents=True)
    
    def compose(self) -> ComposeResult:
        with Container():
            yield Label(self.title_text, classes="modal-title")
            yield Label("Texto del comentario:", classes="section-label")
            yield Input(value=self.initial_text, placeholder="Escribe el comentario...", id="text-input")
            yield Label("Enlace (opcional):", classes="section-label")
            yield Input(value=self.initial_url, placeholder="https://ejemplo.com", id="url-input")
            yield Label("Imagen (opcional):", classes="section-label")
            yield Horizontal(id="image-button-row", classes="image-button-row")
            yield Container(id="image-info-container")
            with Horizontal(classes="button-row"):
                yield Button("Guardar", variant="primary", id="save")
                yield Button("Cancelar", variant="default", id="cancel")
    
    async def on_mount(self) -> None:
        self.query_one("#text-input", Input).focus()
        await self._update_image_buttons()
    
    async def _update_image_buttons(self) -> None:
        """Actualiza los botones de imagen según si hay imagen o no"""
        button_row = self.query_one("#image-button-row", Horizontal)
        await button_row.remove_children()
        
        await button_row.mount(Button("📋 Pegar", variant="default", id="paste-image"))
        await button_row.mount(Button("📁 Examinar", variant="default", id="browse-image"))
        await button_row.mount(Button("✏️ Ruta", variant="default", id="path-image"))
        
        if self.current_image_path:
            await button_row.mount(Button("🗑️ Eliminar", variant="error", id="remove-image"))
        
        info_container = self.query_one("#image-info-container", Container)
        await info_container.remove_children()
        
        if self.current_image_path:
            await info_container.mount(
                Label(f"📷 Imagen: {Path(self.current_image_path).name}", 
                      id="image-info", classes="image-info")
            )
    
    def _save_image_from_clipboard(self) -> Optional[str]:
        """Intenta guardar una imagen desde el portapapeles"""
        try:
            from PIL import ImageGrab
            image = ImageGrab.grabclipboard()
            if image and isinstance(image, Image.Image):
                filename = f"img_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                filepath = self.images_dir / filename
                image.save(filepath)
                return str(filepath)
            else:
                try:
                    clipboard_text = pyperclip.paste()
                    if clipboard_text and Path(clipboard_text).exists():
                        if Path(clipboard_text).suffix.lower() in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp']:
                            return self._copy_image_to_storage(clipboard_text)
                except:
                    pass
            return None
        except Exception as e:
            print(f"Error al pegar imagen: {e}")
            return None
    
    def _copy_image_to_storage(self, source_path: str) -> Optional[str]:
        """Copia una imagen al directorio de almacenamiento"""
        try:
            source = Path(source_path)
            if not source.exists():
                return None
            
            if source.suffix.lower() not in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp']:
                return None
            
            filename = f"img_{datetime.now().strftime('%Y%m%d_%H%M%S')}{source.suffix}"
            filepath = self.images_dir / filename
            shutil.copy2(source, filepath)
            return str(filepath)
        except Exception as e:
            print(f"Error al copiar imagen: {e}")
            return None
    
    def _browse_image(self) -> Optional[str]:
        """Abre el explorador de archivos para seleccionar una imagen"""
        try:
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            
            filepath = filedialog.askopenfilename(
                title="Seleccionar imagen",
                filetypes=[
                    ("Imágenes", "*.png *.jpg *.jpeg *.gif *.bmp *.webp"),
                    ("Todos los archivos", "*.*")
                ]
            )
            root.destroy()
            
            if filepath:
                return self._copy_image_to_storage(filepath)
            return None
        except Exception as e:
            print(f"Error al abrir explorador: {e}")
            return None
    
    @on(Button.Pressed, "#paste-image")
    async def on_paste_image(self) -> None:
        image_path = self._save_image_from_clipboard()
        if image_path:
            self.current_image_path = image_path
            await self._update_image_buttons()
            self.app.notify("📷 Imagen pegada correctamente", severity="information")
        else:
            self.app.notify("⚠️ No hay imagen en el portapapeles", severity="warning")
    
    @on(Button.Pressed, "#browse-image")
    async def on_browse_image(self) -> None:
        image_path = self._browse_image()
        if image_path:
            self.current_image_path = image_path
            await self._update_image_buttons()
            self.app.notify("📷 Imagen seleccionada", severity="information")
    
    @on(Button.Pressed, "#path-image")
    def on_path_image(self) -> None:
        async def on_result(path: Optional[str]) -> None:
            if path:
                if Path(path).exists():
                    image_path = self._copy_image_to_storage(path)
                    if image_path:
                        self.current_image_path = image_path
                        await self._update_image_buttons()
                        self.app.notify("📷 Imagen añadida", severity="information")
                    else:
                        self.app.notify("❌ Formato de imagen no válido", severity="error")
                else:
                    self.app.notify("❌ Ruta no existe", severity="error")
        self.app.push_screen(
            InputModal("📷 Ruta de la imagen", placeholder="/ruta/a/imagen.png"),
            on_result
        )
    
    @on(Button.Pressed, "#remove-image")
    async def on_remove_image(self) -> None:
        self.current_image_path = ""
        await self._update_image_buttons()
        self.app.notify("🗑️ Imagen eliminada", severity="information")
    
    @on(Button.Pressed, "#save")
    def on_save(self) -> None:
        text = self.query_one("#text-input", Input).value.strip()
        url = self.query_one("#url-input", Input).value.strip()
        
        if not text:
            self.app.notify("El texto del comentario no puede estar vacío", severity="warning")
            return
        
        if url and not (url.startswith("http://") or url.startswith("https://")):
            self.app.notify("La URL debe comenzar con http:// o https://", severity="warning")
            return
        
        self.dismiss({
            "text": text,
            "url": url if url else None,
            "image_path": self.current_image_path if self.current_image_path else None
        })
    
    @on(Button.Pressed, "#cancel")
    def on_cancel(self) -> None:
        self.dismiss(None)
    
    @on(Input.Submitted)
    def on_submit(self, event: Input.Submitted) -> None:
        if event.input.id == "text-input":
            self.on_save()
    
    def action_cancel(self) -> None:
        self.dismiss(None)

class CommentsModal(ModalScreen[list[Comment]]):
    DEFAULT_CSS = """
    CommentsModal { align: center middle; }
    CommentsModal > Container {
        width: 80; height: 26; border: thick $primary;
        background: $surface; padding: 1 2;
    }
    CommentsModal .modal-title { text-align: center; text-style: bold; width: 100%; height: 1; margin-bottom: 1; }
    CommentsModal #comments-list { width: 100%; height: 12; overflow-y: auto; border: solid $primary-background; padding: 1; }
    CommentsModal .comment-item {
        width: 100%; height: 3; padding: 0 1;
        border: solid $primary-background; margin-bottom: 1;
    }
    CommentsModal .comment-item:hover { background: $boost; }
    CommentsModal .comment-item.selected { border: solid $accent; background: $surface-lighten-1; }
    CommentsModal .empty-msg { width: 100%; text-align: center; color: $text-muted; text-style: italic; padding: 2; }
    CommentsModal .hint { width: 100%; height: 1; text-align: center; color: $text-muted; margin: 1 0; }
    CommentsModal .button-row { width: 100%; height: 3; align: center middle; }
    CommentsModal Button { margin: 0 1; }
    """
    BINDINGS = [
        Binding("escape", "close", show=False),
        Binding("up", "move_up", show=False),
        Binding("down", "move_down", show=False),
        Binding("k", "move_up", show=False),
        Binding("j", "move_down", show=False),
        Binding("a", "add_comment", show=False),
        Binding("e", "edit_comment", show=False),
        Binding("d", "delete_comment", show=False),
        Binding("ctrl+o", "open_link", show=False),
        Binding("enter", "open_link", show=False),
        Binding("v", "view_image", show=False),
    ]
    
    def __init__(self, comments: list[Comment], next_comment_id: int, **kwargs) -> None:
        super().__init__(**kwargs)
        self.comments = [Comment(id=c.id, text=c.text, url=c.url, 
                                image_path=c.image_path, created_at=c.created_at) 
                        for c in comments]
        self.next_comment_id = next_comment_id
        self.selected_index = 0 if comments else -1
    
    def compose(self) -> ComposeResult:
        with Container():
            yield Label("💬 Comentarios", classes="modal-title")
            yield Container(id="comments-list")
            yield Label("↑↓ Navegar | a: Añadir | e: Editar | d: Eliminar | Enter: Abrir enlace | v: Ver imagen | Esc: Cerrar", classes="hint")
            with Horizontal(classes="button-row"):
                yield Button("➕ Añadir", variant="primary", id="add")
                yield Button("✏️ Editar", variant="default", id="edit")
                yield Button("🗑️ Eliminar", variant="error", id="delete")
    
    async def on_mount(self) -> None:
        await self.refresh_comments_list()
    
    async def refresh_comments_list(self) -> None:
        comments_list = self.query_one("#comments-list", Container)
        await comments_list.remove_children()
        
        if not self.comments:
            await comments_list.mount(Label("No hay comentarios. Pulsa 'a' para añadir uno.", classes="empty-msg"))
            self.selected_index = -1
        else:
            for i, comment in enumerate(self.comments):
                text = comment.text[:35] + "..." if len(comment.text) > 35 else comment.text
                
                link_icon = " 🔗" if comment.url else ""
                image_icon = " 📷" if comment.image_path else ""
                display_text = f"{text}{link_icon}{image_icon}  [{comment.created_at}]"
                
                item = Static(display_text, id=f"comment-{i}", classes="comment-item")
                await comments_list.mount(item)
                if i == self.selected_index:
                    item.add_class("selected")
            self.scroll_to_selected()
    
    def scroll_to_selected(self) -> None:
        if self.selected_index >= 0:
            try:
                item = self.query_one(f"#comment-{self.selected_index}", Static)
                item.scroll_visible()
            except: pass
    
    def update_selection(self) -> None:
        for i in range(len(self.comments)):
            try:
                item = self.query_one(f"#comment-{i}", Static)
                item.set_class(i == self.selected_index, "selected")
            except: pass
        self.scroll_to_selected()
    
    def action_move_up(self) -> None:
        if self.comments and self.selected_index > 0:
            self.selected_index -= 1
            self.update_selection()
    
    def action_move_down(self) -> None:
        if self.comments and self.selected_index < len(self.comments) - 1:
            self.selected_index += 1
            self.update_selection()
    
    def action_add_comment(self) -> None:
        def on_result(result: Optional[dict]) -> None:
            if result and result.get("text"):
                comment = Comment(
                    id=self.next_comment_id, 
                    text=result["text"],
                    url=result.get("url"),
                    image_path=result.get("image_path")
                )
                self.next_comment_id += 1
                self.comments.append(comment)
                self.selected_index = len(self.comments) - 1
                self.call_later(self.refresh_comments_list)
        self.app.push_screen(CommentEditModal("💬 Nuevo Comentario"), on_result)
    
    def action_edit_comment(self) -> None:
        if not self.comments or self.selected_index < 0:
            return
        comment = self.comments[self.selected_index]
        def on_result(result: Optional[dict]) -> None:
            if result and result.get("text"):
                comment.text = result["text"]
                comment.url = result.get("url")
                comment.image_path = result.get("image_path")
                self.call_later(self.refresh_comments_list)
        self.app.push_screen(
            CommentEditModal("✏️ Editar Comentario", initial_text=comment.text, 
                           initial_url=comment.url, initial_image=comment.image_path),
            on_result
        )
    
    def action_delete_comment(self) -> None:
        if not self.comments or self.selected_index < 0:
            return
        comment = self.comments[self.selected_index]
        txt = comment.text[:30] + "..." if len(comment.text) > 30 else comment.text
        def on_confirm(yes: bool) -> None:
            if yes:
                if comment.image_path and Path(comment.image_path).exists():
                    try:
                        Path(comment.image_path).unlink()
                    except:
                        pass
                
                self.comments.pop(self.selected_index)
                if self.selected_index >= len(self.comments) and self.selected_index > 0:
                    self.selected_index -= 1
                if not self.comments:
                    self.selected_index = -1
                self.call_later(self.refresh_comments_list)
        self.app.push_screen(ConfirmModal(f"¿Eliminar comentario '{txt}'?"), on_confirm)
    
    def action_open_link(self) -> None:
        if not self.comments or self.selected_index < 0:
            return
        comment = self.comments[self.selected_index]
        if comment.url:
            try:
                webbrowser.open(comment.url)
                self.app.notify(f"Abriendo: {comment.url}", severity="information")
            except Exception as e:
                self.app.notify(f"Error al abrir enlace: {str(e)}", severity="error")
        else:
            self.app.notify("Este comentario no tiene enlace", severity="warning")
    
    def action_view_image(self) -> None:
        if not self.comments or self.selected_index < 0:
            return
        comment = self.comments[self.selected_index]
        if comment.image_path:
            if Path(comment.image_path).exists():
                self.app.push_screen(ImageViewerModal(comment.image_path))
            else:
                self.app.notify("❌ Imagen no encontrada", severity="error")
        else:
            self.app.notify("Este comentario no tiene imagen", severity="warning")
    
    @on(Button.Pressed, "#add")
    def on_add(self) -> None:
        self.action_add_comment()
    
    @on(Button.Pressed, "#edit")
    def on_edit(self) -> None:
        self.action_edit_comment()
    
    @on(Button.Pressed, "#delete")
    def on_delete(self) -> None:
        self.action_delete_comment()
    
    def action_close(self) -> None:
        self.dismiss(self.comments)

class TagsManagerModal(ModalScreen[list[Tag]]):
    DEFAULT_CSS = """
    TagsManagerModal { align: center middle; }
    TagsManagerModal > Container {
        width: 60; height: 30; border: thick $primary;
        background: $surface; padding: 1 2;
    }
    TagsManagerModal .modal-title { text-align: center; text-style: bold; width: 100%; height: 1; margin-bottom: 1; }
    TagsManagerModal .search-label { color: $text-muted; margin-bottom: 0; }
    TagsManagerModal Input { width: 100%; margin-bottom: 1; }
    TagsManagerModal #tags-list { width: 100%; height: 12; overflow-y: auto; border: solid $primary-background; padding: 1; }
    TagsManagerModal .tag-item {
        width: 100%; height: 3; padding: 0 1;
        border: solid $primary-background; margin-bottom: 1;
    }
    TagsManagerModal .tag-item:hover { background: $boost; }
    TagsManagerModal .tag-item.selected { border: solid $accent; background: $surface-lighten-1; }
    TagsManagerModal .empty-msg { width: 100%; text-align: center; color: $text-muted; text-style: italic; padding: 2; }
    TagsManagerModal .hint { width: 100%; height: 1; text-align: center; color: $text-muted; margin: 1 0; }
    TagsManagerModal .button-row { width: 100%; height: 3; align: center middle; }
    TagsManagerModal Button { margin: 0 1; }
    """
    
    BINDINGS = [
        Binding("escape", "close", show=False),
        Binding("up", "move_up", show=False),
        Binding("down", "move_down", show=False),
        Binding("k", "move_up", show=False),
        Binding("j", "move_down", show=False),
        Binding("a", "add_tag", show=False),
        Binding("e", "edit_tag", show=False),
        Binding("d", "delete_tag", show=False),
        Binding("ctrl+f", "focus_search", show=False),
        Binding("/", "focus_search", show=False),
        Binding("tab", "blur_search", show=False),
    ]
    
    def __init__(self, tags: list[Tag], next_tag_id: int, **kwargs) -> None:
        super().__init__(**kwargs)
        self.tags = [Tag(id=t.id, name=t.name) for t in tags]
        self.next_tag_id = next_tag_id
        self.selected_index = 0 if tags else -1
        self.search_query = ""
        self.filtered_tags: list[Tag] = []
        self.search_focused = False
    
    def compose(self) -> ComposeResult:
        with Container():
            yield Label("🏷️  Gestionar Etiquetas", classes="modal-title")
            yield Label("🔍 Buscar (/ para activar, Tab para salir):", classes="search-label")
            yield Input(placeholder="Escribe para buscar etiquetas...", id="search-input")
            yield Container(id="tags-list")
            yield Label("↑↓ Navegar | a: Añadir | e: Editar | d: Eliminar | /: Buscar | Tab: Salir búsqueda | Esc: Cerrar", classes="hint")
            with Horizontal(classes="button-row"):
                yield Button("➕ Añadir", variant="primary", id="add")
                yield Button("✏️ Editar", variant="default", id="edit")
                yield Button("🗑️ Eliminar", variant="error", id="delete")
    
    async def on_mount(self) -> None:
        await self.refresh_tags_list()
    
    def _filter_tags(self) -> list[Tag]:
        if not self.search_query:
            return self.tags
        
        query_lower = self.search_query.lower()
        return [tag for tag in self.tags if query_lower in tag.name.lower()]
    
    async def refresh_tags_list(self) -> None:
        tags_list = self.query_one("#tags-list", Container)
        await tags_list.remove_children()
        
        self.filtered_tags = self._filter_tags()
        
        if not self.tags:
            await tags_list.mount(Label("No hay etiquetas. Pulsa 'a' para crear una.", classes="empty-msg"))
            self.selected_index = -1
        elif not self.filtered_tags:
            await tags_list.mount(Label(f"No se encontraron etiquetas para '{self.search_query}'", classes="empty-msg"))
            self.selected_index = -1
        else:
            if self.selected_index >= len(self.filtered_tags):
                self.selected_index = max(0, len(self.filtered_tags) - 1)
            
            for i, tag in enumerate(self.filtered_tags):
                item = Static(f"  {tag.name}  ", id=f"tag-{i}", classes="tag-item")
                await tags_list.mount(item)
                if i == self.selected_index:
                    item.add_class("selected")
            self.scroll_to_selected()
    
    def scroll_to_selected(self) -> None:
        if self.selected_index >= 0 and self.selected_index < len(self.filtered_tags):
            try:
                item = self.query_one(f"#tag-{self.selected_index}", Static)
                item.scroll_visible()
            except: pass
    
    def update_selection(self) -> None:
        for i in range(len(self.filtered_tags)):
            try:
                item = self.query_one(f"#tag-{i}", Static)
                item.set_class(i == self.selected_index, "selected")
            except: pass
        self.scroll_to_selected()
    
    def action_move_up(self) -> None:
        if self.search_focused:
            return
        if self.filtered_tags and self.selected_index > 0:
            self.selected_index -= 1
            self.update_selection()
    
    def action_move_down(self) -> None:
        if self.search_focused:
            return
        if self.filtered_tags and self.selected_index < len(self.filtered_tags) - 1:
            self.selected_index += 1
            self.update_selection()
    
    def action_focus_search(self) -> None:
        self.search_focused = True
        self.query_one("#search-input", Input).focus()
    
    def action_blur_search(self) -> None:
        self.search_focused = False
        try:
            self.query_one("#search-input", Input).blur()
        except:
            pass
        self.set_focus(None)
    
    def action_add_tag(self) -> None:
        if self.search_focused:
            return
        
        def on_result(name: Optional[str]) -> None:
            if name:
                tag_names = [n.strip() for n in name.split(';') if n.strip()]
                
                if not tag_names:
                    return
                
                created_count = 0
                duplicates = []
                
                for tag_name in tag_names:
                    tag_name_truncated = tag_name[:30]
                    
                    if any(t.name.lower() == tag_name_truncated.lower() for t in self.tags):
                        duplicates.append(tag_name_truncated)
                        continue
                    
                    tag = Tag(id=self.next_tag_id, name=tag_name_truncated)
                    self.next_tag_id += 1
                    self.tags.append(tag)
                    created_count += 1
                
                if created_count > 0:
                    self.selected_index = 0
                    self.search_query = ""
                    try:
                        self.query_one("#search-input", Input).value = ""
                    except: pass
                    self.call_later(self.refresh_tags_list)
                    
                    if created_count == 1:
                        self.app.notify(f"Etiqueta '{tag_names[0][:30]}' creada", severity="information")
                    else:
                        self.app.notify(f"{created_count} etiquetas creadas", severity="information")
                
                if duplicates:
                    if len(duplicates) == 1:
                        self.app.notify(f"'{duplicates[0]}' ya existe", severity="warning")
                    else:
                        self.app.notify(f"{len(duplicates)} etiquetas ya existían", severity="warning")
        
        self.app.push_screen(
            InputModal(
                "🏷️  Nueva(s) Etiqueta(s)", 
                placeholder="Nombre (usa ; para crear varias)"
            ), 
            on_result
        )
    
    def action_edit_tag(self) -> None:
        if self.search_focused:
            return
        if not self.filtered_tags or self.selected_index < 0 or self.selected_index >= len(self.filtered_tags):
            return
        tag = self.filtered_tags[self.selected_index]
        
        def on_result(name: Optional[str]) -> None:
            if name:
                tag.name = name[:30]
                self.call_later(self.refresh_tags_list)
        self.app.push_screen(InputModal("✏️  Editar Etiqueta", initial_text=tag.name), on_result)
    
    def action_delete_tag(self) -> None:
        if self.search_focused:
            return
        if not self.filtered_tags or self.selected_index < 0 or self.selected_index >= len(self.filtered_tags):
            return
        tag = self.filtered_tags[self.selected_index]
        
        def on_confirm(yes: bool) -> None:
            if yes:
                self.tags.remove(tag)
                if self.selected_index >= len(self.filtered_tags) and self.selected_index > 0:
                    self.selected_index -= 1
                if not self.tags:
                    self.selected_index = -1
                self.call_later(self.refresh_tags_list)
        self.app.push_screen(ConfirmModal(f"¿Eliminar etiqueta '{tag.name}'?"), on_confirm)
    
    @on(Button.Pressed, "#add")
    def on_add(self) -> None:
        self.action_add_tag()
    
    @on(Button.Pressed, "#edit")
    def on_edit(self) -> None:
        self.action_edit_tag()
    
    @on(Button.Pressed, "#delete")
    def on_delete(self) -> None:
        self.action_delete_tag()
    
    @on(Input.Changed, "#search-input")
    async def on_search_changed(self, event: Input.Changed) -> None:
        self.search_query = event.value.strip()
        self.selected_index = 0
        await self.refresh_tags_list()
    
    @on(Input.Submitted, "#search-input")
    def on_search_submitted(self, event: Input.Submitted) -> None:
        self.action_blur_search()
    
    def action_close(self) -> None:
        self.dismiss(self.tags)

class TagPickerModal(ModalScreen[list[int]]):
    DEFAULT_CSS = """
    TagPickerModal { align: center middle; }
    TagPickerModal > Container {
        width: 60; height: 26; border: thick $primary;
        background: $surface; padding: 1 2;
    }
    TagPickerModal .modal-title { text-align: center; text-style: bold; width: 100%; height: 1; margin-bottom: 1; }
    TagPickerModal .search-label { color: $text-muted; margin-bottom: 0; }
    TagPickerModal Input { width: 100%; margin-bottom: 1; }
    TagPickerModal #tags-list { width: 100%; height: 12; overflow-y: auto; border: solid $primary-background; padding: 1; }
    TagPickerModal .tag-item {
        width: 100%; height: 3; padding: 0 1;
        border: solid $primary-background; margin-bottom: 1;
    }
    TagPickerModal .tag-item:hover { background: $boost; }
    TagPickerModal .tag-item.selected { border: solid $accent; background: $surface-lighten-1; }
    TagPickerModal .tag-item.checked { color: $success; }
    TagPickerModal .empty-msg { width: 100%; text-align: center; color: $text-muted; text-style: italic; padding: 2; }
    TagPickerModal .hint { width: 100%; height: 1; text-align: center; color: $text-muted; margin: 1 0; }
    TagPickerModal .button-row { width: 100%; height: 3; align: center middle; }
    TagPickerModal Button { margin: 0 1; }
    """
    BINDINGS = [
        Binding("escape", "cancel", show=False),
        Binding("up", "move_up", show=False),
        Binding("down", "move_down", show=False),
        Binding("k", "move_up", show=False),
        Binding("j", "move_down", show=False),
        Binding("space", "toggle_tag", show=False),
        Binding("enter", "save", show=False),
        Binding("ctrl+f", "focus_search", show=False),
        Binding("/", "focus_search", show=False),
        Binding("tab", "blur_search", show=False),
    ]
    
    def __init__(self, all_tags: list[Tag], selected_tag_ids: list[int], **kwargs) -> None:
        super().__init__(**kwargs)
        self.all_tags = all_tags
        self.selected_tag_ids = list(selected_tag_ids)
        self.selected_index = 0 if all_tags else -1
        self.search_query = ""
        self.filtered_tags: list[Tag] = []
        self.search_focused = False
    
    def compose(self) -> ComposeResult:
        with Container():
            yield Label("🏷️  Seleccionar Etiquetas", classes="modal-title")
            yield Label("🔍 Buscar (/ para activar, Tab para salir):", classes="search-label")
            yield Input(placeholder="Escribe para buscar etiquetas...", id="search-input")
            yield Container(id="tags-list")
            yield Label("↑↓ Navegar | Espacio: Marcar | /: Buscar | Tab: Salir búsqueda | Enter: Guardar", classes="hint")
            with Horizontal(classes="button-row"):
                yield Button("Guardar", variant="primary", id="save")
                yield Button("Cancelar", variant="default", id="cancel")
    
    async def on_mount(self) -> None:
        await self.refresh_tags_list()
    
    def _filter_tags(self) -> list[Tag]:
        if not self.search_query:
            return self.all_tags
        
        query_lower = self.search_query.lower()
        return [tag for tag in self.all_tags if query_lower in tag.name.lower()]
    
    async def refresh_tags_list(self) -> None:
        tags_list = self.query_one("#tags-list", Container)
        await tags_list.remove_children()
        
        self.filtered_tags = self._filter_tags()
        
        if not self.all_tags:
            await tags_list.mount(Label("No hay etiquetas. Créalas con 'T' en el menú principal.", classes="empty-msg"))
            self.selected_index = -1
        elif not self.filtered_tags:
            await tags_list.mount(Label(f"No se encontraron etiquetas para '{self.search_query}'", classes="empty-msg"))
            self.selected_index = -1
        else:
            if self.selected_index >= len(self.filtered_tags):
                self.selected_index = max(0, len(self.filtered_tags) - 1)
            
            for i, tag in enumerate(self.filtered_tags):
                checked = "☑" if tag.id in self.selected_tag_ids else "☐"
                item = Static(f"{checked}  {tag.name}", id=f"tag-{i}", classes="tag-item")
                await tags_list.mount(item)
                if tag.id in self.selected_tag_ids:
                    item.add_class("checked")
                if i == self.selected_index:
                    item.add_class("selected")
            self.scroll_to_selected()
    
    def scroll_to_selected(self) -> None:
        if self.selected_index >= 0 and self.selected_index < len(self.filtered_tags):
            try:
                item = self.query_one(f"#tag-{self.selected_index}", Static)
                item.scroll_visible()
            except: pass
    
    def update_selection(self) -> None:
        for i in range(len(self.filtered_tags)):
            try:
                item = self.query_one(f"#tag-{i}", Static)
                item.set_class(i == self.selected_index, "selected")
            except: pass
        self.scroll_to_selected()
    
    def action_move_up(self) -> None:
        if self.search_focused:
            return
        if self.filtered_tags and self.selected_index > 0:
            self.selected_index -= 1
            self.update_selection()
    
    def action_move_down(self) -> None:
        if self.search_focused:
            return
        if self.filtered_tags and self.selected_index < len(self.filtered_tags) - 1:
            self.selected_index += 1
            self.update_selection()
    
    def action_toggle_tag(self) -> None:
        if self.search_focused:
            return
        if not self.filtered_tags or self.selected_index < 0 or self.selected_index >= len(self.filtered_tags):
            return
        tag = self.filtered_tags[self.selected_index]
        if tag.id in self.selected_tag_ids:
            self.selected_tag_ids.remove(tag.id)
        else:
            self.selected_tag_ids.append(tag.id)
        self.call_later(self.refresh_tags_list)
    
    def action_focus_search(self) -> None:
        self.search_focused = True
        self.query_one("#search-input", Input).focus()
    
    def action_blur_search(self) -> None:
        self.search_focused = False
        try:
            self.query_one("#search-input", Input).blur()
        except:
            pass
        self.set_focus(None)
    
    def action_save(self) -> None:
        self.dismiss(self.selected_tag_ids)
    
    @on(Button.Pressed, "#save")
    def on_save(self) -> None:
        self.action_save()
    
    @on(Button.Pressed, "#cancel")
    def on_cancel(self) -> None:
        self.action_cancel()
    
    @on(Input.Changed, "#search-input")
    async def on_search_changed(self, event: Input.Changed) -> None:
        self.search_query = event.value.strip()
        self.selected_index = 0
        await self.refresh_tags_list()
    
    @on(Input.Submitted, "#search-input")
    def on_search_submitted(self, event: Input.Submitted) -> None:
        self.action_blur_search()
    
    def action_cancel(self) -> None:
        self.dismiss(None)

class StatusFilterPickerModal(ModalScreen[Optional[list[str]]]):
    DEFAULT_CSS = """
    StatusFilterPickerModal { align: center middle; }
    StatusFilterPickerModal > Container {
        width: 40; height: auto; border: thick $primary;
        background: $surface; padding: 1 2;
    }
    StatusFilterPickerModal .modal-title { text-align: center; text-style: bold; width: 100%; height: 1; margin-bottom: 1; }
    StatusFilterPickerModal #status-list { width: 100%; height: auto; padding: 1; }
    StatusFilterPickerModal .status-item {
        width: 100%; height: 3; padding: 0 1;
        border: solid $primary-background; margin-bottom: 1;
        content-align: center middle;
    }
    StatusFilterPickerModal .status-item:hover { background: $boost; }
    StatusFilterPickerModal .status-item.selected { border: solid $accent; background: $surface-lighten-1; }
    StatusFilterPickerModal .status-item.checked { color: $success; }
    StatusFilterPickerModal .hint { width: 100%; height: 1; text-align: center; color: $text-muted; margin: 1 0; }
    StatusFilterPickerModal .button-row { width: 100%; height: 3; align: center middle; }
    StatusFilterPickerModal Button { margin: 0 1; }
    """
    BINDINGS = [
        Binding("escape", "cancel", show=False),
        Binding("up", "move_up", show=False),
        Binding("down", "move_down", show=False),
        Binding("k", "move_up", show=False),
        Binding("j", "move_down", show=False),
        Binding("space", "toggle_status", show=False),
        Binding("enter", "save", show=False),
    ]
    
    def __init__(self, current_filters: list[str], **kwargs) -> None:
        super().__init__(**kwargs)
        self.selected_status_ids = list(current_filters)
        self.options = ["pending", "completed"]
        self.selected_index = 0
    
    def compose(self) -> ComposeResult:
        with Container():
            yield Label("✓ Filtrar por Estado", classes="modal-title")
            yield Container(id="status-list")
            yield Label("↑↓ Navegar | Espacio: Marcar/Desmarcar | Enter: Guardar | Esc: Cancelar", classes="hint")
            with Horizontal(classes="button-row"):
                yield Button("Guardar", variant="primary", id="save")
                yield Button("Cancelar", variant="default", id="cancel")
    
    async def on_mount(self) -> None:
        await self.refresh_list()
    
    async def refresh_list(self) -> None:
        status_list = self.query_one("#status-list", Container)
        await status_list.remove_children()
        
        options_display = [
            ("⏳ Pendientes", "pending"),
            ("✅ Completadas", "completed")
        ]
        
        for i, (text, value) in enumerate(options_display):
            checked = "☑" if value in self.selected_status_ids else "☐"
            display_text = f"{checked}  {text}"
            item = Static(display_text, id=f"status-{i}", classes="status-item")
            await status_list.mount(item)
            if value in self.selected_status_ids:
                item.add_class("checked")
            if i == self.selected_index:
                item.add_class("selected")
    
    def scroll_to_selected(self) -> None:
        if self.selected_index >= 0:
            try:
                item = self.query_one(f"#status-{self.selected_index}", Static)
                item.scroll_visible()
            except: pass
    
    def update_selection(self) -> None:
        for i in range(len(self.options)):
            try:
                item = self.query_one(f"#status-{i}", Static)
                item.set_class(i == self.selected_index, "selected")
            except: pass
        self.scroll_to_selected()
    
    def action_move_up(self) -> None:
        if self.options and self.selected_index > 0:
            self.selected_index -= 1
            self.update_selection()
    
    def action_move_down(self) -> None:
        if self.options and self.selected_index < len(self.options) - 1:
            self.selected_index += 1
            self.update_selection()
    
    def action_toggle_status(self) -> None:
        if not self.options or self.selected_index < 0:
            return
        status_id = self.options[self.selected_index]
        if status_id in self.selected_status_ids:
            self.selected_status_ids.remove(status_id)
        else:
            self.selected_status_ids.append(status_id)
        self.call_later(self.refresh_list) 
    
    def action_save(self) -> None:
        self.dismiss(self.selected_status_ids)
    
    @on(Button.Pressed, "#save")
    def on_save_btn(self) -> None:
        self.action_save()
    
    def action_cancel(self) -> None:
        self.dismiss(None)

class PriorityFilterPickerModal(ModalScreen[Optional[list[int]]]):
    DEFAULT_CSS = """
    PriorityFilterPickerModal { align: center middle; }
    PriorityFilterPickerModal > Container {
        width: 40; height: auto; border: thick $primary;
        background: $surface; padding: 1 2;
    }
    PriorityFilterPickerModal .modal-title { text-align: center; text-style: bold; width: 100%; height: 1; margin-bottom: 1; }
    PriorityFilterPickerModal #priority-list { width: 100%; height: auto; padding: 1; }
    PriorityFilterPickerModal .priority-item {
        width: 100%; height: 3; padding: 0 1;
        border: solid $primary-background; margin-bottom: 1;
        content-align: center middle;
    }
    PriorityFilterPickerModal .priority-item:hover { background: $boost; }
    PriorityFilterPickerModal .priority-item.selected { border: solid $accent; background: $surface-lighten-1; }
    PriorityFilterPickerModal .priority-item.checked { color: $success; }
    PriorityFilterPickerModal .hint { width: 100%; height: 1; text-align: center; color: $text-muted; margin: 1 0; }
    PriorityFilterPickerModal .button-row { width: 100%; height: 3; align: center middle; }
    PriorityFilterPickerModal Button { margin: 0 1; }
    """
    BINDINGS = [
        Binding("escape", "cancel", show=False),
        Binding("up", "move_up", show=False),
        Binding("down", "move_down", show=False),
        Binding("k", "move_up", show=False),
        Binding("j", "move_down", show=False),
        Binding("space", "toggle_priority", show=False),
        Binding("enter", "save", show=False),
    ]
    
    def __init__(self, current_filters: list[int], **kwargs) -> None:
        super().__init__(**kwargs)
        self.selected_priority_ids = list(current_filters)
        self.options = [0, 1, 2, 3]
        self.selected_index = 0
    
    def compose(self) -> ComposeResult:
        with Container():
            yield Label("⭐ Filtrar por Prioridad", classes="modal-title")
            yield Container(id="priority-list")
            yield Label("↑↓ Navegar | Espacio: Marcar/Desmarcar | Enter: Guardar | Esc: Cancelar", classes="hint")
            with Horizontal(classes="button-row"):
                yield Button("Guardar", variant="primary", id="save")
                yield Button("Cancelar", variant="default", id="cancel")
    
    async def on_mount(self) -> None:
        await self.refresh_list()
    
    async def refresh_list(self) -> None:
        priority_list = self.query_one("#priority-list", Container)
        await priority_list.remove_children()
        
        priorities = [
            ("   Sin prioridad", 0),
            ("[green]■[/green]  Baja", 1),
            ("[yellow]■[/yellow]  Media", 2),
            ("[red]■[/red]  Alta", 3)
        ]
        
        for i, (text, value) in enumerate(priorities):
            checked = "☑" if value in self.selected_priority_ids else "☐"
            display_text = f"{checked}  {text}"
            item = Static(display_text, id=f"priority-{i}", classes="priority-item")
            await priority_list.mount(item)
            if value in self.selected_priority_ids:
                item.add_class("checked")
            if i == self.selected_index:
                item.add_class("selected")
    
    def scroll_to_selected(self) -> None:
        if self.selected_index >= 0:
            try:
                item = self.query_one(f"#priority-{self.selected_index}", Static)
                item.scroll_visible()
            except: pass
    
    def update_selection(self) -> None:
        for i in range(len(self.options)):
            try:
                item = self.query_one(f"#priority-{i}", Static)
                item.set_class(i == self.selected_index, "selected")
            except: pass
        self.scroll_to_selected()
    
    def action_move_up(self) -> None:
        if self.options and self.selected_index > 0:
            self.selected_index -= 1
            self.update_selection()
    
    def action_move_down(self) -> None:
        if self.options and self.selected_index < len(self.options) - 1:
            self.selected_index += 1
            self.update_selection()
    
    def action_toggle_priority(self) -> None:
        if not self.options or self.selected_index < 0:
            return
        priority_id = self.options[self.selected_index]
        if priority_id in self.selected_priority_ids:
            self.selected_priority_ids.remove(priority_id)
        else:
            self.selected_priority_ids.append(priority_id)
        self.call_later(self.refresh_list)
    
    def action_save(self) -> None:
        self.dismiss(self.selected_priority_ids)
    
    @on(Button.Pressed, "#save")
    def on_save_btn(self) -> None:
        self.action_save()
    
    @on(Button.Pressed, "#cancel")
    def on_cancel_btn(self) -> None:
        self.dismiss(None)
    
    def action_cancel(self) -> None:
        self.dismiss(None)

class FilterModal(ModalScreen[Optional[dict]]):
    DEFAULT_CSS = """
    FilterModal { align: center middle; }
    FilterModal > Container {
        width: 70; height: auto; border: thick $primary;
        background: $surface; padding: 1 2;
    }
    FilterModal .modal-title { text-align: center; text-style: bold; width: 100%; margin-bottom: 1; }
    FilterModal .section-label { margin-top: 1; color: $text-muted; }
    FilterModal .filter-row { width: 100%; height: auto; align: left middle; margin-bottom: 1; }
    FilterModal .filter-display { width: 1fr; padding: 0 1; }
    FilterModal .button-row { width: 100%; height: auto; align: center middle; margin-top: 1; }
    FilterModal Button { margin: 0 1; }
    """
    BINDINGS = [Binding("escape", "cancel", show=False)]
    
    def __init__(self, current_date_filters: list[str], current_tag_filters: list[int],
                 current_status_filters: list[str], current_priority_filters: list[int],
                 all_tags: list[Tag], available_dates: list[str], **kwargs) -> None:
        super().__init__(**kwargs)
        self.date_filters = list(current_date_filters)
        self.tag_filters = list(current_tag_filters)
        self.status_filters = list(current_status_filters)
        self.priority_filters = list(current_priority_filters)
        self.all_tags = all_tags
        self.available_dates = available_dates
    
    def compose(self) -> ComposeResult:
        with Container():
            yield Label("🔍 Filtrar Tareas", classes="modal-title")
            yield Label("Fecha:", classes="section-label")
            with Horizontal(classes="filter-row"):
                yield Label(self._format_date_filter(), id="date-display", classes="filter-display")
                yield Button("📅 Seleccionar", id="change-date")
                yield Button("❌ Quitar", id="remove-date")
            yield Label("Etiquetas:", classes="section-label")
            with Horizontal(classes="filter-row"):
                yield Label(self._format_tag_filter(), id="tag-display", classes="filter-display")
                yield Button("🏷️ Seleccionar", id="change-tag")
                yield Button("❌ Quitar", id="remove-tag")
            yield Label("Estado:", classes="section-label")
            with Horizontal(classes="filter-row"):
                yield Label(self._format_status_filter(), id="status-display", classes="filter-display")
                yield Button("✓ Seleccionar", id="change-status")
                yield Button("❌ Quitar", id="remove-status")
            yield Label("Prioridad:", classes="section-label")
            with Horizontal(classes="filter-row"):
                yield Label(self._format_priority_filter(), id="priority-display", classes="filter-display")
                yield Button("⭐ Seleccionar", id="change-priority")
                yield Button("❌ Quitar", id="remove-priority")
            with Horizontal(classes="button-row"):
                yield Button("Aplicar", variant="primary", id="apply")
                yield Button("Quitar todos", variant="warning", id="clear")
    
    def _format_date_filter(self) -> str:
        if not self.date_filters:
            return "Todas las fechas"
        date_strs = []
        for fd in self.date_filters:
            if fd == "none":
                date_strs.append("Sin fecha")
            else:
                try:
                    d = datetime.strptime(fd, "%Y-%m-%d")
                    date_strs.append(f"{d.day:02d}/{d.month:02d}")
                except: pass
        return f"📅 {', '.join(date_strs)}" if date_strs else "Todas las fechas"
    
    def _format_tag_filter(self) -> str:
        if not self.tag_filters:
            return "Todas las etiquetas"
        tag_names = []
        for tag_id in self.tag_filters:
            tag = next((t for t in self.all_tags if t.id == tag_id), None)
            if tag:
                tag_names.append(tag.name)
        if tag_names:
            return f"🏷️ {', '.join(tag_names)}"
        return "Todas las etiquetas"
    
    def _format_status_filter(self) -> str:
        if not self.status_filters:
            return "Todos los estados"
        status_names = []
        for status in self.status_filters:
            if status == "completed":
                status_names.append("Completadas")
            elif status == "pending":
                status_names.append("Pendientes")
        return f"✅ {', '.join(status_names)}" if status_names else "Todos los estados"
    
    def _format_priority_filter(self) -> str:
        if not self.priority_filters:
            return "Todas las prioridades"
        priority_names = {0: "Sin prioridad", 1: "■ Baja", 2: "■ Media", 3: "■ Alta"}
        priority_strs = [priority_names.get(p, '') for p in self.priority_filters]
        return f"⭐ {', '.join(priority_strs)}" if priority_strs else "Todas las prioridades"
    
    @on(Button.Pressed, "#change-date")
    def on_change_date(self) -> None:
        def on_result(result: Optional[list[str]]) -> None:
            if result is not None:
                self.date_filters = result
                self.query_one("#date-display", Label).update(self._format_date_filter())
        self.app.push_screen(DateFilterPickerModal(self.available_dates, self.date_filters), on_result)
    
    @on(Button.Pressed, "#remove-date")
    def on_remove_date(self) -> None:
        self.date_filters = []
        self.query_one("#date-display", Label).update(self._format_date_filter())
    
    @on(Button.Pressed, "#change-tag")
    def on_change_tag(self) -> None:
        def on_result(result: Optional[list[int]]) -> None:
            if result is not None:
                self.tag_filters = result
                self.query_one("#tag-display", Label).update(self._format_tag_filter())
        self.app.push_screen(TagPickerModal(self.all_tags, self.tag_filters), on_result)
    
    @on(Button.Pressed, "#remove-tag")
    def on_remove_tag(self) -> None:
        self.tag_filters = []
        self.query_one("#tag-display", Label).update(self._format_tag_filter())
    
    @on(Button.Pressed, "#change-status")
    def on_change_status(self) -> None:
        def on_result(result: Optional[list[str]]) -> None:
            if result is not None:
                self.status_filters = result
                self.query_one("#status-display", Label).update(self._format_status_filter())
        self.app.push_screen(StatusFilterPickerModal(self.status_filters), on_result)
    
    @on(Button.Pressed, "#remove-status")
    def on_remove_status(self) -> None:
        self.status_filters = []
        self.query_one("#status-display", Label).update(self._format_status_filter())
    
    @on(Button.Pressed, "#change-priority")
    def on_change_priority(self) -> None:
        def on_result(result: Optional[list[int]]) -> None:
            if result is not None:
                self.priority_filters = result
                self.query_one("#priority-display", Label).update(self._format_priority_filter())
        self.app.push_screen(PriorityFilterPickerModal(self.priority_filters), on_result)
    
    @on(Button.Pressed, "#remove-priority")
    def on_remove_priority(self) -> None:
        self.priority_filters = []
        self.query_one("#priority-display", Label).update(self._format_priority_filter())
    
    @on(Button.Pressed, "#apply")
    def on_apply(self) -> None:
        self.dismiss({
            "dates": self.date_filters,
            "tags": self.tag_filters,
            "statuses": self.status_filters,
            "priorities": self.priority_filters
        })
    
    @on(Button.Pressed, "#clear")
    def on_clear(self) -> None:
        self.dismiss({"dates": [], "tags": [], "statuses": [], "priorities": []})
    
    def action_cancel(self) -> None:
        self.dismiss(None)

class DateFilterPickerModal(ModalScreen[Optional[list[str]]]):
    DEFAULT_CSS = """
    DateFilterPickerModal { align: center middle; }
    DateFilterPickerModal > Container {
        width: 50; height: 26; border: thick $primary;
        background: $surface; padding: 1 2;
    }
    DateFilterPickerModal .modal-title { text-align: center; text-style: bold; width: 100%; height: 1; margin-bottom: 1; }
    DateFilterPickerModal #dates-list { width: 100%; height: 12; overflow-y: auto; border: solid $primary-background; padding: 1; }
    DateFilterPickerModal .date-item {
        width: 100%; height: 3; padding: 0 1;
        border: solid $primary-background; margin-bottom: 1;
    }
    DateFilterPickerModal .date-item:hover { background: $boost; }
    DateFilterPickerModal .date-item.selected { border: solid $accent; background: $surface-lighten-1; }
    DateFilterPickerModal .date-item.checked { color: $success; }
    DateFilterPickerModal .hint { width: 100%; height: 1; text-align: center; color: $text-muted; margin: 1 0; }
    DateFilterPickerModal .button-row { width: 100%; height: 3; align: center middle; }
    DateFilterPickerModal Button { margin: 0 1; }
    """
    BINDINGS = [
        Binding("escape", "cancel", show=False),
        Binding("up", "move_up", show=False),
        Binding("down", "move_down", show=False),
        Binding("k", "move_up", show=False),
        Binding("j", "move_down", show=False),
        Binding("space", "toggle_date", show=False),
        Binding("enter", "save", show=False),
    ]
    
    def __init__(self, available_dates: list[str], current_filters: list[str], **kwargs) -> None:
        super().__init__(**kwargs)
        self.available_dates = available_dates
        self.selected_date_ids = list(current_filters)
        self.options = ["none"] + sorted(set(available_dates), reverse=True)
        self.selected_index = 0
    
    def compose(self) -> ComposeResult:
        with Container():
            yield Label("📅 Filtrar por Fecha", classes="modal-title")
            yield Container(id="dates-list")
            yield Label("↑↓ Navegar | Espacio: Marcar/Desmarcar | Enter: Guardar | Esc: Cancelar", classes="hint")
            with Horizontal(classes="button-row"):
                yield Button("Guardar", variant="primary", id="save")
                yield Button("Cancelar", variant="default", id="cancel")
    
    async def on_mount(self) -> None:
        await self.refresh_list()
    
    async def refresh_list(self) -> None:
        dates_list = self.query_one("#dates-list", Container)
        await dates_list.remove_children()
        
        for i, opt in enumerate(self.options):
            checked = "☑" if opt in self.selected_date_ids else "☐"
            if opt == "none":
                text = f"{checked}  Sin fecha asignada"
            else:
                try:
                    d = datetime.strptime(opt, "%Y-%m-%d")
                    text = f"{checked}  {d.day:02d}/{d.month:02d}/{d.year}"
                except:
                    text = f"{checked}  {opt}"
            
            item = Static(text, id=f"date-{i}", classes="date-item")
            await dates_list.mount(item)
            if opt in self.selected_date_ids:
                item.add_class("checked")
            if i == self.selected_index:
                item.add_class("selected")
    
    def scroll_to_selected(self) -> None:
        if self.selected_index >= 0:
            try:
                item = self.query_one(f"#date-{self.selected_index}", Static)
                item.scroll_visible()
            except: pass
    
    def update_selection(self) -> None:
        for i in range(len(self.options)):
            try:
                item = self.query_one(f"#date-{i}", Static)
                item.set_class(i == self.selected_index, "selected")
            except: pass
        self.scroll_to_selected()
    
    def action_move_up(self) -> None:
        if self.options and self.selected_index > 0:
            self.selected_index -= 1
            self.update_selection()
    
    def action_move_down(self) -> None:
        if self.options and self.selected_index < len(self.options) - 1:
            self.selected_index += 1
            self.update_selection()
    
    def action_toggle_date(self) -> None:
        if not self.options or self.selected_index < 0:
            return
        date_id = self.options[self.selected_index]
        if date_id in self.selected_date_ids:
            self.selected_date_ids.remove(date_id)
        else:
            self.selected_date_ids.append(date_id)
        self.call_later(self.refresh_list)
    
    def action_save(self) -> None:
        self.dismiss(self.selected_date_ids)
    
    @on(Button.Pressed, "#save")
    def on_save_btn(self) -> None:
        self.action_save()
    
    @on(Button.Pressed, "#cancel")
    def on_cancel_btn(self) -> None:
        self.dismiss(None)
    
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
    EditTaskModal .group-row { width: 100%; height: auto; align: left middle; margin-bottom: 1; }
    EditTaskModal .priority-row { width: 100%; height: auto; align: left middle; margin-bottom: 1; }
    EditTaskModal .comments-row { width: 100%; height: auto; align: left middle; margin-bottom: 1; }
    EditTaskModal .tags-row { width: 100%; height: auto; align: left middle; margin-bottom: 1; }
    EditTaskModal .date-display { width: 1fr; padding: 0 1; }
    EditTaskModal .group-display { width: 1fr; padding: 0 1; }
    EditTaskModal .priority-display { width: 1fr; padding: 0 1; }
    EditTaskModal .comments-display { width: 1fr; padding: 0 1; }
    EditTaskModal .tags-display { width: 1fr; padding: 0 1; }
    EditTaskModal .button-row { width: 100%; height: auto; align: center middle; margin-top: 1; }
    EditTaskModal Button { margin: 0 1; }
    EditTaskModal .subtasks-row { width: 100%; height: auto; align: left middle; margin-bottom: 1; }
    EditTaskModal .subtasks-display { width: 1fr; padding: 0 1; }
    """
    BINDINGS = [Binding("escape", "cancel", show=False)]
    
    def __init__(self, task_text: str, current_date: Optional[str] = None,
                current_group_id: Optional[int] = None, groups: list[Group] = None,
                comments: list[Comment] = None, next_comment_id: int = 1,
                all_tags: list[Tag] = None, selected_tag_ids: list[int] = None,
                current_priority: int = 0, 
                subtasks: list = None, next_subtask_id: int = 1,
                **kwargs) -> None:
        super().__init__(**kwargs)
        self.task_text = task_text
        self.selected_date = current_date
        self.selected_group_id = current_group_id
        self.groups = groups or []
        self.comments = comments or []
        self.next_comment_id = next_comment_id
        self.all_tags = all_tags or []
        self.selected_tag_ids = list(selected_tag_ids) if selected_tag_ids else []
        self.selected_priority = current_priority
        self.subtasks = subtasks or []
        self.next_subtask_id = next_subtask_id
    
    def compose(self) -> ComposeResult:
        with Container():
            yield Label("✏️  Editar Tarea", classes="modal-title")
            yield Label("Texto:", classes="section-label")
            yield Input(value=self.task_text, id="task-input")
            yield Label("Grupo:", classes="section-label")
            with Horizontal(classes="group-row"):
                yield Label(self._format_group(self.selected_group_id), id="group-display", classes="group-display")
                yield Button("📁 Cambiar", id="change-group")
            yield Label("Prioridad:", classes="section-label")
            with Horizontal(classes="priority-row"):
                yield Label(self._format_priority(), id="priority-display", classes="priority-display")
                yield Button("⭐ Cambiar", id="change-priority")
            yield Label("Fecha:", classes="section-label")
            with Horizontal(classes="date-row"):
                yield Label(self._format_date(self.selected_date), id="date-display", classes="date-display")
                yield Button("📅 Cambiar", id="change-date")
                yield Button("❌ Quitar", id="remove-date")
            yield Label("Etiquetas:", classes="section-label")
            with Horizontal(classes="tags-row"):
                yield Label(self._format_tags(), id="tags-display", classes="tags-display")
                yield Button("🏷️ Seleccionar", id="select-tags")
            yield Label("Comentarios:", classes="section-label")
            with Horizontal(classes="comments-row"):
                yield Label(self._format_comments(), id="comments-display", classes="comments-display")
                yield Button("💬 Gestionar", id="manage-comments")
            yield Label("Subtareas:", classes="section-label")
            with Horizontal(classes="subtasks-row"):
                yield Label(self._format_subtasks(), id="subtasks-display", classes="subtasks-display")
                yield Button("📋 Gestionar", id="manage-subtasks")
            with Horizontal(classes="button-row"):
                yield Button("Guardar", variant="primary", id="save")
                yield Button("Cancelar", variant="default", id="cancel")

    def _format_date(self, date_str: Optional[str]) -> str:
        if not date_str: return "Sin fecha"
        try:
            d = datetime.strptime(date_str, "%Y-%m-%d")
            return f"📅 {d.day:02d}/{d.month:02d}/{d.year}"
        except: return "Sin fecha"
    
    def _format_group(self, group_id: Optional[int]) -> str:
        if group_id is None:
            return "📋 Sin grupo"
        group = next((g for g in self.groups if g.id == group_id), None)
        if group:
            return f"📁 {group.name}"
        return "📋 Sin grupo"
    
    def _format_priority(self) -> str:
        priority_names = {
            0: "Sin prioridad",
            1: "■ Baja",
            2: "■ Media",
            3: "■ Alta"
        }
        return priority_names.get(self.selected_priority, "Sin prioridad")
    
    def _format_comments(self) -> str:
        count = len(self.comments)
        if count == 0:
            return "Sin comentarios"
        elif count == 1:
            return "💬 1 comentario"
        else:
            return f"💬 {count} comentarios"
    
    def _format_tags(self) -> str:
        if not self.selected_tag_ids:
            return "Sin etiquetas"
        tag_names = []
        for tag_id in self.selected_tag_ids[:3]:
            tag = next((t for t in self.all_tags if t.id == tag_id), None)
            if tag:
                tag_names.append(tag.name)
        result = "🏷️ " + ", ".join(tag_names)
        if len(self.selected_tag_ids) > 3:
            result += f" (+{len(self.selected_tag_ids) - 3})"
        return result
    
    def on_mount(self) -> None:
        self.query_one("#task-input", Input).focus()
    
    def _format_subtasks(self) -> str:
        count = len(self.subtasks)
        if count == 0:
            return "Sin subtareas"
        done_count = sum(1 for s in self.subtasks if s.done)
        return f"📋 {done_count}/{count} completadas"

    @on(Button.Pressed, "#manage-subtasks")
    def on_manage_subtasks(self) -> None:
        def on_result(updated_subtasks: list) -> None:
            self.subtasks = updated_subtasks
            if self.subtasks:
                self.next_subtask_id = max(s.id for s in self.subtasks) + 1
            self.query_one("#subtasks-display", Label).update(self._format_subtasks())
        
        next_comment_id = self.next_comment_id
        for subtask in self.subtasks:
            if subtask.comments:
                max_id = max(c.id for c in subtask.comments)
                if max_id >= next_comment_id:
                    next_comment_id = max_id + 1
        
        self.app.push_screen(SubtasksModal(self.subtasks, self.next_subtask_id, next_comment_id), on_result)  
    
    @on(Button.Pressed, "#change-group")
    def on_change_group(self) -> None:
        def on_result(result: Optional[int]) -> None:
            self.selected_group_id = result
            self.query_one("#group-display", Label).update(self._format_group(self.selected_group_id))
        self.app.push_screen(GroupPickerModal(self.groups, self.selected_group_id), on_result)
    
    @on(Button.Pressed, "#change-priority")
    def on_change_priority(self) -> None:
        def on_result(result: Optional[int]) -> None:
            if result is not None:
                self.selected_priority = result
                self.query_one("#priority-display", Label).update(self._format_priority())
        self.app.push_screen(PriorityPickerModal(self.selected_priority), on_result)
    
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
    
    @on(Button.Pressed, "#select-tags")
    def on_select_tags(self) -> None:
        def on_result(result: Optional[list[int]]) -> None:
            if result is not None:
                self.selected_tag_ids = result
                self.query_one("#tags-display", Label).update(self._format_tags())
        self.app.push_screen(TagPickerModal(self.all_tags, self.selected_tag_ids), on_result)
    
    @on(Button.Pressed, "#manage-comments")
    def on_manage_comments(self) -> None:
        def on_result(updated_comments: list[Comment]) -> None:
            self.comments = updated_comments
            if self.comments:
                self.next_comment_id = max(c.id for c in self.comments) + 1
            self.query_one("#comments-display", Label).update(self._format_comments())
        self.app.push_screen(CommentsModal(self.comments, self.next_comment_id), on_result)
    
    @on(Button.Pressed, "#save")
    def on_save(self) -> None:
        text = self.query_one("#task-input", Input).value.strip()
        if not text:
            self.dismiss(None)
            return
        
        if self.selected_group_id == self.app.GENERAL_GROUP_ID:
            self.app.notify("No se pueden asignar tareas al grupo General", severity="error", timeout=3)
            return
        
        self.dismiss({
            "text": text, 
            "date": self.selected_date,
            "group_id": self.selected_group_id,
            "comments": self.comments,
            "tags": self.selected_tag_ids,
            "priority": self.selected_priority,
            "subtasks": self.subtasks
        } if text else None)
    
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
        Binding("n", "next_month", show=False),
        Binding("p", "prev_month", show=False),
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
            yield Label("←→↑↓: Día | n/p: Mes", classes="hint")
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
        layout: horizontal;
    }
    DayTasksModal .task-item:hover { background: $boost; }
    DayTasksModal .task-item.selected { border: solid $accent; background: $surface-lighten-1; }
    DayTasksModal .task-main { width: 1fr; height: 1; }
    DayTasksModal .task-group { width: auto; height: 1; text-align: right; color: $text-muted; }
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
                item = Horizontal(id=f"task-item-{i}", classes="task-item")
                await tasks_list.mount(item)
                
                await item.mount(Label(f"{checkbox} {task.text}", classes="task-main"))
                
                await item.mount(Label(f"Grupo: {group_name}", classes="task-group"))
                
                if i == 0:
                    item.add_class("selected")
    
    def update_selection(self) -> None:
        for i in range(len(self.tasks)):
            try:
                item = self.query_one(f"#task-item-{i}", Horizontal)
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
        width: 90; height: 26; border: thick $primary;
        background: $surface; padding: 1 2;
    }
    SearchResultsScreen .modal-title { text-align: center; text-style: bold; width: 100%; height: 1; margin-bottom: 1; }
    SearchResultsScreen #results-list { width: 100%; height: 14; overflow-y: auto; }
    SearchResultsScreen .result-item {
        width: 100%; height: 3; padding: 0 1;
        border: solid $primary-background; margin-bottom: 1;
    }
    SearchResultsScreen .result-item:hover { background: $boost; }
    SearchResultsScreen .result-item.selected { border: solid $accent; background: $surface-lighten-1; }
    SearchResultsScreen .hint { width: 100%; height: 1; text-align: center; color: $text-muted; margin: 1 0; }
    SearchResultsScreen .button-row { width: 100%; height: 3; align: center middle; }
    SearchResultsScreen Button { margin: 0 1; }
    """
    BINDINGS = [
        Binding("escape", "cancel", show=False),
        Binding("up", "move_up", show=False),
        Binding("down", "move_down", show=False),
        Binding("k", "move_up", show=False),
        Binding("j", "move_down", show=False),
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
            with Horizontal(classes="button-row"):
                yield Button("Ir al grupo", variant="primary", id="go")
                yield Button("Cancelar", variant="default", id="cancel")
    
    async def on_mount(self) -> None:
        results_list = self.query_one("#results-list", Container)
        for i, (task, group_name) in enumerate(self.results):
            text = task.text[:30] + "..." if len(task.text) > 30 else task.text
            group_text = f"Grupo: {group_name}"
            total_width = 75
            padding = " " * max(1, total_width - len(text) - len(group_text))
            display_text = f"{text}{padding}{group_text}"
            item = Static(display_text, id=f"result-{i}", classes="result-item")
            await results_list.mount(item)
            if i == 0:
                item.add_class("selected")
    
    def scroll_to_selected(self) -> None:
        if self.selected_index >= 0:
            try:
                item = self.query_one(f"#result-{self.selected_index}", Static)
                item.scroll_visible()
            except: pass
    
    def update_selection(self) -> None:
        for i in range(len(self.results)):
            try:
                item = self.query_one(f"#result-{i}", Static)
                item.set_class(i == self.selected_index, "selected")
            except: pass
        self.scroll_to_selected()
    
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
    
    @on(Button.Pressed, "#go")
    def on_go(self) -> None:
        self.action_select_result()
    
    @on(Button.Pressed, "#cancel")
    def on_cancel_btn(self) -> None:
        self.dismiss(None)
    
    def action_cancel(self) -> None:
        self.dismiss(None)

class UnscheduledTasksModal(ModalScreen[Optional[list[int]]]):
    DEFAULT_CSS = """
    UnscheduledTasksModal { align: center middle; }
    UnscheduledTasksModal > Container {
        width: 70; height: 28; border: thick $primary;
        background: $surface; padding: 1 2;
    }
    UnscheduledTasksModal .modal-title { text-align: center; text-style: bold; width: 100%; height: 1; margin-bottom: 1; }
    UnscheduledTasksModal .info-text { width: 100%; text-align: center; color: $text-muted; margin-bottom: 1; }
    UnscheduledTasksModal #tasks-list { width: 100%; height: 14; overflow-y: auto; border: solid $primary-background; padding: 1; }
    UnscheduledTasksModal .task-item {
        width: 100%; height: 3; padding: 0 1;
        border: solid $primary-background; margin-bottom: 1;
    }
    UnscheduledTasksModal .task-item:hover { background: $boost; }
    UnscheduledTasksModal .task-item.selected { border: solid $accent; background: $surface-lighten-1; }
    UnscheduledTasksModal .task-item.checked { color: $success; }
    UnscheduledTasksModal .empty-msg { width: 100%; text-align: center; color: $text-muted; text-style: italic; padding: 2; }
    UnscheduledTasksModal .hint { width: 100%; height: 1; text-align: center; color: $text-muted; margin: 1 0; }
    UnscheduledTasksModal .button-row { width: 100%; height: 3; align: center middle; }
    UnscheduledTasksModal Button { margin: 0 1; }
    """
    BINDINGS = [
        Binding("escape", "cancel", show=False),
        Binding("up", "move_up", show=False),
        Binding("down", "move_down", show=False),
        Binding("k", "move_up", show=False),
        Binding("j", "move_down", show=False),
        Binding("space", "toggle_task", show=False),
        Binding("enter", "save", show=False),
    ]
    
    def __init__(self, unscheduled_tasks: list[Task], all_groups: list[Group], **kwargs) -> None:
        super().__init__(**kwargs)
        self.unscheduled_tasks = unscheduled_tasks
        self.all_groups = all_groups
        self.selected_task_ids: list[int] = []
        self.selected_index = 0 if unscheduled_tasks else -1
    
    def compose(self) -> ComposeResult:
        with Container():
            yield Label("📋 Tareas sin fecha", classes="modal-title")
            yield Label("Selecciona las tareas para asignarles la fecha del calendario", classes="info-text")
            yield Container(id="tasks-list")
            yield Label("↑↓ Navegar | Espacio: Marcar/Desmarcar | Enter: Asignar fecha | Esc: Cancelar", classes="hint")
            with Horizontal(classes="button-row"):
                yield Button("Asignar fecha", variant="primary", id="save")
                yield Button("Cancelar", variant="default", id="cancel")
    
    async def on_mount(self) -> None:
        await self.refresh_list()
    
    async def refresh_list(self) -> None:
        tasks_list = self.query_one("#tasks-list", Container)
        await tasks_list.remove_children()
        
        if not self.unscheduled_tasks:
            await tasks_list.mount(Label("No hay tareas sin fecha pendientes", classes="empty-msg"))
            self.selected_index = -1
        else:
            for i, task in enumerate(self.unscheduled_tasks):
                checked = "☑" if task.id in self.selected_task_ids else "☐"
                
                group_name = "Sin grupo"
                if task.group_id is not None:
                    group = next((g for g in self.all_groups if g.id == task.group_id), None)
                    if group:
                        group_name = group.name
                
                text = task.text[:35] + "..." if len(task.text) > 35 else task.text
                group_text = f"📁 {group_name}"
                
                padding = " " * max(1, 50 - len(text) - len(group_text))
                display_text = f"{checked}  {text}{padding}{group_text}"
                
                item = Static(display_text, id=f"task-{i}", classes="task-item")
                await tasks_list.mount(item)
                if task.id in self.selected_task_ids:
                    item.add_class("checked")
                if i == self.selected_index:
                    item.add_class("selected")
            self.scroll_to_selected()
    
    def scroll_to_selected(self) -> None:
        if self.selected_index >= 0:
            try:
                item = self.query_one(f"#task-{self.selected_index}", Static)
                item.scroll_visible()
            except: pass
    
    def update_selection(self) -> None:
        for i in range(len(self.unscheduled_tasks)):
            try:
                item = self.query_one(f"#task-{i}", Static)
                item.set_class(i == self.selected_index, "selected")
            except: pass
        self.scroll_to_selected()
    
    def action_move_up(self) -> None:
        if self.unscheduled_tasks and self.selected_index > 0:
            self.selected_index -= 1
            self.update_selection()
    
    def action_move_down(self) -> None:
        if self.unscheduled_tasks and self.selected_index < len(self.unscheduled_tasks) - 1:
            self.selected_index += 1
            self.update_selection()
    
    def action_toggle_task(self) -> None:
        if not self.unscheduled_tasks or self.selected_index < 0:
            return
        task = self.unscheduled_tasks[self.selected_index]
        if task.id in self.selected_task_ids:
            self.selected_task_ids.remove(task.id)
        else:
            self.selected_task_ids.append(task.id)
        self.call_later(self.refresh_list)
    
    def action_save(self) -> None:
        self.dismiss(self.selected_task_ids if self.selected_task_ids else None)
    
    @on(Button.Pressed, "#save")
    def on_save_btn(self) -> None:
        self.action_save()
    
    @on(Button.Pressed, "#cancel")
    def on_cancel_btn(self) -> None:
        self.dismiss(None)
    
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

class SortPickerModal(ModalScreen[Optional[dict[str, Optional[str]]]]):
    DEFAULT_CSS = """
    SortPickerModal { align: center middle; }
    SortPickerModal > Container {
        width: 70; height: auto; border: thick $primary;
        background: $surface; padding: 1 2;
    }
    SortPickerModal .modal-title { text-align: center; text-style: bold; width: 100%; height: 1; margin-bottom: 1; }
    SortPickerModal .info-text { width: 100%; text-align: center; color: $text-muted; margin-bottom: 1; }
    SortPickerModal .category-title { 
        width: 100%; text-align: left; 
        text-style: bold; color: $accent;
        margin: 1 0; padding: 0 1;
    }
    SortPickerModal #sort-list { width: 100%; height: auto; max-height: 20; overflow-y: auto; padding: 1; }
    SortPickerModal .sort-item {
        width: 100%; height: 3; padding: 0 2;
        border: solid $primary-background; margin-bottom: 1;
    }
    SortPickerModal .sort-item:hover { background: $boost; }
    SortPickerModal .sort-item.selected { border: solid $accent; background: $surface-lighten-1; }
    SortPickerModal .sort-item.checked { color: $success; }
    SortPickerModal .hint { width: 100%; height: 1; text-align: center; color: $text-muted; margin: 1 0; }
    SortPickerModal .button-row { width: 100%; height: 3; align: center middle; }
    SortPickerModal Button { margin: 0 1; }
    """
    BINDINGS = [
        Binding("escape", "cancel", show=False),
        Binding("up", "move_up", show=False),
        Binding("down", "move_down", show=False),
        Binding("k", "move_up", show=False),
        Binding("j", "move_down", show=False),
        Binding("space", "toggle_sort", show=False),
        Binding("enter", "save", show=False),
    ]
    
    def __init__(self, current_criteria: dict[str, Optional[str]], **kwargs) -> None:
        super().__init__(**kwargs)
        self.criteria = {
            "alphabetical": current_criteria.get("alphabetical"),
            "date": current_criteria.get("date"),
            "priority": current_criteria.get("priority")
        }
        
        self.flat_options = [
            ("alphabetical", "alpha_asc"),
            ("alphabetical", "alpha_desc"),
            ("date", "date_asc"),
            ("date", "date_desc"),
            ("priority", "priority_desc"),
            ("priority", "priority_asc")
        ]
        self.selected_index = 0
    
    def compose(self) -> ComposeResult:
        with Container():
            yield Label("📊 Ordenar Tareas", classes="modal-title")
            yield Label("Prioridad: Prioridad → Fecha → Alfabético", classes="info-text")
            yield Container(id="sort-list")
            yield Label("↑↓ Navegar | Espacio: Seleccionar | Enter: Guardar | Esc: Cancelar", classes="hint")
            with Horizontal(classes="button-row"):
                yield Button("Guardar", variant="primary", id="save")
                yield Button("Limpiar todo", variant="warning", id="clear")
    
    async def on_mount(self) -> None:
        await self.refresh_list()
    
    async def refresh_list(self) -> None:
        sort_list = self.query_one("#sort-list", Container)
        await sort_list.remove_children()
        
        await sort_list.mount(Static("🔤 Alfabético:", classes="category-title"))
        
        alpha_options = [
            ("  A → Z", "alphabetical", "alpha_asc", 0),
            ("  Z → A", "alphabetical", "alpha_desc", 1)
        ]
        
        for text, category, value, idx in alpha_options:
            checked = "☑" if self.criteria.get(category) == value else "☐"
            display_text = f"{checked} {text}"
            item = Static(display_text, id=f"sort-{idx}", classes="sort-item")
            await sort_list.mount(item)
            if self.criteria.get(category) == value:
                item.add_class("checked")
            if idx == self.selected_index:
                item.add_class("selected")
        
        await sort_list.mount(Static("📅 Fecha:", classes="category-title"))
        
        date_options = [
            ("  Más próximas primero ↑", "date", "date_asc", 2),
            ("  Más lejanas primero ↓", "date", "date_desc", 3)
        ]
        
        for text, category, value, idx in date_options:
            checked = "☑" if self.criteria.get(category) == value else "☐"
            display_text = f"{checked} {text}"
            item = Static(display_text, id=f"sort-{idx}", classes="sort-item")
            await sort_list.mount(item)
            if self.criteria.get(category) == value:
                item.add_class("checked")
            if idx == self.selected_index:
                item.add_class("selected")
        
        await sort_list.mount(Static("⭐ Prioridad:", classes="category-title"))
        
        priority_options = [
            ("  Alta → Baja", "priority", "priority_desc", 4),
            ("  Baja → Alta", "priority", "priority_asc", 5)
        ]
        
        for text, category, value, idx in priority_options:
            checked = "☑" if self.criteria.get(category) == value else "☐"
            display_text = f"{checked} {text}"
            item = Static(display_text, id=f"sort-{idx}", classes="sort-item")
            await sort_list.mount(item)
            if self.criteria.get(category) == value:
                item.add_class("checked")
            if idx == self.selected_index:
                item.add_class("selected")
    
    def scroll_to_selected(self) -> None:
        if self.selected_index >= 0:
            try:
                item = self.query_one(f"#sort-{self.selected_index}", Static)
                item.scroll_visible()
            except: pass
    
    def update_selection(self) -> None:
        for i in range(len(self.flat_options)):
            try:
                item = self.query_one(f"#sort-{i}", Static)
                item.set_class(i == self.selected_index, "selected")
            except: pass
        self.scroll_to_selected()
    
    def action_move_up(self) -> None:
        if self.selected_index > 0:
            self.selected_index -= 1
            self.update_selection()
    
    def action_move_down(self) -> None:
        if self.selected_index < len(self.flat_options) - 1:
            self.selected_index += 1
            self.update_selection()
    
    def action_toggle_sort(self) -> None:
        if self.selected_index < 0 or self.selected_index >= len(self.flat_options):
            return
        
        category, value = self.flat_options[self.selected_index]
        
        if self.criteria.get(category) == value:
            self.criteria[category] = None
        else:
            self.criteria[category] = value
        
        self.call_later(self.refresh_list)
    
    def action_save(self) -> None:
        self.dismiss(self.criteria)
    
    @on(Button.Pressed, "#save")
    def on_save_btn(self) -> None:
        self.action_save()
    
    @on(Button.Pressed, "#clear")
    def on_clear_btn(self) -> None:
        self.dismiss({"alphabetical": None, "date": None, "priority": None})
    
    @on(Button.Pressed, "#cancel")
    def on_cancel_btn(self) -> None:
        self.dismiss(None)
    
    def action_cancel(self) -> None:
        self.dismiss(None)

class TodoApp(App):
    CSS = """
    Screen { background: $background; }
    Header {
        background: #1e1e1e;
        color: #00ff00;  /* Verde terminal */
    }
    Header .header--title {
        color: #00ff00;
        text-style: bold;
    }
    #main-container { width: 100%; height: 1fr; padding: 0 2; }
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
        Binding("f", "filter_tasks", "Filtrar"),
        Binding("f5", "reset_filters", "Reset Filtros", show=True),
        Binding("o", "sort_tasks", "Ordenar"),
        Binding("g", "new_group", "Nuevo Grupo"),
        Binding("G", "group_options", "Opc. Grupo"),
        Binding("T", "manage_tags", "Etiquetas"),
        Binding("c", "toggle_calendar", "Calendario"),
        Binding("i", "today_tasks", "Hoy"),
        Binding("/", "search", "Buscar"),
        Binding("escape", "handle_escape", show=False),
        Binding("left", "nav_left", show=False),
        Binding("right", "nav_right", show=False),
        Binding("up", "nav_up", show=False),
        Binding("down", "nav_down", show=False),
        Binding("h", "nav_left", show=False),
        Binding("l", "nav_right", show=False),
        Binding("k", "nav_up", show=False),
        Binding("j", "nav_down", show=False),
        Binding("n", "next_month", "Mes sig.", show=False),
        Binding("p", "prev_month", "Mes ant.", show=False),
        Binding("t", "go_today", show=False),
        Binding("space", "toggle_done", "Completar"),
        Binding("enter", "action_enter", show=False),
        Binding("q", "quit", "Salir"),
        Binding("ctrl+z", "undo", "Deshacer"),
        Binding("ctrl+y", "redo", "Rehacer"),
    ]
    
    TITLE = "MyTaskit"
    theme = "dracula"
    
    def __init__(self) -> None:
        super().__init__()
        self.tasks: list[Task] = []
        self.groups: list[Group] = []
        self.tags: list[Tag] = []
        self.next_task_id = 1
        self.next_group_id = 1
        self.next_tag_id = 1
        self.next_subtask_id = 1 
        self.selected_index = 0
        self.GENERAL_GROUP_ID = -1
        self.current_group_id: Optional[int] = self.GENERAL_GROUP_ID
        self.data_file = Path.home() / "todo" / "todo_tasks.json"
        self.data_file.parent.mkdir(exist_ok=True)
        
        self.calendar_mode = False
        self.cal_year = date.today().year
        self.cal_month = date.today().month
        self.cal_day = date.today().day
        
        self.filter_dates: list[str] = []
        self.filter_tag_ids: list[int] = []
        self.filter_statuses: list[str] = []
        self.filter_priorities: list[int] = []
        
        self.sort_criteria: dict[str, Optional[str]] = {
            "alphabetical": None,
            "date": None,
            "priority": None
        }
        
        self.save_lock = Lock()
        
        self.undo_stack: list[dict] = []
        self.redo_stack: list[dict] = []
        self.max_undo = 50
        
        self.load_data()
    
    def action_reset_filters(self) -> None:
        self.filter_dates = []
        self.filter_tag_ids = []
        self.filter_statuses = []
        self.filter_priorities = []
        self.selected_index = 0
        self.refresh_view()
        self.update_stats()
        self.notify("🔄 Filtros reseteados", severity="information", timeout=2)
    
    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="main-container"):
            yield Horizontal(id="tabs-container")
            yield Container(id="task-list")
            with Container(id="calendar-view"):
                yield Static("", id="calendar-header")
                yield Static("", id="calendar-display")
                yield Static("", id="calendar-day-tasks")
                yield Static("←→↑↓: Navegar | n/p: Mes | t: Hoy | a: Asignar | Enter: Ver tareas | Esc: Volver", id="calendar-hint")
            yield Static("", id="stats")
        yield Footer()
    
    async def on_mount(self) -> None:
        await self.refresh_tabs()
        await self.refresh_view()
        self.update_stats()
        self.set_timer(0.1, self.show_today_reminders)
        self.set_interval(10, self.save_data)

    def on_exit(self) -> None:
        self.save_data()

    def action_today_tasks(self) -> None:
        today = date.today()
        tasks, subtasks = self._get_tasks_for_date(today.year, today.month, today.day)
        date_str = f"{today.day}/{today.month}/{today.year}"
        
        def on_result(result):
            if result:
                item_type, item_obj = result
                self._go_to_task(item_obj)
        
        self.push_screen(DayItemsModal(tasks, subtasks, date_str), on_result)
    
    def show_today_reminders(self) -> None:
        today_str = date.today().strftime("%Y-%m-%d")
        today_tasks = []
        today_subtasks = []
        
        for task in self.tasks:
            if task.due_date == today_str and not task.done:
                if task.group_id is None:
                    group_name = "Sin grupo"
                else:
                    group = next((g for g in self.groups if g.id == task.group_id), None)
                    group_name = group.name if group else "Sin grupo"
                today_tasks.append((task, group_name))
            
            for subtask in task.subtasks:
                if subtask.due_date == today_str and not subtask.done:
                    if task.group_id is None:
                        group_name = "Sin grupo"
                    else:
                        group = next((g for g in self.groups if g.id == task.group_id), None)
                        group_name = group.name if group else "Sin grupo"
                    parent_info = f"{task.text[:30]}..." if len(task.text) > 30 else task.text
                    today_subtasks.append((subtask, parent_info, group_name))
        
        all_reminders = []
        
        for task, group_name in today_tasks:
            all_reminders.append(("task", task, group_name, None))
        
        for subtask, parent_info, group_name in today_subtasks:
            all_reminders.append(("subtask", subtask, group_name, parent_info))
        
        def show_next(index=0):
            if index < len(all_reminders):
                item_type, item_obj, group_name, parent_info = all_reminders[index]
                
                def on_close(result):
                    show_next(index + 1)
                
                if item_type == "task":
                    self.push_screen(ReminderModal(item_obj, group_name), on_close)
                else:
                    self.push_screen(SubtaskReminderModal(item_obj, parent_info, group_name), on_close)
        
        show_next()
    
    async def refresh_tabs(self) -> None:
        tabs = self.query_one("#tabs-container", Horizontal)
        await tabs.remove_children()
        
        if self.calendar_mode:
            tab = GroupTab(None, "📅 Calendario", id="tab-calendar")
            await tabs.mount(tab)
            tab.active = True
        else:
            tab = GroupTab(self.GENERAL_GROUP_ID, "📚 General", id="tab-general")
            await tabs.mount(tab)
            tab.active = (self.current_group_id == self.GENERAL_GROUP_ID)
            
            tab = GroupTab(None, "📋 Sin grupo", id="tab-all")
            await tabs.mount(tab)
            tab.active = (self.current_group_id is None)
            
            for g in self.groups:
                icon = "📂" if self.current_group_id == g.id else "📁"
                t = GroupTab(g.id, f"{icon} {g.name}", id=f"tab-{g.id}")
                await tabs.mount(t)
                t.active = (self.current_group_id == g.id)
    
    def _get_current_tasks(self) -> list[Task]:
        if self.current_group_id == self.GENERAL_GROUP_ID:
            tasks = list(self.tasks)
        elif self.current_group_id is None:
            tasks = [t for t in self.tasks if t.group_id is None]
        else:
            tasks = [t for t in self.tasks if t.group_id == self.current_group_id]
        
        if self.filter_dates:
            filtered = []
            for t in tasks:
                for filter_date in self.filter_dates:
                    if filter_date == "none" and t.due_date is None:
                        filtered.append(t)
                        break
                    elif t.due_date == filter_date:
                        filtered.append(t)
                        break
            tasks = filtered
        
        if self.filter_tag_ids:
            tasks = [t for t in tasks if all(tag_id in t.tags for tag_id in self.filter_tag_ids)]
        
        if self.filter_statuses:
            filtered = []
            for t in tasks:
                for status in self.filter_statuses:
                    if (status == "completed" and t.done) or (status == "pending" and not t.done):
                        filtered.append(t)
                        break
            tasks = filtered
        
        if self.filter_priorities:
            tasks = [t for t in tasks if t.priority in self.filter_priorities]
        
        return tasks
    
    def _get_tasks_for_date(self, y: int, m: int, d: int) -> tuple[list[tuple], list[tuple]]:
        date_str = f"{y:04d}-{m:02d}-{d:02d}"
        
        tasks_result = []
        subtasks_result = []
        
        for t in self.tasks:
            if t.due_date == date_str:
                if t.group_id is None:
                    gname = "Sin grupo"
                else:
                    g = next((x for x in self.groups if x.id == t.group_id), None)
                    gname = g.name if g else "Sin grupo"
                tasks_result.append((t, gname))
            
            for subtask in t.subtasks:
                if subtask.due_date == date_str:
                    if t.group_id is None:
                        gname = "Sin grupo"
                    else:
                        g = next((x for x in self.groups if x.id == t.group_id), None)
                        gname = g.name if g else "Sin grupo"
                    subtasks_result.append((subtask, t, gname))
        
        return tasks_result, subtasks_result
    
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
            await task_list.remove_children()
            await self._refresh_task_list(task_list)
    
    async def _refresh_task_list(self, task_list: Container) -> None:
        ordered = self._get_ordered_tasks()
        pending = [t for t in ordered if not t.done]
        completed = [t for t in ordered if t.done]
        
        if not ordered:
            msg = "No hay tareas. Pulsa 'a' para añadir una."
            await task_list.mount(Label(msg, id="empty-message"))
        else:
            for t in pending:
                w = TaskWidget(t, all_tags=self.tags, all_groups=self.groups, id=f"task-{t.id}")
                await task_list.mount(w)
            if completed:
                await task_list.mount(Static("── Completadas ──", id="completed-separator"))
                for t in completed:
                    w = TaskWidget(t, all_tags=self.tags, all_groups=self.groups, id=f"task-{t.id}")
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
                    date_str = current.strftime("%Y-%m-%d")
                    
                    has_tasks = any(t.due_date == date_str for t in self.tasks)
                    has_subtasks = any(
                        any(st.due_date == date_str for st in t.subtasks)
                        for t in self.tasks
                    )
                    
                    if day == self.cal_day:
                        week_str += f"[bold cyan][{day:2d}][/bold cyan]"
                    elif current == today:
                        if has_tasks and has_subtasks:
                            week_str += f"[bold #D2B48C]{day:2d}◆[/bold #D2B48C]"
                        elif has_subtasks:
                            week_str += f"[bold #FFA500]{day:2d}▪[/bold #FFA500]"
                        elif has_tasks:
                            week_str += f"[bold green]{day:2d}•[/bold green]"
                        else:
                            week_str += f"[bold green] {day:2d} [/bold green]"
                    else:
                        if has_tasks and has_subtasks:
                            week_str += f"[#D2B48C]{day:2d}◆[/#D2B48C]"
                        elif has_subtasks:
                            week_str += f"[#FFA500]{day:2d}▪[/#FFA500]"
                        elif has_tasks:
                            week_str += f"[yellow]{day:2d}•[/yellow]"
                        else:
                            week_str += f" {day:2d} "
            lines.append(week_str)
        
        self.query_one("#calendar-display", Static).update("\n".join(lines))
        
        tasks, subtasks = self._get_tasks_for_date(self.cal_year, self.cal_month, self.cal_day)
        day_tasks = self.query_one("#calendar-day-tasks", Static)
        
        total_items = len(tasks) + len(subtasks)
        
        if total_items > 0:
            lines = [f"📋 {len(tasks)} tarea(s) | 📝 {len(subtasks)} subtarea(s):"]
            
            for t, gname in tasks[:2]:
                cb = "☑" if t.done else "☐"
                txt = t.text[:30] + "..." if len(t.text) > 30 else t.text
                group_text = f"📁 {gname}"
                padding = " " * max(1, 45 - len(txt) - len(group_text))
                lines.append(f"  {cb} {txt}{padding}{group_text}")
            
            for st, parent, gname in subtasks[:2]:
                cb = "☑" if st.done else "☐"
                txt = st.text[:25] + "..." if len(st.text) > 25 else st.text
                parent_txt = parent.text[:15] + "..." if len(parent.text) > 15 else parent.text
                lines.append(f"  {cb} ↳ {txt} 🔗 {parent_txt}")
            
            if total_items > 4:
                lines.append(f"  ... y {total_items - 4} más")
            
            day_tasks.update("\n".join(lines))
        else:
            day_tasks.update("No hay tareas ni subtareas para este día")
    
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
        pending = [t for t in c if not t.done]
        completed = [t for t in c if t.done]
        
        alpha_criterion = self.sort_criteria.get("alphabetical")
        if alpha_criterion == "alpha_asc":
            pending.sort(key=lambda t: t.text.lower())
            completed.sort(key=lambda t: t.text.lower())
        elif alpha_criterion == "alpha_desc":
            pending.sort(key=lambda t: t.text.lower(), reverse=True)
            completed.sort(key=lambda t: t.text.lower(), reverse=True)
        
        date_criterion = self.sort_criteria.get("date")
        if date_criterion == "date_asc":
            pending_with = [t for t in pending if t.due_date]
            pending_without = [t for t in pending if not t.due_date]
            pending_with.sort(key=lambda t: t.due_date)
            pending = pending_with + pending_without
            
            completed_with = [t for t in completed if t.due_date]
            completed_without = [t for t in completed if not t.due_date]
            completed_with.sort(key=lambda t: t.due_date)
            completed = completed_with + completed_without
        elif date_criterion == "date_desc":
            pending_with = [t for t in pending if t.due_date]
            pending_without = [t for t in pending if not t.due_date]
            pending_with.sort(key=lambda t: t.due_date, reverse=True)
            pending = pending_with + pending_without
            
            completed_with = [t for t in completed if t.due_date]
            completed_without = [t for t in completed if not t.due_date]
            completed_with.sort(key=lambda t: t.due_date, reverse=True)
            completed = completed_with + completed_without
        
        priority_criterion = self.sort_criteria.get("priority")
        if priority_criterion == "priority_desc":
            pending.sort(key=lambda t: t.priority, reverse=True)
            completed.sort(key=lambda t: t.priority, reverse=True)
        elif priority_criterion == "priority_asc":
            pending.sort(key=lambda t: t.priority)
            completed.sort(key=lambda t: t.priority)
        
        return pending + completed
    
    def update_selection(self) -> None:
        ordered = self._get_ordered_tasks()
        if not ordered:
            self.selected_index = 0
            return
        self.selected_index = max(0, min(self.selected_index, len(ordered) - 1))
        for i, t in enumerate(ordered):
            try:
                self.query_one(f"#task-{t.id}", TaskWidget).selected = (i == self.selected_index)
            except: pass
    
    def update_stats(self) -> None:
        if self.calendar_mode:
            tasks, subtasks = self._get_tasks_for_date(self.cal_year, self.cal_month, self.cal_day)
            total_tasks = len(tasks)
            total_subtasks = len(subtasks)
            done_tasks = sum(1 for t, _ in tasks if t.done)
            done_subtasks = sum(1 for st, _, _ in subtasks if st.done)
            text = f"📅 {self.cal_day}/{self.cal_month}/{self.cal_year} | Tareas: {total_tasks} ({done_tasks} ✓) | Subtareas: {total_subtasks} ({done_subtasks} ✓)"
        else:
            c = self._get_current_tasks()
            total, done = len(c), sum(1 for t in c if t.done)
            
            if self.current_group_id == self.GENERAL_GROUP_ID:
                gname = "General"
            elif self.current_group_id is None:
                gname = "Sin grupo"
            else:
                g = next((x for x in self.groups if x.id == self.current_group_id), None)
                gname = g.name if g else "Sin grupo"
            
            text = f"Total: {total} | Completadas: {done} | Pendientes: {total - done} | Grupo: {gname}"
            
            sort_parts = []
            sort_names = {
                "alpha_asc": "A→Z",
                "alpha_desc": "Z→A",
                "date_asc": "Fecha↑",
                "date_desc": "Fecha↓",
                "priority_desc": "Pri↓",
                "priority_asc": "Pri↑"
            }
            
            if self.sort_criteria.get("priority"):
                sort_parts.append(sort_names.get(self.sort_criteria["priority"], ""))
            if self.sort_criteria.get("date"):
                sort_parts.append(sort_names.get(self.sort_criteria["date"], ""))
            if self.sort_criteria.get("alphabetical"):
                sort_parts.append(sort_names.get(self.sort_criteria["alphabetical"], ""))
            
            if sort_parts:
                text += f" | Orden: {' → '.join(sort_parts)}"
            else:
                text += " | Orden: Creación"
            
            filters = []
            
            if self.filter_dates:
                date_strs = []
                for fd in self.filter_dates:
                    if fd == "none":
                        date_strs.append("Sin fecha")
                    else:
                        try:
                            d = datetime.strptime(fd, "%Y-%m-%d")
                            date_strs.append(f"{d.day:02d}/{d.month:02d}")
                        except: pass
                if date_strs:
                    filters.append(f"📅 {', '.join(date_strs)}")
            
            if self.filter_tag_ids:
                tag_names = []
                for tag_id in self.filter_tag_ids:
                    tag = next((t for t in self.tags if t.id == tag_id), None)
                    if tag:
                        tag_names.append(tag.name)
                if tag_names:
                    filters.append(f"🏷️ {', '.join(tag_names)}")
            
            if self.filter_statuses:
                status_names = []
                for status in self.filter_statuses:
                    if status == "completed":
                        status_names.append("Completadas")
                    elif status == "pending":
                        status_names.append("Pendientes")
                if status_names:
                    filters.append(f"✅ {', '.join(status_names)}")
            
            if self.filter_priorities:
                priority_names = {0: "Sin prioridad", 1: "■ Baja", 2: "■ Media", 3: "■ Alta"}
                priority_strs = [priority_names.get(p, '') for p in self.filter_priorities]
                if priority_strs:
                    filters.append(f"⭐ {', '.join(priority_strs)}")
            
            if filters:
                text += " | Filtros: " + ", ".join(filters)

        self.query_one("#stats", Static).update(text)

        self.query_one("#stats", Static).update(text)
    
    def get_selected_widget(self) -> Optional[TaskWidget]:
        ordered = self._get_ordered_tasks()
        if not ordered or self.selected_index >= len(ordered): return None
        try: return self.query_one(f"#task-{ordered[self.selected_index].id}", TaskWidget)
        except: return None
    
    def action_quit(self) -> None:
        self.save_data()
        self.exit()
    
    async def action_handle_escape(self) -> None:
        if self.calendar_mode:
            self.calendar_mode = False
            await self.refresh_tabs()
            await self.refresh_view()
            self.update_stats()
    
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
        ids = [self.GENERAL_GROUP_ID, None] + [g.id for g in self.groups]
        idx = (ids.index(self.current_group_id) - 1) % len(ids)
        self.current_group_id = ids[idx]
        self.selected_index = 0
        await self.refresh_tabs()
        await self.refresh_view()
        self.update_stats()

    async def _next_group(self) -> None:
        ids = [self.GENERAL_GROUP_ID, None] + [g.id for g in self.groups]
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
            tasks, subtasks = self._get_tasks_for_date(self.cal_year, self.cal_month, self.cal_day)
            date_str = f"{self.cal_day}/{self.cal_month}/{self.cal_year}"
            
            def on_result(result):
                if result:
                    item_type, item_obj = result
                    self._go_to_task(item_obj)
            
            self.push_screen(DayItemsModal(tasks, subtasks, date_str), on_result)
        else:
            self.action_toggle_done()
    
    async def action_toggle_done(self) -> None:
        if not self.calendar_mode:
            w = self.get_selected_widget()
            if w:
                self._save_undo_state()
                w.toggle_done()
                self.save_data()
                self.update_stats()
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
                self.notify(f"No se encontraron tareas para '{query}'", severity="error", timeout=3)
            elif len(results) == 1:
                self._go_to_task(results[0][0])
            else:
                self.push_screen(SearchResultsScreen(results, query), lambda t: self._go_to_task(t) if t else None)
        self.push_screen(InputModal("🔍 Buscar", placeholder="Buscar tareas..."), on_input)
    
    def action_assign_tasks_from_calendar(self) -> None:
        if not self.calendar_mode:
            return
        
        has_unscheduled = any(
            (t.due_date is None and not t.done) or
            any(st.due_date is None and not st.done for st in t.subtasks)
            for t in self.tasks
        )
        
        if not has_unscheduled:
            self.notify("No hay tareas ni subtareas sin fecha para asignar", severity="information", timeout=3)
            return
        
        async def on_result(result: Optional[dict]) -> None:
            if result:
                self._save_undo_state()
                selected_date = f"{self.cal_year:04d}-{self.cal_month:02d}-{self.cal_day:02d}"
                
                task_ids = result.get("task_ids", [])
                subtask_selections = result.get("subtask_selections", [])
                
                for task in self.tasks:
                    if task.id in task_ids:
                        task.due_date = selected_date
                
                for task in self.tasks:
                    for subtask in task.subtasks:
                        if (task.id, subtask.id) in subtask_selections:
                            subtask.due_date = selected_date
                
                count = len(task_ids) + len(subtask_selections)
                if count > 0:
                    self.save_data()
                    self.refresh_calendar()
                    self.update_stats()
                    self.notify(f"📅 {count} elemento(s) asignado(s) (Ctrl+Z para deshacer)", 
                            severity="information", timeout=2)
        
        self.push_screen(UnscheduledItemsModal(self.tasks, self.groups), on_result)
    
    def action_filter_tasks(self) -> None:
        if self.calendar_mode: return
        
        if self.current_group_id == self.GENERAL_GROUP_ID:
            group_tasks = list(self.tasks)
        elif self.current_group_id is None:
            group_tasks = [t for t in self.tasks if t.group_id is None]
        else:
            group_tasks = [t for t in self.tasks if t.group_id == self.current_group_id]
        
        available_dates = [t.due_date for t in group_tasks if t.due_date]
        
        async def on_result(result: Optional[dict]) -> None:
            if result is not None:
                self.filter_dates = result.get("dates", [])
                self.filter_tag_ids = result.get("tags", [])
                self.filter_statuses = result.get("statuses", [])
                self.filter_priorities = result.get("priorities", [])
                self.selected_index = 0
                await self.refresh_view()
                self.update_stats()
        
        self.push_screen(
            FilterModal(
                self.filter_dates,
                self.filter_tag_ids,
                self.filter_statuses,
                self.filter_priorities,
                self.tags,
                available_dates
            ),
            on_result
        )
    
    def action_sort_tasks(self) -> None:
        if self.calendar_mode:
            return
        
        async def on_result(sort_criteria: Optional[dict[str, Optional[str]]]) -> None:
            if sort_criteria is not None:
                self.sort_criteria = sort_criteria
                self.selected_index = 0
                await self.refresh_view()
                self.update_stats()
        
        self.push_screen(SortPickerModal(self.sort_criteria), on_result)
    
    def action_new_group(self) -> None:
        if self.calendar_mode: return
        async def on_result(name: Optional[str]) -> None:
            if name:
                self._save_undo_state()
                g = Group(id=self.next_group_id, name=name)
                self.next_group_id += 1
                self.groups.append(g)
                self.current_group_id = g.id
                self.selected_index = 0
                await self.refresh_tabs()
                await self.refresh_view()
                self.update_stats()
                self.save_data()
                self.notify("📁 Grupo creado (Ctrl+Z para deshacer)", severity="information", timeout=2)
        self.push_screen(InputModal("Nuevo Grupo", placeholder="Nombre..."), on_result)
    
    def action_group_options(self) -> None:
        if self.calendar_mode or self.current_group_id is None or self.current_group_id == self.GENERAL_GROUP_ID:
            return
        g = next((x for x in self.groups if x.id == self.current_group_id), None)
        if not g: return
        
        async def on_opt(opt: str) -> None:
            if opt == "rename":
                def on_name(name: Optional[str]) -> None:
                    if name:
                        self._save_undo_state()
                        g.name = name
                        self.call_later(self._after_rename)
                        self.notify("✏️ Grupo renombrado (Ctrl+Z para deshacer)", severity="information", timeout=2)
                self.push_screen(InputModal("Renombrar", initial_text=g.name), on_name)
            elif opt == "delete":
                count = len([t for t in self.tasks if t.group_id == g.id])
                async def on_confirm(yes: bool) -> None:
                    if yes:
                        self._save_undo_state()
                        self.tasks = [t for t in self.tasks if t.group_id != g.id]
                        self.groups.remove(g)
                        self.current_group_id = None
                        self.selected_index = 0
                        await self.refresh_tabs()
                        await self.refresh_view()
                        self.update_stats()
                        self.save_data()
                        self.notify(f"🗑️ Grupo eliminado con {count} tareas (Ctrl+Z para deshacer)", 
                                severity="information", timeout=2)
                self.push_screen(ConfirmModal(f"¿Eliminar '{g.name}' y sus {count} tareas?"), on_confirm)
        self.push_screen(GroupOptionsModal(g.name), on_opt)
    
    async def _after_rename(self) -> None:
        await self.refresh_tabs()
        self.update_stats()
        self.save_data()
    
    def action_manage_comments(self) -> None:
        if not self.subtasks or self.selected_index < 0:
            return
        subtask = self.subtasks[self.selected_index]
        
        next_comment_id = self.next_comment_id
        if subtask.comments:
            next_comment_id = max(c.id for c in subtask.comments) + 1
        
        def on_result(updated_comments: list[Comment]) -> None:
            subtask.comments = updated_comments
            if subtask.comments:
                self.next_comment_id = max(c.id for c in subtask.comments) + 1
            self.call_later(self.refresh_subtasks_list)
        
        self.app.push_screen(CommentsModal(subtask.comments, next_comment_id), on_result)
    
    def action_add_task(self) -> None:
        if self.calendar_mode:
            self.action_assign_tasks_from_calendar()
            return
        
        if self.current_group_id == self.GENERAL_GROUP_ID:
            self.notify("No se pueden crear tareas en General. Cambia a un grupo específico.", severity="error", timeout=3)
            return
        
        async def on_result(text: Optional[str]) -> None:
            if text:
                self._save_undo_state()
                t = Task(id=self.next_task_id, text=text, group_id=self.current_group_id)
                self.next_task_id += 1
                self.tasks.append(t)
                pending = [x for x in self._get_current_tasks() if not x.done]
                self.selected_index = len(pending) - 1
                await self.refresh_view()
                self.update_stats()
                self.save_data()
                self.notify("✅ Tarea creada (Ctrl+Z para deshacer)", severity="information", timeout=2)
        self.push_screen(InputModal("Nueva Tarea", placeholder="Escribe la tarea..."), on_result)
    
    def action_edit_task(self) -> None:
        if self.calendar_mode: return
        w = self.get_selected_widget()
        if not w: return
        t = w.task_data
        next_comment_id = 1
        if t.comments:
            next_comment_id = max(c.id for c in t.comments) + 1
        
        next_subtask_id = 1
        if t.subtasks:
            next_subtask_id = max(s.id for s in t.subtasks) + 1
        
        async def on_result(result: Optional[dict]) -> None:
            if result:
                self._save_undo_state()
                t.text = result["text"]
                t.due_date = result["date"]
                t.comments = result.get("comments", [])
                t.tags = result.get("tags", [])
                t.priority = result.get("priority", 0)
                t.subtasks = result.get("subtasks", [])
                old_group_id = t.group_id
                new_group_id = result.get("group_id")
                t.group_id = new_group_id
                self.save_data()
                if old_group_id != new_group_id:
                    self.current_group_id = new_group_id
                    self.selected_index = 0
                    await self.refresh_tabs()
                await self.refresh_view()
                self.update_stats()
                for i, task in enumerate(self._get_ordered_tasks()):
                    if task.id == t.id:
                        self.selected_index = i
                        break
                self.update_selection()
                self.notify("✏️ Tarea editada (Ctrl+Z para deshacer)", severity="information", timeout=2)
        
        self.push_screen(EditTaskModal(t.text, t.due_date, t.group_id, self.groups, 
                                    t.comments, next_comment_id, self.tags, t.tags, 
                                    t.priority, t.subtasks, next_subtask_id), on_result)
        
    def action_delete_task(self) -> None:
        if self.calendar_mode: return
        ordered = self._get_ordered_tasks()
        if not ordered: return
        t = ordered[self.selected_index]
        
        async def on_confirm(yes: bool) -> None:
            if yes:
                self._save_undo_state()
                self.tasks.remove(t)
                if self.selected_index >= len(self._get_ordered_tasks()) and self.selected_index > 0:
                    self.selected_index -= 1
                await self.refresh_view()
                self.update_stats()
                self.save_data()
                self.notify("🗑️ Tarea eliminada (Ctrl+Z para deshacer)", severity="information", timeout=2)
        txt = t.text[:30] + "..." if len(t.text) > 30 else t.text
        self.push_screen(ConfirmModal(f"¿Eliminar '{txt}'?"), on_confirm)
        
    def _capture_state(self) -> dict:
        return {
            "next_task_id": self.next_task_id,
            "next_group_id": self.next_group_id,
            "next_tag_id": self.next_tag_id,
            "next_subtask_id": self.next_subtask_id,
            "current_group_id": self.current_group_id,
            "selected_index": self.selected_index,
            "groups": [{"id": g.id, "name": g.name} for g in self.groups],
            "tags": [{"id": t.id, "name": t.name} for t in self.tags],
            "tasks": [{
                "id": t.id,
                "text": t.text,
                "done": t.done,
                "created_at": t.created_at,
                "group_id": t.group_id,
                "due_date": t.due_date,
                "comments": [{
                    "id": c.id, 
                    "text": c.text, 
                    "url": c.url, 
                    "image_path": c.image_path, 
                    "created_at": c.created_at
                } for c in t.comments],
                "tags": list(t.tags),
                "priority": t.priority,
                "subtasks": [{
                    "id": s.id, 
                    "text": s.text, 
                    "done": s.done,
                    "created_at": s.created_at, 
                    "due_date": s.due_date,
                    "comments": [{
                        "id": c.id, 
                        "text": c.text, 
                        "url": c.url,
                        "image_path": c.image_path, 
                        "created_at": c.created_at
                    } for c in s.comments]
                } for s in t.subtasks]
            } for t in self.tasks]
        }

    def _save_undo_state(self) -> None:
        state = self._capture_state()
        self.undo_stack.append(state)
        
        self.redo_stack.clear()
        
        if len(self.undo_stack) > self.max_undo:
            self.undo_stack.pop(0)

    def _restore_state(self, state: dict) -> None:
        self.next_task_id = state["next_task_id"]
        self.next_group_id = state["next_group_id"]
        self.next_tag_id = state["next_tag_id"]
        self.next_subtask_id = state.get("next_subtask_id", 1)
        self.current_group_id = state["current_group_id"]
        self.selected_index = state["selected_index"]
        
        self.groups = [Group(id=g["id"], name=g["name"]) for g in state["groups"]]
        
        self.tags = [Tag(id=t["id"], name=t["name"]) for t in state["tags"]]
        
        self.tasks = []
        for t in state["tasks"]:
            comments = [Comment(
                id=c["id"], 
                text=c["text"], 
                url=c.get("url"), 
                image_path=c.get("image_path"),
                created_at=c.get("created_at", "")
            ) for c in t["comments"]]
            
            subtasks = []
            for s in t.get("subtasks", []):
                subtask_comments = [Comment(
                    id=c["id"], 
                    text=c["text"], 
                    url=c.get("url"),
                    image_path=c.get("image_path"),
                    created_at=c.get("created_at", "")
                ) for c in s.get("comments", [])]
                
                subtask = Subtask(
                    id=s["id"], 
                    text=s["text"], 
                    done=s.get("done", False),
                    created_at=s.get("created_at", ""),
                    due_date=s.get("due_date"),
                    comments=subtask_comments
                )
                subtasks.append(subtask)
            
            task = Task(
                id=t["id"],
                text=t["text"],
                done=t["done"],
                created_at=t["created_at"],
                group_id=t["group_id"],
                due_date=t["due_date"],
                comments=comments,
                tags=list(t["tags"]),
                priority=t["priority"],
                subtasks=subtasks
            )
            self.tasks.append(task)

    async def action_undo(self) -> None:
        if not self.undo_stack:
            self.notify("⚠️ No hay acciones para deshacer", severity="warning", timeout=2)
            return
        
        current_state = self._capture_state()
        self.redo_stack.append(current_state)
        
        if len(self.redo_stack) > self.max_undo:
            self.redo_stack.pop(0)
        
        previous_state = self.undo_stack.pop()
        
        self._restore_state(previous_state)
        
        await self.refresh_tabs()
        await self.refresh_view()
        self.update_stats()
        
        self.notify(f"↩️ Deshecho (Ctrl+Y para rehacer | {len(self.undo_stack)} deshacer restantes)", severity="information", timeout=2)
    
    async def action_redo(self) -> None:
        if not self.redo_stack:
            self.notify("⚠️ No hay acciones para rehacer", severity="warning", timeout=2)
            return
        
        current_state = self._capture_state()
        self.undo_stack.append(current_state)
        
        if len(self.undo_stack) > self.max_undo:
            self.undo_stack.pop(0)
        
        redo_state = self.redo_stack.pop()
        
        self._restore_state(redo_state)
        
        await self.refresh_tabs()
        await self.refresh_view()
        self.update_stats()
        
        self.notify(f"↪️ Rehecho (Ctrl+Z para deshacer | {len(self.redo_stack)} rehacer restantes)", severity="information", timeout=2)
    
    def save_data(self) -> None:
        with self.save_lock:
            data = {
                "next_task_id": self.next_task_id,
                "next_group_id": self.next_group_id,
                "next_tag_id": self.next_tag_id,
                "next_subtask_id": self.next_subtask_id,
                "groups": [{"id": g.id, "name": g.name} for g in self.groups],
                "tags": [{"id": t.id, "name": t.name} for t in self.tags],
                "tasks": [{
                    "id": t.id, 
                    "text": t.text, 
                    "done": t.done, 
                    "created_at": t.created_at,
                    "group_id": t.group_id, 
                    "due_date": t.due_date,
                    "comments": [{"id": c.id, "text": c.text, "url": c.url, 
                                "image_path": c.image_path, "created_at": c.created_at} 
                                for c in t.comments],
                    "tags": t.tags, 
                    "priority": t.priority,
                    "subtasks": [{
                        "id": s.id, 
                        "text": s.text, 
                        "done": s.done,
                        "created_at": s.created_at, 
                        "due_date": s.due_date,
                        "comments": [{
                            "id": c.id, 
                            "text": c.text, 
                            "url": c.url,
                            "image_path": c.image_path, 
                            "created_at": c.created_at
                        } for c in s.comments]
                    } for s in t.subtasks]
                } for t in self.tasks]
            }
        try: 
            self.data_file.write_text(json.dumps(data, ensure_ascii=False, indent=2))
        except Exception as e:
            print(f"Error guardando datos: {e}")
            self.notify(f"❌ Error al guardar: {e}", severity="error", timeout=3)
        
    def load_data(self) -> None:
        try:
            if self.data_file.exists():
                data = json.loads(self.data_file.read_text())
                self.next_task_id = data.get("next_task_id", 1)
                self.next_group_id = data.get("next_group_id", 1)
                self.next_tag_id = data.get("next_tag_id", 1)
                self.next_subtask_id = data.get("next_subtask_id", 1)
                self.groups = [Group(id=g["id"], name=g["name"]) for g in data.get("groups", [])]
                self.tags = [Tag(id=t["id"], name=t["name"]) for t in data.get("tags", [])]
                self.tasks = []
                for t in data.get("tasks", []):
                    comments = [Comment(id=c["id"], text=c["text"], url=c.get("url"), 
                                    image_path=c.get("image_path"),
                                    created_at=c.get("created_at", ""))
                            for c in t.get("comments", [])]
                    
                    subtasks = []
                    for s in t.get("subtasks", []):
                        subtask_comments = [Comment(
                            id=c["id"], 
                            text=c["text"], 
                            url=c.get("url"),
                            image_path=c.get("image_path"),
                            created_at=c.get("created_at", "")
                        ) for c in s.get("comments", [])]
                        
                        subtask = Subtask(
                            id=s["id"], 
                            text=s["text"], 
                            done=s.get("done", False),
                            created_at=s.get("created_at", ""),
                            due_date=s.get("due_date"),
                            comments=subtask_comments
                        )
                        subtasks.append(subtask)
                    
                    task = Task(
                        id=t["id"], 
                        text=t["text"], 
                        done=t.get("done", False),
                        created_at=t.get("created_at", ""), 
                        group_id=t.get("group_id"),
                        due_date=t.get("due_date"), 
                        comments=comments, 
                        tags=t.get("tags", []),
                        priority=t.get("priority", 0), 
                        subtasks=subtasks
                    )
                    self.tasks.append(task)
        except Exception as e:
            self.tasks, self.groups, self.tags = [], [], []
            self.next_task_id = self.next_group_id = self.next_tag_id = self.next_subtask_id = 1
        
def main():
    TodoApp().run()

if __name__ == "__main__":
    main()  
