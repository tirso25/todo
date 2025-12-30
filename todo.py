#!/usr/bin/env python3
"""
TODO App - Aplicación de tareas para terminal con grupos y calendario
Controles:
  a - Añadir tarea
  e - Editar tarea (incluye opción de fecha y grupo)
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
class Comment:
    id: int
    text: str
    created_at: str = ""
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().strftime("%d/%m %H:%M")


@dataclass
class Tag:
    id: int
    name: str
    
    def __post_init__(self):
        # Limitar nombre a 30 caracteres
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
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().strftime("%d/%m %H:%M")
        if self.comments is None:
            self.comments = []
        if self.tags is None:
            self.tags = []


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
    TaskWidget .tag { background: #90EE90; color: #000000; }
    TaskWidget .tag-separator { width: 1; }
    TaskWidget .task-comments { width: 5; height: 1; text-align: right; color: $primary; }
    TaskWidget .task-date { width: 8; height: 1; text-align: right; color: $warning; }
    TaskWidget .task-time { width: 12; height: 1; text-align: right; color: $text-muted; }
    TaskWidget.done .task-text { text-style: strike; color: $text-muted; }
    TaskWidget.done .checkbox { color: $success; }
    TaskWidget.done .task-date { color: $text-muted; }
    TaskWidget.done .task-comments { color: $text-muted; }
    """
    
    def __init__(self, task_data: Task, all_tags: list[Tag] = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.task_data = task_data
        self.all_tags = all_tags or []
        self._selected = False
    
    def compose(self) -> ComposeResult:
        checkbox = "☑" if self.task_data.done else "☐"
        yield Label(checkbox, classes="checkbox")
        yield Label(self.task_data.text, classes="task-text")
        # Mostrar etiquetas
        if self.task_data.tags:
            for tag_id in self.task_data.tags[:2]:  # Máximo 2 etiquetas visibles
                tag = next((t for t in self.all_tags if t.id == tag_id), None)
                if tag:
                    # Truncar nombre de etiqueta a 10 chars para que quepa
                    tag_name = tag.name[:10] if len(tag.name) > 10 else tag.name
                    yield Label(f" {tag_name} ", classes="tag")
                    yield Label(" ", classes="tag-separator")  # Separador
        comments_str = f"💬{len(self.task_data.comments)}" if self.task_data.comments else ""
        yield Label(comments_str, classes="task-comments")
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


class GroupPickerModal(ModalScreen[Optional[int]]):
    """Modal para seleccionar un grupo"""
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
        # Lista de opciones: None (sin grupo) + todos los grupos
        self.options: list[Optional[int]] = [None] + [g.id for g in groups]
        # Índice inicial basado en el grupo actual
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
        
        # Opción "Sin grupo"
        item = Static("📋 Sin grupo", id="group-item-0", classes="group-item")
        await groups_list.mount(item)
        if self.selected_index == 0:
            item.add_class("selected")
        
        # Grupos existentes
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
        self.dismiss(self.current_group_id)  # Devolver el grupo actual si se cancela


class CommentsModal(ModalScreen[list[Comment]]):
    """Modal para gestionar comentarios de una tarea"""
    DEFAULT_CSS = """
    CommentsModal { align: center middle; }
    CommentsModal > Container {
        width: 70; height: 22; border: thick $primary;
        background: $surface; padding: 1 2;
    }
    CommentsModal .modal-title { text-align: center; text-style: bold; width: 100%; height: 1; margin-bottom: 1; }
    CommentsModal #comments-list { width: 100%; height: 10; overflow-y: auto; border: solid $primary-background; padding: 1; }
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
    ]
    
    def __init__(self, comments: list[Comment], next_comment_id: int, **kwargs) -> None:
        super().__init__(**kwargs)
        self.comments = [Comment(id=c.id, text=c.text, created_at=c.created_at) for c in comments]
        self.next_comment_id = next_comment_id
        self.selected_index = 0 if comments else -1
    
    def compose(self) -> ComposeResult:
        with Container():
            yield Label("💬 Comentarios", classes="modal-title")
            yield Container(id="comments-list")
            yield Label("↑↓ Navegar | a: Añadir | e: Editar | d: Eliminar | Esc: Cerrar", classes="hint")
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
                # Truncar texto si es muy largo
                text = comment.text[:50] + "..." if len(comment.text) > 50 else comment.text
                item = Static(f"{text}  [{comment.created_at}]", id=f"comment-{i}", classes="comment-item")
                await comments_list.mount(item)
                if i == self.selected_index:
                    item.add_class("selected")
            # Scroll al elemento seleccionado
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
        def on_result(text: Optional[str]) -> None:
            if text:
                comment = Comment(id=self.next_comment_id, text=text)
                self.next_comment_id += 1
                self.comments.append(comment)
                self.selected_index = len(self.comments) - 1
                self.call_later(self.refresh_comments_list)
        self.app.push_screen(InputModal("💬 Nuevo Comentario", placeholder="Escribe el comentario..."), on_result)
    
    def action_edit_comment(self) -> None:
        if not self.comments or self.selected_index < 0:
            return
        comment = self.comments[self.selected_index]
        def on_result(text: Optional[str]) -> None:
            if text:
                comment.text = text
                self.call_later(self.refresh_comments_list)
        self.app.push_screen(InputModal("✏️ Editar Comentario", initial_text=comment.text), on_result)
    
    def action_delete_comment(self) -> None:
        if not self.comments or self.selected_index < 0:
            return
        comment = self.comments[self.selected_index]
        txt = comment.text[:30] + "..." if len(comment.text) > 30 else comment.text
        def on_confirm(yes: bool) -> None:
            if yes:
                self.comments.pop(self.selected_index)
                if self.selected_index >= len(self.comments) and self.selected_index > 0:
                    self.selected_index -= 1
                if not self.comments:
                    self.selected_index = -1
                self.call_later(self.refresh_comments_list)
        self.app.push_screen(ConfirmModal(f"¿Eliminar comentario '{txt}'?"), on_confirm)
    
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
    """Modal para gestionar etiquetas globales"""
    DEFAULT_CSS = """
    TagsManagerModal { align: center middle; }
    TagsManagerModal > Container {
        width: 60; height: 22; border: thick $primary;
        background: $surface; padding: 1 2;
    }
    TagsManagerModal .modal-title { text-align: center; text-style: bold; width: 100%; height: 1; margin-bottom: 1; }
    TagsManagerModal #tags-list { width: 100%; height: 10; overflow-y: auto; border: solid $primary-background; padding: 1; }
    TagsManagerModal .tag-item {
        width: 100%; height: 3; padding: 0 1;
        border: solid $primary-background; margin-bottom: 1;
    }
    TagsManagerModal .tag-item:hover { background: $boost; }
    TagsManagerModal .tag-item.selected { border: solid $accent; background: $surface-lighten-1; }
    TagsManagerModal .tag-preview { background: #90EE90; color: #000000; padding: 0 1; }
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
    ]
    
    def __init__(self, tags: list[Tag], next_tag_id: int, **kwargs) -> None:
        super().__init__(**kwargs)
        self.tags = [Tag(id=t.id, name=t.name) for t in tags]
        self.next_tag_id = next_tag_id
        self.selected_index = 0 if tags else -1
    
    def compose(self) -> ComposeResult:
        with Container():
            yield Label("🏷️  Gestionar Etiquetas", classes="modal-title")
            yield Container(id="tags-list")
            yield Label("↑↓ Navegar | a: Añadir | e: Editar | d: Eliminar | Esc: Cerrar", classes="hint")
            with Horizontal(classes="button-row"):
                yield Button("➕ Añadir", variant="primary", id="add")
                yield Button("✏️ Editar", variant="default", id="edit")
                yield Button("🗑️ Eliminar", variant="error", id="delete")
    
    async def on_mount(self) -> None:
        await self.refresh_tags_list()
    
    async def refresh_tags_list(self) -> None:
        tags_list = self.query_one("#tags-list", Container)
        await tags_list.remove_children()
        
        if not self.tags:
            await tags_list.mount(Label("No hay etiquetas. Pulsa 'a' para crear una.", classes="empty-msg"))
            self.selected_index = -1
        else:
            for i, tag in enumerate(self.tags):
                item = Static(f"  {tag.name}  ", id=f"tag-{i}", classes="tag-item")
                await tags_list.mount(item)
                if i == self.selected_index:
                    item.add_class("selected")
            self.scroll_to_selected()
    
    def scroll_to_selected(self) -> None:
        if self.selected_index >= 0:
            try:
                item = self.query_one(f"#tag-{self.selected_index}", Static)
                item.scroll_visible()
            except: pass
    
    def update_selection(self) -> None:
        for i in range(len(self.tags)):
            try:
                item = self.query_one(f"#tag-{i}", Static)
                item.set_class(i == self.selected_index, "selected")
            except: pass
        self.scroll_to_selected()
    
    def action_move_up(self) -> None:
        if self.tags and self.selected_index > 0:
            self.selected_index -= 1
            self.update_selection()
    
    def action_move_down(self) -> None:
        if self.tags and self.selected_index < len(self.tags) - 1:
            self.selected_index += 1
            self.update_selection()
    
    def action_add_tag(self) -> None:
        def on_result(name: Optional[str]) -> None:
            if name:
                tag = Tag(id=self.next_tag_id, name=name[:30])
                self.next_tag_id += 1
                self.tags.append(tag)
                self.selected_index = len(self.tags) - 1
                self.call_later(self.refresh_tags_list)
        self.app.push_screen(InputModal("🏷️  Nueva Etiqueta", placeholder="Nombre (máx 30 caracteres)..."), on_result)
    
    def action_edit_tag(self) -> None:
        if not self.tags or self.selected_index < 0:
            return
        tag = self.tags[self.selected_index]
        def on_result(name: Optional[str]) -> None:
            if name:
                tag.name = name[:30]
                self.call_later(self.refresh_tags_list)
        self.app.push_screen(InputModal("✏️  Editar Etiqueta", initial_text=tag.name), on_result)
    
    def action_delete_tag(self) -> None:
        if not self.tags or self.selected_index < 0:
            return
        tag = self.tags[self.selected_index]
        def on_confirm(yes: bool) -> None:
            if yes:
                self.tags.pop(self.selected_index)
                if self.selected_index >= len(self.tags) and self.selected_index > 0:
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
    
    def action_close(self) -> None:
        self.dismiss(self.tags)


class TagPickerModal(ModalScreen[list[int]]):
    """Modal para seleccionar etiquetas para una tarea"""
    DEFAULT_CSS = """
    TagPickerModal { align: center middle; }
    TagPickerModal > Container {
        width: 60; height: 22; border: thick $primary;
        background: $surface; padding: 1 2;
    }
    TagPickerModal .modal-title { text-align: center; text-style: bold; width: 100%; height: 1; margin-bottom: 1; }
    TagPickerModal #tags-list { width: 100%; height: 10; overflow-y: auto; border: solid $primary-background; padding: 1; }
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
    ]
    
    def __init__(self, all_tags: list[Tag], selected_tag_ids: list[int], **kwargs) -> None:
        super().__init__(**kwargs)
        self.all_tags = all_tags
        self.selected_tag_ids = list(selected_tag_ids)
        self.selected_index = 0 if all_tags else -1
    
    def compose(self) -> ComposeResult:
        with Container():
            yield Label("🏷️  Seleccionar Etiquetas", classes="modal-title")
            yield Container(id="tags-list")
            yield Label("↑↓ Navegar | Espacio: Marcar/Desmarcar | Enter: Guardar | Esc: Cancelar", classes="hint")
            with Horizontal(classes="button-row"):
                yield Button("Guardar", variant="primary", id="save")
                yield Button("Cancelar", variant="default", id="cancel")
    
    async def on_mount(self) -> None:
        await self.refresh_tags_list()
    
    async def refresh_tags_list(self) -> None:
        tags_list = self.query_one("#tags-list", Container)
        await tags_list.remove_children()
        
        if not self.all_tags:
            await tags_list.mount(Label("No hay etiquetas. Créalas con 'T' en el menú principal.", classes="empty-msg"))
            self.selected_index = -1
        else:
            for i, tag in enumerate(self.all_tags):
                checked = "☑" if tag.id in self.selected_tag_ids else "☐"
                item = Static(f"{checked}  {tag.name}", id=f"tag-{i}", classes="tag-item")
                await tags_list.mount(item)
                if tag.id in self.selected_tag_ids:
                    item.add_class("checked")
                if i == self.selected_index:
                    item.add_class("selected")
            self.scroll_to_selected()
    
    def scroll_to_selected(self) -> None:
        if self.selected_index >= 0:
            try:
                item = self.query_one(f"#tag-{self.selected_index}", Static)
                item.scroll_visible()
            except: pass
    
    def update_selection(self) -> None:
        for i in range(len(self.all_tags)):
            try:
                item = self.query_one(f"#tag-{i}", Static)
                item.set_class(i == self.selected_index, "selected")
            except: pass
        self.scroll_to_selected()
    
    def action_move_up(self) -> None:
        if self.all_tags and self.selected_index > 0:
            self.selected_index -= 1
            self.update_selection()
    
    def action_move_down(self) -> None:
        if self.all_tags and self.selected_index < len(self.all_tags) - 1:
            self.selected_index += 1
            self.update_selection()
    
    def action_toggle_tag(self) -> None:
        if not self.all_tags or self.selected_index < 0:
            return
        tag = self.all_tags[self.selected_index]
        if tag.id in self.selected_tag_ids:
            self.selected_tag_ids.remove(tag.id)
        else:
            self.selected_tag_ids.append(tag.id)
        self.call_later(self.refresh_tags_list)
    
    def action_save(self) -> None:
        self.dismiss(self.selected_tag_ids)
    
    @on(Button.Pressed, "#save")
    def on_save(self) -> None:
        self.action_save()
    
    @on(Button.Pressed, "#cancel")
    def on_cancel(self) -> None:
        self.action_cancel()
    
    def action_cancel(self) -> None:
        self.dismiss(None)


class FilterModal(ModalScreen[Optional[dict]]):
    """Modal para filtrar tareas por fecha o etiqueta"""
    DEFAULT_CSS = """
    FilterModal { align: center middle; }
    FilterModal > Container {
        width: 50; height: auto; border: thick $primary;
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
    
    def __init__(self, current_date_filter: Optional[str], current_tag_filter: Optional[int],
                 all_tags: list[Tag], available_dates: list[str], **kwargs) -> None:
        super().__init__(**kwargs)
        self.date_filter = current_date_filter
        self.tag_filter = current_tag_filter
        self.all_tags = all_tags
        self.available_dates = available_dates
    
    def compose(self) -> ComposeResult:
        with Container():
            yield Label("🔍 Filtrar Tareas", classes="modal-title")
            yield Label("Fecha:", classes="section-label")
            with Horizontal(classes="filter-row"):
                yield Label(self._format_date_filter(), id="date-display", classes="filter-display")
                yield Button("📅 Cambiar", id="change-date")
                yield Button("❌ Quitar", id="remove-date")
            yield Label("Etiqueta:", classes="section-label")
            with Horizontal(classes="filter-row"):
                yield Label(self._format_tag_filter(), id="tag-display", classes="filter-display")
                yield Button("🏷️ Cambiar", id="change-tag")
                yield Button("❌ Quitar", id="remove-tag")
            with Horizontal(classes="button-row"):
                yield Button("Aplicar", variant="primary", id="apply")
                yield Button("Quitar todos", variant="warning", id="clear")
                yield Button("Cancelar", variant="default", id="cancel")
    
    def _format_date_filter(self) -> str:
        if self.date_filter is None:
            return "Todas las fechas"
        elif self.date_filter == "none":
            return "📅 Sin fecha asignada"
        else:
            try:
                d = datetime.strptime(self.date_filter, "%Y-%m-%d")
                return f"📅 {d.day:02d}/{d.month:02d}/{d.year}"
            except:
                return "Todas las fechas"
    
    def _format_tag_filter(self) -> str:
        if self.tag_filter is None:
            return "Todas las etiquetas"
        tag = next((t for t in self.all_tags if t.id == self.tag_filter), None)
        if tag:
            return f"🏷️ {tag.name}"
        return "Todas las etiquetas"
    
    @on(Button.Pressed, "#change-date")
    def on_change_date(self) -> None:
        def on_result(result: Optional[str]) -> None:
            if result is not None:
                self.date_filter = result
                self.query_one("#date-display", Label).update(self._format_date_filter())
        self.app.push_screen(DateFilterPickerModal(self.available_dates, self.date_filter), on_result)
    
    @on(Button.Pressed, "#remove-date")
    def on_remove_date(self) -> None:
        self.date_filter = None
        self.query_one("#date-display", Label).update(self._format_date_filter())
    
    @on(Button.Pressed, "#change-tag")
    def on_change_tag(self) -> None:
        def on_result(result: Optional[int]) -> None:
            if result is not None:
                self.tag_filter = result if result != -1 else None
                self.query_one("#tag-display", Label).update(self._format_tag_filter())
        self.app.push_screen(TagFilterPickerModal(self.all_tags, self.tag_filter), on_result)
    
    @on(Button.Pressed, "#remove-tag")
    def on_remove_tag(self) -> None:
        self.tag_filter = None
        self.query_one("#tag-display", Label).update(self._format_tag_filter())
    
    @on(Button.Pressed, "#apply")
    def on_apply(self) -> None:
        self.dismiss({"date": self.date_filter, "tag": self.tag_filter})
    
    @on(Button.Pressed, "#clear")
    def on_clear(self) -> None:
        self.dismiss({"date": None, "tag": None})
    
    @on(Button.Pressed, "#cancel")
    def on_cancel_btn(self) -> None:
        self.dismiss(None)
    
    def action_cancel(self) -> None:
        self.dismiss(None)


class DateFilterPickerModal(ModalScreen[Optional[str]]):
    """Modal para seleccionar filtro de fecha"""
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
        Binding("enter", "select", show=False),
    ]
    
    def __init__(self, available_dates: list[str], current_filter: Optional[str], **kwargs) -> None:
        super().__init__(**kwargs)
        self.available_dates = available_dates
        self.current_filter = current_filter
        # Opciones: "none" (sin fecha) + fechas disponibles
        self.options = ["none"] + sorted(set(available_dates), reverse=True)
        self.selected_index = 0
        if current_filter in self.options:
            self.selected_index = self.options.index(current_filter)
    
    def compose(self) -> ComposeResult:
        with Container():
            yield Label("📅 Filtrar por Fecha", classes="modal-title")
            yield Container(id="dates-list")
            yield Label("↑↓ Navegar | Enter: Seleccionar | Esc: Cancelar", classes="hint")
            with Horizontal(classes="button-row"):
                yield Button("Seleccionar", variant="primary", id="select")
                yield Button("Cancelar", variant="default", id="cancel")
    
    async def on_mount(self) -> None:
        await self.refresh_list()
    
    async def refresh_list(self) -> None:
        dates_list = self.query_one("#dates-list", Container)
        await dates_list.remove_children()
        
        for i, opt in enumerate(self.options):
            if opt == "none":
                text = "📅 Sin fecha asignada"
            else:
                try:
                    d = datetime.strptime(opt, "%Y-%m-%d")
                    text = f"📅 {d.day:02d}/{d.month:02d}/{d.year}"
                except:
                    text = opt
            item = Static(text, id=f"date-{i}", classes="date-item")
            await dates_list.mount(item)
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
    
    def action_select(self) -> None:
        if self.options:
            self.dismiss(self.options[self.selected_index])
    
    @on(Button.Pressed, "#select")
    def on_select_btn(self) -> None:
        self.action_select()
    
    @on(Button.Pressed, "#cancel")
    def on_cancel_btn(self) -> None:
        self.dismiss(None)
    
    def action_cancel(self) -> None:
        self.dismiss(None)


class TagFilterPickerModal(ModalScreen[Optional[int]]):
    """Modal para seleccionar filtro de etiqueta"""
    DEFAULT_CSS = """
    TagFilterPickerModal { align: center middle; }
    TagFilterPickerModal > Container {
        width: 50; height: 26; border: thick $primary;
        background: $surface; padding: 1 2;
    }
    TagFilterPickerModal .modal-title { text-align: center; text-style: bold; width: 100%; height: 1; margin-bottom: 1; }
    TagFilterPickerModal #tags-list { width: 100%; height: 12; overflow-y: auto; border: solid $primary-background; padding: 1; }
    TagFilterPickerModal .tag-item {
        width: 100%; height: 3; padding: 0 1;
        border: solid $primary-background; margin-bottom: 1;
    }
    TagFilterPickerModal .tag-item:hover { background: $boost; }
    TagFilterPickerModal .tag-item.selected { border: solid $accent; background: $surface-lighten-1; }
    TagFilterPickerModal .empty-msg { width: 100%; text-align: center; color: $text-muted; text-style: italic; padding: 2; }
    TagFilterPickerModal .hint { width: 100%; height: 1; text-align: center; color: $text-muted; margin: 1 0; }
    TagFilterPickerModal .button-row { width: 100%; height: 3; align: center middle; }
    TagFilterPickerModal Button { margin: 0 1; }
    """
    BINDINGS = [
        Binding("escape", "cancel", show=False),
        Binding("up", "move_up", show=False),
        Binding("down", "move_down", show=False),
        Binding("k", "move_up", show=False),
        Binding("j", "move_down", show=False),
        Binding("enter", "select", show=False),
    ]
    
    def __init__(self, all_tags: list[Tag], current_filter: Optional[int], **kwargs) -> None:
        super().__init__(**kwargs)
        self.all_tags = all_tags
        self.current_filter = current_filter
        self.selected_index = 0
        if current_filter is not None:
            for i, tag in enumerate(all_tags):
                if tag.id == current_filter:
                    self.selected_index = i
                    break
    
    def compose(self) -> ComposeResult:
        with Container():
            yield Label("🏷️ Filtrar por Etiqueta", classes="modal-title")
            yield Container(id="tags-list")
            yield Label("↑↓ Navegar | Enter: Seleccionar | Esc: Cancelar", classes="hint")
            with Horizontal(classes="button-row"):
                yield Button("Seleccionar", variant="primary", id="select")
                yield Button("Cancelar", variant="default", id="cancel")
    
    async def on_mount(self) -> None:
        await self.refresh_list()
    
    async def refresh_list(self) -> None:
        tags_list = self.query_one("#tags-list", Container)
        await tags_list.remove_children()
        
        if not self.all_tags:
            await tags_list.mount(Label("No hay etiquetas disponibles", classes="empty-msg"))
            self.selected_index = -1
        else:
            for i, tag in enumerate(self.all_tags):
                item = Static(f"🏷️ {tag.name}", id=f"tag-{i}", classes="tag-item")
                await tags_list.mount(item)
                if i == self.selected_index:
                    item.add_class("selected")
    
    def scroll_to_selected(self) -> None:
        if self.selected_index >= 0:
            try:
                item = self.query_one(f"#tag-{self.selected_index}", Static)
                item.scroll_visible()
            except: pass
    
    def update_selection(self) -> None:
        for i in range(len(self.all_tags)):
            try:
                item = self.query_one(f"#tag-{i}", Static)
                item.set_class(i == self.selected_index, "selected")
            except: pass
        self.scroll_to_selected()
    
    def action_move_up(self) -> None:
        if self.all_tags and self.selected_index > 0:
            self.selected_index -= 1
            self.update_selection()
    
    def action_move_down(self) -> None:
        if self.all_tags and self.selected_index < len(self.all_tags) - 1:
            self.selected_index += 1
            self.update_selection()
    
    def action_select(self) -> None:
        if self.all_tags and self.selected_index >= 0:
            self.dismiss(self.all_tags[self.selected_index].id)
        else:
            self.dismiss(-1)
    
    @on(Button.Pressed, "#select")
    def on_select_btn(self) -> None:
        self.action_select()
    
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
    EditTaskModal .comments-row { width: 100%; height: auto; align: left middle; margin-bottom: 1; }
    EditTaskModal .tags-row { width: 100%; height: auto; align: left middle; margin-bottom: 1; }
    EditTaskModal .date-display { width: 1fr; padding: 0 1; }
    EditTaskModal .group-display { width: 1fr; padding: 0 1; }
    EditTaskModal .comments-display { width: 1fr; padding: 0 1; }
    EditTaskModal .tags-display { width: 1fr; padding: 0 1; }
    EditTaskModal .button-row { width: 100%; height: auto; align: center middle; margin-top: 1; }
    EditTaskModal Button { margin: 0 1; }
    """
    BINDINGS = [Binding("escape", "cancel", show=False)]
    
    def __init__(self, task_text: str, current_date: Optional[str] = None,
                 current_group_id: Optional[int] = None, groups: list[Group] = None,
                 comments: list[Comment] = None, next_comment_id: int = 1,
                 all_tags: list[Tag] = None, selected_tag_ids: list[int] = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.task_text = task_text
        self.selected_date = current_date
        self.selected_group_id = current_group_id
        self.groups = groups or []
        self.comments = comments or []
        self.next_comment_id = next_comment_id
        self.all_tags = all_tags or []
        self.selected_tag_ids = list(selected_tag_ids) if selected_tag_ids else []
    
    def compose(self) -> ComposeResult:
        with Container():
            yield Label("✏️  Editar Tarea", classes="modal-title")
            yield Label("Texto:", classes="section-label")
            yield Input(value=self.task_text, id="task-input")
            yield Label("Grupo:", classes="section-label")
            with Horizontal(classes="group-row"):
                yield Label(self._format_group(self.selected_group_id), id="group-display", classes="group-display")
                yield Button("📁 Cambiar", id="change-group")
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
    
    @on(Button.Pressed, "#change-group")
    def on_change_group(self) -> None:
        def on_result(result: Optional[int]) -> None:
            self.selected_group_id = result
            self.query_one("#group-display", Label).update(self._format_group(self.selected_group_id))
        self.app.push_screen(GroupPickerModal(self.groups, self.selected_group_id), on_result)
    
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
        self.dismiss({
            "text": text, 
            "date": self.selected_date,
            "group_id": self.selected_group_id,
            "comments": self.comments,
            "tags": self.selected_tag_ids
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
            # Truncar texto si es muy largo
            text = task.text[:30] + "..." if len(task.text) > 30 else task.text
            # Calcular espacios para alinear a la derecha
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
        Binding("f", "filter_tasks", "Filtrar"),
        Binding("g", "new_group", "Nuevo Grupo"),
        Binding("G", "group_options", "Opc. Grupo"),
        Binding("T", "manage_tags", "Etiquetas"),
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
        Binding("n", "next_month", "Mes sig.", show=False),
        Binding("p", "prev_month", "Mes ant.", show=False),
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
        self.tags: list[Tag] = []
        self.next_task_id = 1
        self.next_group_id = 1
        self.next_tag_id = 1
        self.selected_index = 0
        self.current_group_id: Optional[int] = None
        self.data_file = Path.home() / "todo" / "todo_tasks.json"
        self.data_file.parent.mkdir(exist_ok=True)
        
        self.calendar_mode = False
        self.cal_year = date.today().year
        self.cal_month = date.today().month
        self.cal_day = date.today().day
        
        # Filtros
        self.filter_date: Optional[str] = None  # None=todos, "none"=sin fecha, "YYYY-MM-DD"=fecha específica
        self.filter_tag_id: Optional[int] = None  # None=todos, ID=etiqueta específica
        
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
                yield Static("←→↑↓: Navegar | n/p: Mes | t: Hoy | Enter: Ver tareas | c: Volver", id="calendar-hint")
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
        # Primero filtrar por grupo
        if self.current_group_id is None:
            tasks = [t for t in self.tasks if t.group_id is None]
        else:
            tasks = [t for t in self.tasks if t.group_id == self.current_group_id]
        
        # Aplicar filtro de fecha
        if self.filter_date is not None:
            if self.filter_date == "none":
                tasks = [t for t in tasks if t.due_date is None]
            else:
                tasks = [t for t in tasks if t.due_date == self.filter_date]
        
        # Aplicar filtro de etiqueta
        if self.filter_tag_id is not None:
            tasks = [t for t in tasks if self.filter_tag_id in t.tags]
        
        return tasks
    
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
            # Forzar limpieza completa antes de refrescar
            await task_list.remove_children()
            await self._refresh_task_list(task_list)
    
    async def _refresh_task_list(self, task_list: Container) -> None:
        current = self._get_current_tasks()
        pending = [t for t in current if not t.done]
        completed = [t for t in current if t.done]
        
        if not current:
            msg = "No hay tareas. Pulsa 'a' para añadir una."
            await task_list.mount(Label(msg, id="empty-message"))
        else:
            for t in pending:
                w = TaskWidget(t, all_tags=self.tags, id=f"task-{t.id}")
                await task_list.mount(w)
            if completed:
                await task_list.mount(Static("── Completadas ──", id="completed-separator"))
                for t in completed:
                    w = TaskWidget(t, all_tags=self.tags, id=f"task-{t.id}")
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
            
            # Mostrar filtros activos
            filters = []
            if self.filter_date is not None:
                if self.filter_date == "none":
                    filters.append("📅 Sin fecha")
                else:
                    try:
                        d = datetime.strptime(self.filter_date, "%Y-%m-%d")
                        filters.append(f"📅 {d.day:02d}/{d.month:02d}")
                    except: pass
            if self.filter_tag_id is not None:
                tag = next((t for t in self.tags if t.id == self.filter_tag_id), None)
                if tag:
                    filters.append(f"🏷️ {tag.name}")
            if filters:
                text += " | Filtros: " + ", ".join(filters)
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
        # Resetear filtros al cambiar de grupo
        self.filter_date = None
        self.filter_tag_id = None
        await self.refresh_tabs()
        await self.refresh_view()
        self.update_stats()
    
    async def _next_group(self) -> None:
        ids = [None] + [g.id for g in self.groups]
        idx = (ids.index(self.current_group_id) + 1) % len(ids)
        self.current_group_id = ids[idx]
        self.selected_index = 0
        # Resetear filtros al cambiar de grupo
        self.filter_date = None
        self.filter_tag_id = None
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
    
    # Filter
    def action_filter_tasks(self) -> None:
        if self.calendar_mode: return
        # Obtener fechas disponibles en el grupo actual (sin filtros aplicados)
        if self.current_group_id is None:
            group_tasks = [t for t in self.tasks if t.group_id is None]
        else:
            group_tasks = [t for t in self.tasks if t.group_id == self.current_group_id]
        available_dates = [t.due_date for t in group_tasks if t.due_date]
        
        async def on_result(result: Optional[dict]) -> None:
            if result is not None:
                self.filter_date = result.get("date")
                self.filter_tag_id = result.get("tag")
                self.selected_index = 0
                await self.refresh_view()
                self.update_stats()
        self.push_screen(FilterModal(self.filter_date, self.filter_tag_id, self.tags, available_dates), on_result)
    
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
    
    def action_manage_tags(self) -> None:
        """Gestionar etiquetas globales"""
        async def on_result(updated_tags: list[Tag]) -> None:
            if updated_tags is not None:
                # Obtener IDs de etiquetas eliminadas
                old_tag_ids = {t.id for t in self.tags}
                new_tag_ids = {t.id for t in updated_tags}
                deleted_tag_ids = old_tag_ids - new_tag_ids
                
                # Eliminar etiquetas borradas de todas las tareas
                if deleted_tag_ids:
                    for task in self.tasks:
                        task.tags = [tid for tid in task.tags if tid not in deleted_tag_ids]
                
                self.tags = updated_tags
                if self.tags:
                    self.next_tag_id = max(t.id for t in self.tags) + 1
                self.save_data()
                await self.refresh_view()
        self.push_screen(TagsManagerModal(self.tags, self.next_tag_id), on_result)
    
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
        # Calcular el siguiente ID de comentario
        next_comment_id = 1
        if t.comments:
            next_comment_id = max(c.id for c in t.comments) + 1
        async def on_result(result: Optional[dict]) -> None:
            if result:
                t.text = result["text"]
                t.due_date = result["date"]
                t.comments = result.get("comments", [])
                t.tags = result.get("tags", [])
                old_group_id = t.group_id
                new_group_id = result.get("group_id")
                t.group_id = new_group_id
                self.save_data()
                # Si cambió de grupo, navegar al nuevo grupo
                if old_group_id != new_group_id:
                    self.current_group_id = new_group_id
                    self.selected_index = 0
                    await self.refresh_tabs()
                await self.refresh_view()
                self.update_stats()
                # Seleccionar la tarea editada
                for i, task in enumerate(self._get_ordered_tasks()):
                    if task.id == t.id:
                        self.selected_index = i
                        break
                self.update_selection()
        self.push_screen(EditTaskModal(t.text, t.due_date, t.group_id, self.groups, t.comments, next_comment_id, self.tags, t.tags), on_result)
    
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
            "next_tag_id": self.next_tag_id,
            "groups": [{"id": g.id, "name": g.name} for g in self.groups],
            "tags": [{"id": t.id, "name": t.name} for t in self.tags],
            "tasks": [{"id": t.id, "text": t.text, "done": t.done, "created_at": t.created_at,
                       "group_id": t.group_id, "due_date": t.due_date,
                       "comments": [{"id": c.id, "text": c.text, "created_at": c.created_at} for c in t.comments],
                       "tags": t.tags} for t in self.tasks]
        }
        try: self.data_file.write_text(json.dumps(data, ensure_ascii=False, indent=2))
        except: pass
    
    def load_data(self) -> None:
        try:
            if self.data_file.exists():
                data = json.loads(self.data_file.read_text())
                self.next_task_id = data.get("next_task_id", 1)
                self.next_group_id = data.get("next_group_id", 1)
                self.next_tag_id = data.get("next_tag_id", 1)
                self.groups = [Group(id=g["id"], name=g["name"]) for g in data.get("groups", [])]
                self.tags = [Tag(id=t["id"], name=t["name"]) for t in data.get("tags", [])]
                self.tasks = []
                for t in data.get("tasks", []):
                    comments = [Comment(id=c["id"], text=c["text"], created_at=c.get("created_at", "")) 
                               for c in t.get("comments", [])]
                    task = Task(id=t["id"], text=t["text"], done=t.get("done", False),
                               created_at=t.get("created_at", ""), group_id=t.get("group_id"),
                               due_date=t.get("due_date"), comments=comments, tags=t.get("tags", []))
                    self.tasks.append(task)
        except:
            self.tasks, self.groups, self.tags = [], [], []
            self.next_task_id = self.next_group_id = self.next_tag_id = 1


def main():
    TodoApp().run()


if __name__ == "__main__":
    main()
