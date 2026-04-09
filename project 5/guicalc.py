import tkinter as tk

import ttkbootstrap as ttk


class TipCalculatorApp:
	"""A modern tip calculator built with ttkbootstrap."""

	def __init__(self, root: ttk.Window) -> None:
		self.root = root
		self.root.title("Tip & Split Calculator")
		self.root.geometry("620x520")
		self.root.resizable(True, True)

		self.bill_var = tk.StringVar()
		self.tip_var = tk.StringVar(value="15")
		self.custom_tip_var = tk.StringVar()
		self.diners_var = tk.StringVar(value="1")
		self.tip_amount_var = tk.StringVar(value="$0.00")
		self.total_with_tip_var = tk.StringVar(value="$0.00")
		self.per_person_var = tk.StringVar(value="$0.00")
		self.status_var = tk.StringVar(value="Enter values to calculate.")

		self.root.columnconfigure(0, weight=1)
		self.root.rowconfigure(0, weight=1)

		outer_frame = ttk.Frame(self.root)
		outer_frame.grid(row=0, column=0, sticky="nsew")
		outer_frame.columnconfigure(0, weight=1)
		outer_frame.rowconfigure(0, weight=1)

		self.scroll_canvas = tk.Canvas(outer_frame, highlightthickness=0, bg="#f8f9fa")
		self.scroll_canvas.grid(row=0, column=0, sticky="nsew")

		self.v_scrollbar = ttk.Scrollbar(
			outer_frame,
			orient="vertical",
			command=self.scroll_canvas.yview,
			bootstyle="round",
		)
		self.v_scrollbar.grid(row=0, column=1, sticky="ns")
		self.scroll_canvas.configure(yscrollcommand=self.v_scrollbar.set)

		container = ttk.Frame(self.scroll_canvas, padding=18)
		self.scroll_window = self.scroll_canvas.create_window((0, 0), window=container, anchor="nw")
		container.columnconfigure(0, weight=1)
		container.bind("<Configure>", self._update_scroll_region)
		self.scroll_canvas.bind("<Configure>", self._resize_scrollable_frame)
		self.root.bind_all("<MouseWheel>", self._on_mousewheel)

		header = ttk.Frame(container, padding=18, bootstyle="light")
		header.grid(row=0, column=0, sticky="ew")
		header.columnconfigure(0, weight=1)

		ttk.Label(
			header,
			text="Tip & Split Calculator",
			font=("Segoe UI", 20, "bold"),
			bootstyle="primary",
		).grid(row=0, column=0, sticky="w")
		ttk.Label(
			header,
			text="A cleaner, modern bill-splitting calculator powered by ttkbootstrap.",
			bootstyle="secondary",
		).grid(row=1, column=0, sticky="w", pady=(4, 0))

		form_box = ttk.Labelframe(container, text="Bill Details", padding=16, bootstyle="info")
		form_box.grid(row=1, column=0, sticky="ew", pady=(14, 10))
		form_box.columnconfigure(1, weight=1)

		ttk.Label(form_box, text="Meal total ($)", bootstyle="secondary").grid(
			row=0, column=0, sticky="w", pady=8
		)
		self.bill_entry = ttk.Entry(form_box, textvariable=self.bill_var, width=24)
		self.bill_entry.grid(row=0, column=1, sticky="ew", pady=8)

		ttk.Label(form_box, text="Tip percentage (%)", bootstyle="secondary").grid(
			row=1, column=0, sticky="w", pady=8
		)
		self.tip_selector = ttk.Combobox(
			form_box,
			textvariable=self.tip_var,
			values=("10", "15", "20", "Custom"),
			state="readonly",
			width=22,
		)
		self.tip_selector.grid(row=1, column=1, sticky="ew", pady=8)

		ttk.Label(form_box, text="Custom tip (%)", bootstyle="secondary").grid(
			row=2, column=0, sticky="w", pady=8
		)
		self.custom_tip_entry = ttk.Entry(
			form_box,
			textvariable=self.custom_tip_var,
			width=24,
			state="disabled",
		)
		self.custom_tip_entry.grid(row=2, column=1, sticky="ew", pady=8)

		ttk.Label(form_box, text="Number of guests", bootstyle="secondary").grid(
			row=3, column=0, sticky="w", pady=8
		)
		self.diners_selector = ttk.Spinbox(
			form_box,
			from_=1,
			to=99,
			textvariable=self.diners_var,
			width=22,
		)
		self.diners_selector.grid(row=3, column=1, sticky="ew", pady=8)

		button_row = ttk.Frame(container)
		button_row.grid(row=2, column=0, sticky="ew", pady=(2, 10))
		button_row.columnconfigure((0, 1), weight=1)

		ttk.Button(
			button_row,
			text="Clear",
			command=self.clear,
			bootstyle="secondary-outline",
		).grid(row=0, column=0, sticky="ew", padx=(0, 6))
		ttk.Button(
			button_row,
			text="Exit",
			command=self.root.destroy,
			bootstyle="danger",
		).grid(row=0, column=1, sticky="ew", padx=(6, 0))

		results_box = ttk.Labelframe(container, text="Results", padding=16, bootstyle="success")
		results_box.grid(row=3, column=0, sticky="ew")
		results_box.columnconfigure(1, weight=1)

		result_rows = (
			("Tip amount:", self.tip_amount_var),
			("Total with tip:", self.total_with_tip_var),
			("Amount per diner:", self.per_person_var),
		)
		for row, (label_text, value_var) in enumerate(result_rows):
			ttk.Label(results_box, text=label_text, bootstyle="secondary").grid(
				row=row, column=0, sticky="w", pady=6
			)
			ttk.Label(
				results_box,
				textvariable=value_var,
				font=("Segoe UI", 12, "bold"),
				bootstyle="success",
			).grid(row=row, column=1, sticky="e", pady=6)

		ttk.Label(
			container,
			textvariable=self.status_var,
			bootstyle="danger",
		).grid(row=4, column=0, sticky="w", pady=(10, 0))

		self.bill_entry.focus_set()
		for var in (self.bill_var, self.tip_var, self.custom_tip_var, self.diners_var):
			var.trace_add("write", self.on_value_changed)

		self.update_custom_tip_state()
		self.calculate()

	def on_value_changed(self, *_args: object) -> None:
		"""Recalculate whenever an input changes."""
		self.update_custom_tip_state()
		self.calculate()

	def _update_scroll_region(self, _event: object) -> None:
		"""Keep the scrollable area sized to the full content height."""
		self.scroll_canvas.configure(scrollregion=self.scroll_canvas.bbox("all"))

	def _resize_scrollable_frame(self, event: tk.Event) -> None:
		"""Make the inner content frame match the visible canvas width."""
		self.scroll_canvas.itemconfigure(self.scroll_window, width=event.width)

	def _on_mousewheel(self, event: tk.Event) -> None:
		"""Allow the mouse wheel to move the window up and down."""
		if self.scroll_canvas.winfo_exists():
			self.scroll_canvas.yview_scroll(int(-event.delta / 120), "units")

	def update_custom_tip_state(self) -> None:
		"""Enable the custom tip box only when needed."""
		is_custom = self.tip_var.get() == "Custom"
		self.custom_tip_entry.configure(state="normal" if is_custom else "disabled")
		if not is_custom and self.custom_tip_var.get():
			self.custom_tip_var.set("")

	def reset_outputs(self, message: str) -> None:
		"""Reset displayed totals and show a helper message."""
		self.tip_amount_var.set("$0.00")
		self.total_with_tip_var.set("$0.00")
		self.per_person_var.set("$0.00")
		self.status_var.set(message)

	def calculate(self) -> None:
		"""Compute the bill totals from the current form values."""
		bill_text = self.bill_var.get().strip()
		if bill_text == "":
			self.reset_outputs("Enter values to calculate.")
			return

		try:
			bill_amount = float(bill_text)
		except ValueError:
			self.reset_outputs("Meal total must be a numeric value.")
			return
		if bill_amount < 0:
			self.reset_outputs("Meal total cannot be negative.")
			return

		if self.tip_var.get() == "Custom":
			custom_tip_text = self.custom_tip_var.get().strip()
			if custom_tip_text == "":
				self.reset_outputs("Enter a custom tip percentage.")
				return
			try:
				tip_percentage = float(custom_tip_text)
			except ValueError:
				self.reset_outputs("Custom tip must be a numeric value.")
				return
		else:
			tip_percentage = float(self.tip_var.get())
		if tip_percentage < 0:
			self.reset_outputs("Tip percentage cannot be negative.")
			return

		try:
			diners = int(self.diners_var.get().strip())
		except ValueError:
			self.reset_outputs("Number of guests must be a whole number.")
			return
		if diners <= 0:
			self.reset_outputs("Number of guests must be at least 1.")
			return

		tip_amount = bill_amount * (tip_percentage / 100)
		total_with_tip = bill_amount + tip_amount
		per_person = total_with_tip / diners

		self.tip_amount_var.set(f"${tip_amount:,.2f}")
		self.total_with_tip_var.set(f"${total_with_tip:,.2f}")
		self.per_person_var.set(f"${per_person:,.2f}")
		self.status_var.set("")

	def clear(self) -> None:
		"""Reset the calculator back to its defaults."""
		self.bill_var.set("")
		self.tip_var.set("15")
		self.custom_tip_var.set("")
		self.diners_var.set("1")
		self.update_custom_tip_state()
		self.bill_entry.focus_set()


def main() -> None:
	root = ttk.Window(themename="flatly")
	TipCalculatorApp(root)
	root.mainloop()


if __name__ == "__main__":
	main()
