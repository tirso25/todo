# 📋 MyTaskit - Gestor de Tareas para Terminal

<div align="center">

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Textual](https://img.shields.io/badge/Textual-0.47+-purple.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Platform](https://img.shields.io/badge/Platform-Linux%20%7C%20Windows%20%7C%20macOS-lightgrey.svg)

Una aplicación de gestión de tareas moderna y completa para la terminal, construida con [Textual](https://textual.textualize.io/).

[Características](#-características) • [Instalación](#-instalación) • [Uso](#-uso) • [Atajos de Teclado](#%EF%B8%8F-atajos-de-teclado)

</div>

---

## ✨ Características

### 🎯 Gestión Completa de Tareas
- **Crear, editar y eliminar** tareas con interfaz intuitiva
- **Prioridades** con 4 niveles: Sin prioridad, Baja ⬇, Media ■, Alta ⬆
- **Fechas de vencimiento** con calendario visual integrado
- **Comentarios** con soporte para enlaces/URLs
- **Etiquetas** personalizables e ilimitadas por tarea
- **Estado** de tareas: pendientes y completadas
- **Auto-guardado** cada 10 segundos

### 📁 Organización por Grupos
- **Grupos personalizados** para categorizar tareas
- **Grupo General** - Vista unificada de todas las tareas
- **Grupo Sin grupo** - Tareas sin categoría asignada
- **Navegación rápida** entre grupos con flechas o Tab
- **Gestión de grupos**: crear, renombrar y eliminar

### 🔍 Filtrado y Ordenación Avanzada
- **Filtros múltiples** combinables:
  - 📅 Por fechas (múltiples fechas o sin fecha)
  - 🏷️ Por etiquetas (modo AND - todas deben coincidir)
  - ✅ Por estado (pendientes/completadas)
  - ⭐ Por prioridad (múltiples niveles)

- **Ordenación flexible** por categorías:
  - 🔤 Alfabético (A→Z o Z→A)
  - 📅 Fecha (próximas primero o lejanas primero)
  - ⭐ Prioridad (alta→baja o baja→alta)
  - ➕ **Combinable**: Los criterios se aplican en orden jerárquico

### 📅 Modo Calendario
- **Calendario visual** completo
- **Navegación** por días, semanas y meses
- **Indicadores visuales** de días con tareas
- **Vista de tareas del día** seleccionado
- **Salto rápido** al grupo de una tarea

### 💬 Comentarios con Enlaces
- **Comentarios ilimitados** por tarea
- **Enlaces/URLs** opcionales en cada comentario
- **Apertura automática** de enlaces en navegador con Control + o
- **Icono 🔗** indica comentarios con enlaces
- **Validación de URLs** (http:// o https://)

### 🔔 Sistema de Recordatorios
- **Notificaciones** automáticas al iniciar la app
- **Alerta** de tareas que vencen HOY
- **Modal no intrusivo** con información del grupo

### 🎨 Interfaz Moderna
- **Tema Dracula** por defecto
- **Diseño responsive** que se adapta a tu terminal
- **Navegación tipo Vim** (h/j/k/l) además de flechas
- **Estadísticas en tiempo real** en barra inferior
- **Separación visual** entre tareas pendientes y completadas

### 🔎 Búsqueda Global
- **Búsqueda de texto** en todas las tareas
- **Navegación directa** al grupo de la tarea encontrada
- **Resultados múltiples** con modal de selección

---

## 🚀 Instalación

### Requisitos
- Python 3.8 o superior
- pip (gestor de paquetes de Python)

### Instalación Rápida
```bash
# Clonar el repositorio
git clone https://github.com/tu-usuario/todo-app.git
cd todo-app

# Instalar dependencias
pip install textual

# Ejecutar la aplicación
python todo.py
```

### Instalación de Dependencias
```bash
pip install textual
```

### Ubicación de Datos

Los datos se guardan automáticamente en:
- **Linux/macOS**: `~/todo/todo_tasks.json`
- **Windows**: `C:\Users\TuUsuario\todo\todo_tasks.json`

---

## 📖 Uso

### Inicio Rápido

1. **Ejecutar la aplicación**:
```bash
   python todo.py
```

2. **Crear tu primera tarea**:
   - Presiona `a` para añadir una tarea
   - Escribe el texto y presiona Enter

3. **Organizar con grupos**:
   - Presiona `g` para crear un grupo
   - Usa `←` `→` para navegar entre grupos

4. **Marcar como completada**:
   - Selecciona una tarea con `↑` `↓`
   - Presiona `Espacio` o `Enter`

### Flujo de Trabajo Típico
```
1. Crear grupos por proyecto/contexto
2. Añadir tareas a cada grupo
3. Asignar prioridades y fechas
4. Añadir etiquetas para categorización
5. Filtrar y ordenar según necesites
6. Marcar como completadas al terminar
```

---

## ⌨️ Atajos de Teclado

### Gestión de Tareas
| Tecla | Acción |
|-------|--------|
| `a` | Añadir nueva tarea |
| `e` | Editar tarea seleccionada |
| `d` | Eliminar tarea seleccionada |
| `Espacio` | Marcar/Desmarcar como completada |
| `Enter` | Marcar/Desmarcar como completada |

### Navegación
| Tecla | Acción |
|-------|--------|
| `↑` `↓` o `k` `j` | Navegar entre tareas |
| `←` `→` o `h` `l` | Cambiar de grupo |
| `Tab` | Ciclo: General → Sin grupo → Grupos personalizados |

### Grupos
| Tecla | Acción |
|-------|--------|
| `g` | Crear nuevo grupo |
| `G` | Opciones de grupo (renombrar/eliminar) |

### Filtros y Ordenación
| Tecla | Acción |
|-------|--------|
| `f` | Abrir modal de filtros |
| `o` | Abrir modal de ordenación |
| `/` | Buscar tareas por texto |

### Etiquetas
| Tecla | Acción |
|-------|--------|
| `T` | Gestionar etiquetas globales |
| (En edición) | Asignar etiquetas a tarea |

### Calendario
| Tecla | Acción |
|-------|--------|
| `c` | Activar/Desactivar modo calendario |
| `i` | Ver tareas de HOY |
| `←` `→` `↑` `↓` | Navegar por días/semanas |
| `n` `p` | Mes siguiente/anterior |
| `t` | Ir a hoy |
| `Enter` | Ver tareas del día seleccionado |

### Sistema
| Tecla | Acción |
|-------|--------|
| `q` | Salir (guarda automáticamente) |
| `Esc` | Cancelar/Cerrar modal |

---

## 🖼️ Capturas de Pantalla

### Vista Principal
```
┌─ 📋 TODO App ─────────────────────────────────────────────────────────────┐
│  📚 General   📋 Sin grupo   📁 Trabajo   📁 Personal                      │
├───────────────────────────────────────────────────────────────────────────┤
│ ☐ ⬆  Revisar propuesta cliente  Urgente  💬2 🔗1  Grupo: Trabajo  📅 08/01│
│ ☐ ■  Comprar regalo cumpleaños  Personal  💬1     Grupo: Personal 📅 10/01│
│ ☑    Llamar al dentista                           Grupo: Personal         │
├───────────────────────────────────────────────────────────────────────────┤
│ Total: 3 | Completadas: 1 | Pendientes: 2 | Grupo: General               │
└───────────────────────────────────────────────────────────────────────────┘
```

### Modo Calendario
```
┌─ 📋 TODO App ─────────────────────────────────────────────────────────────┐
│                          Enero 2026                                        │
│   Lu  Ma  Mi  Ju  Vi  Sá  Do                                              │
│   ─────────────────────────                                               │
│                   1   2   3                                                │
│    4   5   6  •7  [8]  9  10                                              │
│   11  12  13  14  15  16  17                                              │
│                                                                            │
│ 📋 2 tarea(s):                                                            │
│   ☐ Revisar propuesta cliente          Grupo: Trabajo                     │
│   ☐ Reunión equipo                     Grupo: Trabajo                     │
└───────────────────────────────────────────────────────────────────────────┘
```

### Modal de Filtros
```
┌─ 🔍 Filtrar Tareas ──────────────────────────────────────┐
│ Fecha:                                                   │
│  📅 08/01, 10/01                [📅 Seleccionar] [❌ Quitar]│
│ Etiquetas:                                               │
│  🏷️ Urgente, Personal           [🏷️ Seleccionar] [❌ Quitar]│
│ Estado:                                                  │
│  ✅ Pendientes                  [✓ Seleccionar] [❌ Quitar] │
│ Prioridad:                                               │
│  ⭐ Alta, Media                 [⭐ Seleccionar] [❌ Quitar] │
│                                                          │
│            [Aplicar] [Quitar todos]                      │
└──────────────────────────────────────────────────────────┘
```

---

## 🗂️ Estructura de Datos

El archivo `todo_tasks.json` tiene la siguiente estructura:
```json
{
  "next_task_id": 4,
  "next_group_id": 3,
  "next_tag_id": 4,
  "groups": [
    {"id": 1, "name": "Trabajo"},
    {"id": 2, "name": "Personal"}
  ],
  "tags": [
    {"id": 1, "name": "Urgente"},
    {"id": 2, "name": "Importante"},
    {"id": 3, "name": "Revisión"}
  ],
  "tasks": [
    {
      "id": 1,
      "text": "Revisar propuesta cliente",
      "done": false,
      "created_at": "08/01 14:30",
      "group_id": 1,
      "due_date": "2026-01-08",
      "priority": 3,
      "tags": [1, 2],
      "comments": [
        {
          "id": 1,
          "text": "Revisar sección de precios",
          "url": "https://docs.google.com/...",
          "created_at": "08/01 14:35"
        }
      ]
    }
  ]
}
```

---

## 🎯 Casos de Uso

### Para Desarrolladores
```
✅ Gestión de issues/bugs por proyecto
✅ Seguimiento de tareas de sprint
✅ Lista de features pendientes
✅ Recordatorios de code review
```

### Para Estudiantes
```
✅ Tareas por asignatura
✅ Fechas de exámenes y entregas
✅ Proyectos grupales
✅ Material de estudio pendiente
```

### Para Uso Personal
```
✅ Lista de compras
✅ Tareas del hogar
✅ Recordatorios médicos
✅ Planificación de eventos
```

### Para Gestión de Proyectos
```
✅ Hitos del proyecto
✅ Tareas por fase
✅ Seguimiento de dependencias
✅ Coordinación de equipo
```

---

## 🔧 Configuración Avanzada

### Personalizar Ubicación de Datos

Edita en el código (línea ~2717):
```python
self.data_file = Path.home() / "todo" / "todo_tasks.json"
# Cambiar a tu ubicación preferida:
# self.data_file = Path("/mi/ruta/custom/tasks.json")
```

### Cambiar Tema

Edita en el código (línea ~2740):
```python
theme = "dracula"
# Otros temas disponibles:
# "textual-dark", "textual-light", "nord", "monokai"
```

### Ajustar Auto-guardado

Edita en el código (línea ~2759):
```python
self.set_interval(10, self.save_data)  # 10 segundos
# Cambiar el número para ajustar intervalo
```

## 📄 Licencia

Este proyecto está bajo la Licencia MIT - ver el archivo [LICENSE](LICENSE) para más detalles.

---

## 👤 Autor

**Tirso**

- GitHub: [@tirso](https://github.com/tirso25)

<div align="center">

**¿Te gusta este proyecto? ¡Dale una ⭐ en GitHub!**

[Reportar Bug](https://github.com/tu-usuario/todo-app/issues) • [Solicitar Feature](https://github.com/tu-usuario/todo-app/issues) • [Discusiones](https://github.com/tu-usuario/todo-app/discussions)

</div>
