import json
import random
import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox, ttk
from typing import Any

# This program creates a simple paint app where the user can draw,
# switch tools, and organize artwork into separate layers.


class PaintApp:
    """Feature-rich Tkinter paint program.

    The implementation favors readability so an intermediate developer can
    follow how drawing tools, selection, undo history, and save/load behavior
    work together.
    """

    CANVAS_BG = "white"
    MAX_UNDO = 5
    WORKSPACE_WIDTH = 1800
    WORKSPACE_HEIGHT = 1400
    DRAWABLE_TAG = "drawable"
    OVERLAY_TAG = "overlay"
    LAYER_PREFIX = "layer::"
    TOOL_LABELS = {
        "brush": "Brush",
        "eraser": "Eraser",
        "spray": "Spray Paint",
        "rectangle": "Rectangle",
        "square": "Square",
        "circle": "Circle",
        "triangle": "Triangle",
        "select": "Select Area",
        "paste": "Paste Selection",
    }

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Sketch Studio")
        self.root.geometry("1120x720")
        self.root.minsize(860, 560)
        self.root.configure(bg="#eef2ff")

        # These values remember what the user is currently doing on the canvas.
        # For example: which tool is active, which color is selected,
        # and where the mouse was during the last drawing action.
        self.current_tool = "brush"
        self.current_color = "black"
        self.current_color_name = "Black"
        self.last_x: int | None = None
        self.last_y: int | None = None
        self.start_x: int | None = None
        self.start_y: int | None = None
        self.preview_item: int | None = None
        self.selection_rect: int | None = None
        self.selection_bounds: tuple[float, float, float, float] | None = None

        # Layers work like clear sheets stacked on top of each other.
        # This makes it possible to draw on one layer without changing another.
        self.layer_order = ["Layer 1"]
        self.hidden_layers: set[str] = set()
        self.layer_counter = 1

        # These lists store copied artwork and recent versions of the canvas
        # so the user can paste items or undo recent changes.
        self.copied_items: list[dict[str, Any]] = []
        self.undo_history: list[dict[str, Any]] = []

        # Tk variables update labels and controls without manual widget refresh.
        self.brush_size_var = tk.IntVar(value=6)
        self.feedback_var = tk.StringVar(value="Current tool: Brush | Current color: Black")
        self.status_var = tk.StringVar(value="Ready to paint.")
        self.width_label_var = tk.StringVar(value="Pen width: 6")
        self.tool_var = tk.StringVar(value=self.TOOL_LABELS[self.current_tool])
        self.layer_var = tk.StringVar(value=self.layer_order[0])

        self.color_buttons: dict[str, tk.Button] = {}

        self._configure_styles()
        self._build_layout()
        self._refresh_layers()
        self._bind_canvas_events()
        self._update_feedback()

    def _configure_styles(self) -> None:
        """Configure the shared ttk styles used by the application."""
        style = ttk.Style()
        if "clam" in style.theme_names():
            style.theme_use("clam")

        style.configure("App.TFrame", background="#eef2ff")
        style.configure("Panel.TFrame", background="#ffffff")
        style.configure(
            "Title.TLabel",
            background="#ffffff",
            foreground="#111827",
            font=("Segoe UI", 16, "bold"),
        )
        style.configure(
            "Body.TLabel",
            background="#ffffff",
            foreground="#475467",
            font=("Segoe UI", 9),
        )
        style.configure(
            "Section.TLabel",
            background="#ffffff",
            foreground="#1f2937",
            font=("Segoe UI", 9, "bold"),
        )
        style.configure(
            "Action.TButton",
            font=("Segoe UI", 8, "bold"),
            padding=(6, 4),
        )
        style.configure(
            "ToolbarCard.TLabelframe",
            background="#ffffff",
            borderwidth=1,
            relief="solid",
        )
        style.configure(
            "ToolbarCard.TLabelframe.Label",
            background="#ffffff",
            foreground="#334155",
            font=("Segoe UI", 10, "bold"),
        )

    def _build_layout(self) -> None:
        """Create a tighter top toolbar and the scrollable drawing canvas."""
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        main_frame = ttk.Frame(self.root, padding=10, style="App.TFrame")
        main_frame.grid(row=0, column=0, sticky="nsew")
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)

        controls = ttk.Frame(main_frame, padding=10, style="Panel.TFrame")
        controls.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        controls.columnconfigure(1, weight=1)

        ttk.Label(controls, text="Sketch Studio", style="Title.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 12))
        ttk.Label(
            controls,
            text="Compact toolbar: colors, tools, layers, actions, and status in less space.",
            style="Body.TLabel",
            wraplength=560,
        ).grid(row=0, column=1, sticky="w")

        # The top toolbar holds the most-used controls so they stay easy to reach.
        toolbar = ttk.Frame(controls, style="Panel.TFrame")
        toolbar.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        toolbar.columnconfigure(4, weight=1)

        ttk.Label(toolbar, text="Colors", style="Section.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 6))
        color_row = tk.Frame(toolbar, bg="#ffffff")
        color_row.grid(row=0, column=1, sticky="w", padx=(0, 8))
        for index, (name, color) in enumerate((("Red", "red"), ("Green", "green"), ("Blue", "blue"), ("Black", "black"))):
            button = tk.Button(
                color_row,
                bg=color,
                activebackground=color,
                width=2,
                height=1,
                relief=tk.RAISED,
                bd=2,
                command=lambda value=color, label=name: self.select_color(value, label),
            )
            button.grid(row=0, column=index, padx=(0, 4), pady=1)
            self.color_buttons[color] = button
        ttk.Button(toolbar, text="Custom…", command=self.select_custom_color, style="Action.TButton").grid(row=0, column=2, sticky="w", padx=(0, 8))

        ttk.Label(toolbar, text="Tool", style="Section.TLabel").grid(row=0, column=3, sticky="w", padx=(0, 6))
        self.tool_selector = ttk.Combobox(
            toolbar,
            textvariable=self.tool_var,
            values=tuple(self.TOOL_LABELS.values()),
            state="readonly",
            width=15,
        )
        self.tool_selector.grid(row=0, column=4, sticky="w", padx=(0, 8))
        self.tool_selector.bind("<<ComboboxSelected>>", self._on_tool_selected)

        ttk.Label(toolbar, text="Layer", style="Section.TLabel").grid(row=0, column=5, sticky="w", padx=(0, 6))
        self.layer_selector = ttk.Combobox(
            toolbar,
            textvariable=self.layer_var,
            values=tuple(self.layer_order),
            state="readonly",
            width=11,
        )
        self.layer_selector.grid(row=0, column=6, sticky="w", padx=(0, 6))
        self.layer_selector.bind("<<ComboboxSelected>>", self._on_layer_selected)

        layer_actions = ttk.Frame(toolbar, style="Panel.TFrame")
        layer_actions.grid(row=0, column=7, sticky="w", padx=(0, 8))
        for index, (label, handler) in enumerate((("+", self.add_layer), ("Hide", self.toggle_layer_visibility), ("↑", lambda: self.move_layer(1)), ("↓", lambda: self.move_layer(-1)), ("Del", self.delete_layer))):
            button = ttk.Button(layer_actions, text=label, command=handler, style="Action.TButton")
            button.grid(row=0, column=index, padx=1)
            if label == "Hide":
                self.layer_toggle_button = button

        ttk.Label(toolbar, textvariable=self.width_label_var, style="Section.TLabel").grid(row=0, column=8, sticky="w", padx=(0, 6))
        ttk.Scale(toolbar, from_=1, to=24, orient="horizontal", variable=self.brush_size_var, command=self._on_width_changed).grid(
            row=0, column=9, sticky="ew", padx=(0, 8)
        )

        actions = ttk.Frame(toolbar, style="Panel.TFrame")
        actions.grid(row=0, column=10, sticky="e")
        for index, (label, handler) in enumerate((("Copy", self.copy_selection), ("Paste", self.paste_selection), ("Undo", self.undo_last_action), ("Clear", self.clear_canvas), ("Save", self.save_drawing), ("Load", self.load_drawing))):
            ttk.Button(actions, text=label, command=handler, style="Action.TButton").grid(row=0, column=index, padx=2)

        status_bar = ttk.Frame(controls, style="Panel.TFrame")
        status_bar.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        status_bar.columnconfigure(1, weight=1)
        status_bar.columnconfigure(2, weight=1)

        self.color_preview = tk.Label(status_bar, text="   ", bg=self.current_color, relief=tk.SUNKEN, bd=1)
        self.color_preview.grid(row=0, column=0, sticky="w", padx=(0, 8))
        ttk.Label(status_bar, textvariable=self.feedback_var, style="Body.TLabel", wraplength=320).grid(row=0, column=1, sticky="w")
        ttk.Label(status_bar, textvariable=self.status_var, style="Body.TLabel", wraplength=320).grid(row=0, column=2, sticky="w", padx=(10, 0))

        # This is the main drawing area. Scrollbars let the user work on
        # artwork that is larger than the visible window.
        canvas_panel = ttk.Frame(main_frame, padding=6, style="Panel.TFrame")
        canvas_panel.grid(row=1, column=0, sticky="nsew")
        canvas_panel.columnconfigure(0, weight=1)
        canvas_panel.rowconfigure(0, weight=1)

        self.v_scrollbar = ttk.Scrollbar(canvas_panel, orient="vertical")
        self.h_scrollbar = ttk.Scrollbar(canvas_panel, orient="horizontal")
        self.canvas = tk.Canvas(
            canvas_panel,
            bg=self.CANVAS_BG,
            highlightthickness=0,
            cursor="crosshair",
            xscrollcommand=self.h_scrollbar.set,
            yscrollcommand=self.v_scrollbar.set,
            scrollregion=(0, 0, self.WORKSPACE_WIDTH, self.WORKSPACE_HEIGHT),
        )
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.v_scrollbar.configure(command=self.canvas.yview)
        self.v_scrollbar.grid(row=0, column=1, sticky="ns")
        self.h_scrollbar.configure(command=self.canvas.xview)
        self.h_scrollbar.grid(row=1, column=0, sticky="ew")
        self._highlight_active_color()

    def _bind_canvas_events(self) -> None:
        """Bind mouse actions so the canvas responds to clicks, drags, and wheel scrolling."""
        self.canvas.bind("<ButtonPress-1>", self.on_canvas_press)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Shift-MouseWheel>", self._on_shift_mousewheel)

    def _on_width_changed(self, value: str) -> None:
        """Keep the brush width label in sync with the slider."""
        self.brush_size_var.set(int(float(value)))
        self.width_label_var.set(f"Pen width: {self.brush_size_var.get()}")

    def _on_tool_selected(self, _event: object | None = None) -> None:
        """Switch tools when the user picks a new option from the dropdown."""
        self.set_tool(next((tool for tool, label in self.TOOL_LABELS.items() if label == self.tool_var.get()), self.current_tool))

    def _on_layer_selected(self, _event: object | None = None) -> None:
        """Switch the active drawing layer from the layer dropdown."""
        self.status_var.set(f"Active layer: {self.layer_var.get()}.")
        self._refresh_layers()
        self._update_feedback()

    def _layer_tag(self, layer: str | None = None) -> str:
        """Return the canvas tag used to group all items on one layer."""
        return f"{self.LAYER_PREFIX}{layer or self.layer_var.get()}"

    def _refresh_layers(self) -> None:
        """Refresh the layer chooser, visibility, and stacking order on the canvas."""
        # Whenever the user changes layers, this keeps the drop-down list,
        # layer visibility, and front/back order all in sync.
        active = self.layer_var.get() if self.layer_var.get() in self.layer_order else self.layer_order[-1]
        self.layer_var.set(active)
        if hasattr(self, "layer_selector"):
            self.layer_selector.configure(values=tuple(self.layer_order))
        if hasattr(self, "layer_toggle_button"):
            self.layer_toggle_button.configure(text="Show" if active in self.hidden_layers else "Hide")
        if not hasattr(self, "canvas"):
            return
        for layer in self.layer_order:
            self.canvas.itemconfigure(self._layer_tag(layer), state="hidden" if layer in self.hidden_layers else "normal")
            self.canvas.tag_raise(self._layer_tag(layer))
        self.canvas.tag_raise(self.OVERLAY_TAG)

    def add_layer(self) -> None:
        """Create a new drawing layer and make it active."""
        self._push_undo_state()
        self.layer_counter += 1
        while (name := f"Layer {self.layer_counter}") in self.layer_order:
            self.layer_counter += 1
        self.layer_order.append(name)
        self.layer_var.set(name)
        self.status_var.set(f"Added {name}.")
        self._refresh_layers()
        self._update_feedback()

    def delete_layer(self) -> None:
        """Delete the active layer and any artwork assigned to it."""
        if len(self.layer_order) == 1:
            self.status_var.set("At least one layer must remain.")
            return
        self._push_undo_state()
        layer = self.layer_var.get()
        self.canvas.delete(self._layer_tag(layer))
        self.hidden_layers.discard(layer)
        index = self.layer_order.index(layer)
        self.layer_order.remove(layer)
        self.layer_var.set(self.layer_order[max(0, min(index, len(self.layer_order) - 1))])
        self._clear_selection()
        self.status_var.set(f"Deleted {layer}.")
        self._refresh_layers()
        self._update_feedback()

    def toggle_layer_visibility(self) -> None:
        """Hide or show the active layer without deleting its artwork."""
        layer = self.layer_var.get()
        if layer in self.hidden_layers:
            self.hidden_layers.remove(layer)
            message = f"{layer} is now visible."
        else:
            self.hidden_layers.add(layer)
            message = f"{layer} is now hidden."
        self.status_var.set(message)
        self._refresh_layers()
        self._update_feedback()

    def move_layer(self, direction: int) -> None:
        """Move the active layer up or down in the stacking order."""
        layer = self.layer_var.get()
        index = self.layer_order.index(layer)
        new_index = max(0, min(len(self.layer_order) - 1, index + direction))
        if new_index == index:
            return
        self._push_undo_state()
        self.layer_order.insert(new_index, self.layer_order.pop(index))
        self.status_var.set(f"Moved {layer} {'up' if direction > 0 else 'down'}.")
        self._refresh_layers()

    def set_tool(self, tool: str) -> None:
        """Change the active tool and refresh user-facing feedback."""
        self.current_tool = tool
        self.tool_var.set(self.TOOL_LABELS.get(tool, tool.title()))
        self.status_var.set({
            "select": "Drag on the canvas to choose an area to copy.",
            "paste": "Click on the canvas to place the copied selection.",
        }.get(tool, "Ready to paint. Use the dropdown to switch tools."))
        self._update_feedback()

    def _canvas_point(self, event: tk.Event) -> tuple[int, int]:
        """Convert a mouse event position into canvas coordinates for scrolled drawing."""
        return int(self.canvas.canvasx(event.x)), int(self.canvas.canvasy(event.y))

    def _on_mousewheel(self, event: tk.Event) -> str:
        """Scroll vertically with the mouse wheel while the pointer is over the canvas."""
        step = -1 if event.delta > 0 else 1
        self.canvas.yview_scroll(step, "units")
        return "break"

    def _on_shift_mousewheel(self, event: tk.Event) -> str:
        """Scroll horizontally with Shift + mouse wheel."""
        step = -1 if event.delta > 0 else 1
        self.canvas.xview_scroll(step, "units")
        return "break"

    def use_brush(self) -> None:
        """Activate the regular brush tool."""
        self.set_tool("brush")

    def use_eraser(self) -> None:
        """Activate the eraser tool."""
        self.set_tool("eraser")

    def select_color(self, color: str, name: str) -> None:
        """Switch to the brush and use the requested drawing color."""
        self.current_color = color
        self.current_color_name = name
        if self.current_tool in {"eraser", "paste"}:
            self.current_tool = "brush"
        self.status_var.set(f"Color set to {name}.")
        self._highlight_active_color()
        self._update_feedback()

    def select_custom_color(self) -> None:
        """Open the system color wheel and apply the chosen custom color."""
        _rgb, hex_color = colorchooser.askcolor(
            color=self.current_color,
            title="Choose a custom paint color",
        )
        if hex_color:
            self.select_color(hex_color, f"Custom ({hex_color.upper()})")

    def copy_selection(self) -> None:
        """Copy items inside the current selection rectangle into memory."""
        item_ids = self._selected_item_ids()
        if not item_ids or self.selection_bounds is None:
            self.status_var.set("Select an area first, then click Copy.")
            return

        x1, y1, _x2, _y2 = self.selection_bounds
        self.copied_items = [
            self._serialize_item(item_id, x_offset=x1, y_offset=y1) for item_id in item_ids
        ]
        self.status_var.set(
            f"Copied {len(self.copied_items)} item(s). Click Paste, then click the canvas."
        )

    def paste_selection(self) -> None:
        """Enter paste mode so the copied selection can be placed on the canvas."""
        if not self.copied_items:
            self.status_var.set("Nothing is copied yet. Use Select Area and Copy first.")
            return
        self.set_tool("paste")

    def undo_last_action(self) -> None:
        """Restore the canvas to its prior state, up to five actions back."""
        if not self.undo_history:
            self.status_var.set("Undo history is empty.")
            return

        snapshot = self.undo_history.pop()
        self._restore_snapshot(snapshot)
        self._clear_selection()
        self.status_var.set("Undid the last action.")

    def clear_canvas(self) -> None:
        """Erase the entire drawing surface in one action."""
        if not self._serialize_canvas():
            self.status_var.set("Canvas is already clear.")
            return

        self._push_undo_state()
        self.canvas.delete("all")
        self.selection_rect = None
        self.selection_bounds = None
        self.preview_item = None
        self.status_var.set("Canvas cleared.")

    def save_drawing(self) -> None:
        """Save the current canvas to a JSON file that can be loaded later."""
        file_path = filedialog.asksaveasfilename(
            title="Save drawing",
            defaultextension=".json",
            filetypes=[("Sketch files", "*.json"), ("All files", "*.*")],
        )
        if not file_path:
            return

        payload = dict(self._snapshot_state(), background=self.CANVAS_BG)
        try:
            with open(file_path, "w", encoding="utf-8") as file_handle:
                json.dump(payload, file_handle, indent=2)
        except OSError as exc:
            messagebox.showerror("Save failed", f"Could not save the drawing.\n\n{exc}")
            self.status_var.set("Save failed.")
            return

        self.status_var.set(f"Saved drawing to {file_path}.")

    def load_drawing(self) -> None:
        """Load a previously saved JSON drawing back onto the canvas."""
        file_path = filedialog.askopenfilename(
            title="Load drawing",
            filetypes=[("Sketch files", "*.json"), ("All files", "*.*")],
        )
        if not file_path:
            return

        try:
            with open(file_path, "r", encoding="utf-8") as file_handle:
                payload = json.load(file_handle)
        except (OSError, json.JSONDecodeError) as exc:
            messagebox.showerror("Load failed", f"Could not load the drawing.\n\n{exc}")
            self.status_var.set("Load failed.")
            return

        if not isinstance(payload, (dict, list)):
            messagebox.showerror("Load failed", "The selected file does not contain a valid sketch.")
            self.status_var.set("Load failed.")
            return

        self._push_undo_state()
        self._restore_snapshot(payload)
        self.status_var.set(f"Loaded drawing from {file_path}.")

    def on_canvas_press(self, event: tk.Event) -> None:
        """Start a new drawing, shape, selection, or paste action."""
        # When the mouse button is pressed, the app decides whether the user
        # is drawing, making a shape, selecting an area, or pasting artwork.
        canvas_x, canvas_y = self._canvas_point(event)
        self.last_x = canvas_x
        self.last_y = canvas_y
        self.start_x = canvas_x
        self.start_y = canvas_y

        if self.current_tool in {"brush", "eraser", "spray"}:
            self._push_undo_state()
            if self.current_tool == "spray":
                self._spray_at(canvas_x, canvas_y)
            else:
                self._draw_segment(canvas_x, canvas_y, canvas_x + 1, canvas_y + 1)
            return

        if self.current_tool in {"rectangle", "square", "circle", "triangle"}:
            self._push_undo_state()
            self.canvas.delete(self.preview_item) if self.preview_item else None
            self.preview_item = self._create_shape_preview(canvas_x, canvas_y, canvas_x, canvas_y)
            return

        if self.current_tool == "select":
            self._clear_selection()
            self.selection_rect = self.canvas.create_rectangle(
                canvas_x,
                canvas_y,
                canvas_x,
                canvas_y,
                outline="#6366f1",
                dash=(4, 2),
                width=2,
                tags=(self.OVERLAY_TAG, "selection"),
            )
            self.selection_bounds = None
            return

        if self.current_tool == "paste":
            self._push_undo_state()
            self._paste_at(canvas_x, canvas_y)
            self.set_tool("brush")
            self.status_var.set("Selection pasted.")

    def on_canvas_drag(self, event: tk.Event) -> None:
        """Handle continuous updates while the user drags on the canvas."""
        canvas_x, canvas_y = self._canvas_point(event)

        if self.current_tool in {"brush", "eraser"} and self.last_x is not None and self.last_y is not None:
            self._draw_segment(self.last_x, self.last_y, canvas_x, canvas_y)
            self.last_x = canvas_x
            self.last_y = canvas_y
            return

        if self.current_tool == "spray":
            self._spray_at(canvas_x, canvas_y)
            self.last_x = canvas_x
            self.last_y = canvas_y
            return

        if self.current_tool in {"rectangle", "square", "circle", "triangle"} and self.preview_item is not None:
            self._update_shape_preview(canvas_x, canvas_y)
            return

        if self.current_tool == "select" and self.selection_rect is not None:
            self.canvas.coords(self.selection_rect, self.start_x, self.start_y, canvas_x, canvas_y)

    def on_canvas_release(self, event: tk.Event) -> None:
        """Finish the current mouse-driven action and clean up temporary state."""
        canvas_x, canvas_y = self._canvas_point(event)

        if self.current_tool in {"rectangle", "square", "circle", "triangle"} and self.preview_item is not None:
            final_coords = self._shape_geometry(self.start_x or 0, self.start_y or 0, canvas_x, canvas_y)
            self.canvas.delete(self.preview_item)
            self.preview_item = None
            self._create_shape_item(final_coords)

        if self.current_tool == "select" and self.selection_rect is not None:
            raw_bounds = self.canvas.coords(self.selection_rect)
            self.selection_bounds = self._normalize_bounds(*raw_bounds)
            count = len(self._selected_item_ids())
            self.status_var.set(f"Selection ready with {count} item(s). Click Copy to store it.")

        self.last_x = None
        self.last_y = None
        self.start_x = None
        self.start_y = None

    def _draw_segment(self, x1: int, y1: int, x2: int, y2: int) -> None:
        """Draw one line segment for the brush or the eraser."""
        draw_color = self.CANVAS_BG if self.current_tool == "eraser" else self.current_color
        self.canvas.create_line(
            x1,
            y1,
            x2,
            y2,
            fill=draw_color,
            width=self.brush_size_var.get(),
            capstyle=tk.ROUND,
            smooth=True,
            splinesteps=36,
            state="hidden" if self.layer_var.get() in self.hidden_layers else "normal",
            tags=(self.DRAWABLE_TAG, self._layer_tag()),
        )
        self._refresh_layers()

    def _spray_at(self, x: int, y: int) -> None:
        """Create a spray-paint effect by scattering small dots near the cursor."""
        radius = max(6, self.brush_size_var.get() * 2)
        dot_size = max(1, self.brush_size_var.get() // 4)
        dot_count = max(10, self.brush_size_var.get() * 2)

        for _ in range(dot_count):
            dx = random.randint(-radius, radius)
            dy = random.randint(-radius, radius)
            if dx * dx + dy * dy > radius * radius:
                continue
            self.canvas.create_oval(
                x + dx,
                y + dy,
                x + dx + dot_size,
                y + dy + dot_size,
                fill=self.current_color,
                outline=self.current_color,
                state="hidden" if self.layer_var.get() in self.hidden_layers else "normal",
                tags=(self.DRAWABLE_TAG, self._layer_tag()),
            )
        self._refresh_layers()

    def _create_shape_preview(self, x1: int, y1: int, x2: int, y2: int) -> int:
        """Draw a temporary outline while the user sizes a geometric shape."""
        creator = {
            "rectangle": self.canvas.create_rectangle,
            "square": self.canvas.create_rectangle,
            "circle": self.canvas.create_oval,
            "triangle": self.canvas.create_polygon,
        }[self.current_tool]
        return creator(
            *self._shape_geometry(x1, y1, x2, y2),
            outline=self.current_color,
            width=max(2, self.brush_size_var.get() // 2),
            dash=(4, 2),
            fill="",
            tags=(self.OVERLAY_TAG, "preview"),
        )

    def _update_shape_preview(self, x2: int, y2: int) -> None:
        """Resize the temporary preview item as the user drags the mouse."""
        if self.preview_item is None or self.start_x is None or self.start_y is None:
            return
        self.canvas.coords(self.preview_item, *self._shape_geometry(self.start_x, self.start_y, x2, y2))

    def _create_shape_item(self, coords: list[float]) -> None:
        """Create the final rectangle, square, circle, or triangle on the canvas."""
        {
            "rectangle": self.canvas.create_rectangle,
            "square": self.canvas.create_rectangle,
            "circle": self.canvas.create_oval,
            "triangle": self.canvas.create_polygon,
        }[self.current_tool](
            *coords,
            outline=self.current_color,
            width=self.brush_size_var.get(),
            fill="",
            state="hidden" if self.layer_var.get() in self.hidden_layers else "normal",
            tags=(self.DRAWABLE_TAG, self._layer_tag()),
        )
        self._refresh_layers()

    def _shape_geometry(self, x1: int, y1: int, x2: int, y2: int) -> list[float]:
        """Convert the drag endpoints into coordinates for the active shape tool."""
        if self.current_tool == "rectangle":
            return [x1, y1, x2, y2]

        if self.current_tool in {"square", "circle"}:
            side = max(abs(x2 - x1), abs(y2 - y1))
            end_x = x1 + side if x2 >= x1 else x1 - side
            end_y = y1 + side if y2 >= y1 else y1 - side
            return [x1, y1, end_x, end_y]

        left, right = sorted((x1, x2))
        top, bottom = sorted((y1, y2))
        middle_x = (left + right) / 2
        return [middle_x, top, left, bottom, right, bottom]

    def _normalize_bounds(
        self, x1: float, y1: float, x2: float, y2: float
    ) -> tuple[float, float, float, float]:
        """Return consistent left/top/right/bottom bounds for a selection."""
        left, right = sorted((x1, x2))
        top, bottom = sorted((y1, y2))
        return left, top, right, bottom

    def _selected_item_ids(self) -> list[int]:
        """Return all drawable items intersecting the current selection."""
        if self.selection_bounds is None:
            return []

        x1, y1, x2, y2 = self.selection_bounds
        return [
            item_id
            for item_id in self.canvas.find_overlapping(x1, y1, x2, y2)
            if self.DRAWABLE_TAG in self.canvas.gettags(item_id)
            and self.canvas.itemcget(item_id, "state") != "hidden"
        ]

    def _paste_at(self, x: int, y: int) -> None:
        """Paste the copied items so their selection origin starts at the click point."""
        for item_data in self.copied_items:
            self._create_item_from_data(item_data, x_offset=x, y_offset=y, layer_name=self.layer_var.get())

    def _snapshot_state(self) -> dict[str, Any]:
        """Capture layers and drawable items so undo/save can restore them later."""
        # Think of this like taking a quick picture of the whole project state.
        # That picture can be used for Undo or for saving the drawing to a file.
        return {
            "layers": self.layer_order[:],
            "hidden_layers": sorted(self.hidden_layers),
            "active_layer": self.layer_var.get(),
            "items": self._serialize_canvas(),
        }

    def _push_undo_state(self) -> None:
        """Store a snapshot of the current canvas so it can be restored later."""
        snapshot = self._snapshot_state()
        if self.undo_history and snapshot == self.undo_history[-1]:
            return
        self.undo_history.append(snapshot)
        if len(self.undo_history) > self.MAX_UNDO:
            self.undo_history.pop(0)

    def _serialize_canvas(self) -> list[dict[str, Any]]:
        """Convert every drawable canvas item into JSON-friendly data."""
        return [self._serialize_item(item_id) for item_id in self.canvas.find_withtag(self.DRAWABLE_TAG)]

    def _serialize_item(
        self, item_id: int, x_offset: float = 0.0, y_offset: float = 0.0
    ) -> dict[str, Any]:
        """Convert a single canvas item into a serializable dictionary."""
        raw_coords = self.canvas.coords(item_id)
        coords = [
            value - x_offset if index % 2 == 0 else value - y_offset
            for index, value in enumerate(raw_coords)
        ]
        layer = next(
            (tag.removeprefix(self.LAYER_PREFIX) for tag in self.canvas.gettags(item_id) if tag.startswith(self.LAYER_PREFIX)),
            self.layer_order[0],
        )

        options: dict[str, Any] = {}
        for option_name in ("fill", "outline", "width", "capstyle", "smooth", "splinesteps"):
            try:
                value = self.canvas.itemcget(item_id, option_name)
            except tk.TclError:
                continue
            if value != "":
                options[option_name] = value

        return {
            "type": self.canvas.type(item_id),
            "coords": coords,
            "options": options,
            "layer": layer,
        }

    def _restore_snapshot(self, snapshot: dict[str, Any] | list[dict[str, Any]]) -> None:
        """Replace the current drawing and layer stack with a previously saved snapshot."""
        state = snapshot if isinstance(snapshot, dict) else {"items": snapshot, "layers": ["Layer 1"], "hidden_layers": [], "active_layer": "Layer 1"}
        self.layer_order = list(state.get("layers") or ["Layer 1"])
        self.hidden_layers = set(state.get("hidden_layers", []))
        self.layer_counter = max(
            [int(name.split()[-1]) for name in self.layer_order if name.startswith("Layer ") and name.split()[-1].isdigit()],
            default=len(self.layer_order),
        )
        self.canvas.delete("all")
        for item_data in state.get("items", []):
            self._create_item_from_data(item_data)
        self.layer_var.set(state.get("active_layer", self.layer_order[-1]))
        if self.layer_var.get() not in self.layer_order:
            self.layer_var.set(self.layer_order[-1])
        self._clear_selection()
        self.preview_item = None
        self._refresh_layers()

    def _create_item_from_data(
        self, item_data: dict[str, Any], x_offset: float = 0.0, y_offset: float = 0.0, layer_name: str | None = None
    ) -> None:
        """Rebuild a line, shape, or spray dot from serialized data."""
        coords = [
            value + x_offset if index % 2 == 0 else value + y_offset
            for index, value in enumerate(item_data.get("coords", []))
        ]
        creator = getattr(self.canvas, f"create_{item_data.get('type')}", None)
        layer = layer_name or item_data.get("layer", self.layer_var.get())
        if layer not in self.layer_order:
            self.layer_order.append(layer)
        if creator:
            creator(
                *coords,
                **dict(
                    item_data.get("options", {}),
                    state="hidden" if layer in self.hidden_layers else "normal",
                    tags=(self.DRAWABLE_TAG, self._layer_tag(layer)),
                ),
            )

    def _clear_selection(self) -> None:
        """Remove the visible selection box and forget its bounds."""
        if self.selection_rect is not None:
            self.canvas.delete(self.selection_rect)
            self.selection_rect = None
        self.selection_bounds = None

    def _highlight_active_color(self) -> None:
        """Visually mark the selected preset color button for quick feedback."""
        for color, button in self.color_buttons.items():
            if color == self.current_color:
                button.configure(relief=tk.SUNKEN, bd=3)
            else:
                button.configure(relief=tk.RAISED, bd=2)

    def _update_feedback(self) -> None:
        """Refresh the active tool text and the visible color preview swatch."""
        preview_color = self.CANVAS_BG if self.current_tool == "eraser" else self.current_color
        layer_name = self.layer_var.get()
        hidden_note = " (hidden)" if layer_name in self.hidden_layers else ""
        self.tool_var.set(self.TOOL_LABELS.get(self.current_tool, self.current_tool.title()))
        self.color_preview.configure(bg=preview_color)
        self.feedback_var.set(
            f"Tool: {self.TOOL_LABELS.get(self.current_tool, self.current_tool.title())} | "
            f"Color: {self.current_color_name} | Layer: {layer_name}{hidden_note}"
        )
        self._highlight_active_color()


def main() -> None:
    """Start the painting program."""
    # This is the entry point that opens the app window.
    root = tk.Tk()
    PaintApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

