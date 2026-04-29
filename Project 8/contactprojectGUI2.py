import json
import os
import re
import tkinter as tk
from tkinter import messagebox
from tkinter import simpledialog
from tkinter import ttk

# File where all contacts are persistently stored.
# We intentionally point to the shared root-level contacts.json so this GUI
# and contactproject.py both read/write the same source of truth.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
CONTACTS_FILE = os.path.join(PROJECT_ROOT, "contacts.json")
LEGACY_CONTACTS_FILE = os.path.join(SCRIPT_DIR, "contacts.json")

# This app uses Tkinter (Python's built-in GUI library) to show contacts
# in a window instead of printing and reading from the terminal.

# ============ VALIDATION FUNCTIONS ============

def validate_phone(phone):
    """Return True when the input contains at least 10 numeric digits."""
    return len(re.sub(r'\D', '', phone)) >= 10

def validate_email(email):
    """Return True when email matches a basic user@domain.tld pattern."""
    return re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email) is not None

def validate_name(name):
    """Return True when name contains at least one non-space character."""
    return len(name.strip()) > 0

def validate_address(address):
    """Return True when address contains at least one non-space character."""
    return len(address.strip()) > 0

# ============ FILE OPERATIONS ============

def load_contacts():
    """Load contacts from the shared JSON file, with legacy fallback support."""
    # Prefer the shared file; fall back to the legacy local file so existing
    # data from older versions of this GUI is still readable.
    source_file = CONTACTS_FILE if os.path.exists(CONTACTS_FILE) else LEGACY_CONTACTS_FILE
    if not os.path.exists(source_file):
        return []

    try:
        with open(source_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        # Keep the app usable even if the JSON file is malformed.
        return []

def save_contacts(contacts):
    """Persist the full contacts list to disk and return success status."""
    try:
        with open(CONTACTS_FILE, "w", encoding="utf-8") as f:
            json.dump(contacts, f, indent=2)
        return True
    except Exception:
        return False

class ContactApp:
    """GUI contact manager with menu-based actions."""

    def __init__(self, root):
        """Initialize window state, build UI, and render current contacts."""
        # "root" is the main application window created in main().
        self.root = root
        self.root.title("Contact Management System")
        self.root.geometry("860x480")

        # Build screen parts, then load contacts into the table.
        self._build_menu()
        self._build_widgets()
        self.refresh_contacts()

    def _build_menu(self):
        """Create and attach the top menu bar and contact actions."""
        # Top menu bar (Contacts -> Add, Update, Delete, etc.).
        menubar = tk.Menu(self.root)

        contacts_menu = tk.Menu(menubar, tearoff=0)
        contacts_menu.add_command(label="Add Contact", command=self.add_contact)
        contacts_menu.add_command(label="Update Selected", command=self.update_selected)
        contacts_menu.add_command(label="Delete Selected", command=self.delete_selected)
        contacts_menu.add_separator()
        contacts_menu.add_command(label="Search by Name", command=self.search_contact)
        contacts_menu.add_command(label="Show All", command=self.refresh_contacts)
        contacts_menu.add_separator()
        contacts_menu.add_command(label="Exit", command=self.root.destroy)

        menubar.add_cascade(label="Contacts", menu=contacts_menu)
        self.root.config(menu=menubar)

    def _build_widgets(self):
        """Create table, scrollbar, and action buttons for contact management."""
        # Main container that holds the title and contact table.
        main_frame = ttk.Frame(self.root, padding=12)
        main_frame.pack(fill="both", expand=True)

        header = ttk.Label(main_frame, text="Saved Contacts", font=("Segoe UI", 14, "bold"))
        header.pack(anchor="w", pady=(0, 10))

        columns = ("name", "phone", "address", "email")
        # Treeview is a table-like widget in Tkinter.
        self.tree = ttk.Treeview(main_frame, columns=columns, show="headings", height=14)

        self.tree.heading("name", text="Name")
        self.tree.heading("phone", text="Phone")
        self.tree.heading("address", text="Address")
        self.tree.heading("email", text="Email")

        self.tree.column("name", width=150, anchor="w")
        self.tree.column("phone", width=140, anchor="w")
        self.tree.column("address", width=240, anchor="w")
        self.tree.column("email", width=260, anchor="w")

        # Vertical scrollbar so long contact lists can be scrolled.
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="left", fill="y")

        button_frame = ttk.Frame(self.root, padding=(12, 0, 12, 12))
        button_frame.pack(fill="x")

        # These buttons do the same actions as the menu items.
        ttk.Button(button_frame, text="Add", command=self.add_contact).pack(side="left", padx=4)
        ttk.Button(button_frame, text="Update", command=self.update_selected).pack(side="left", padx=4)
        ttk.Button(button_frame, text="Delete", command=self.delete_selected).pack(side="left", padx=4)
        ttk.Button(button_frame, text="Search", command=self.search_contact).pack(side="left", padx=4)
        ttk.Button(button_frame, text="Show All", command=self.refresh_contacts).pack(side="left", padx=4)

    def refresh_contacts(self, contacts=None):
        """Reload table rows from disk or from a provided filtered contacts list."""
        # If no custom list is provided, load and show all saved contacts.
        contacts_to_show = contacts if contacts is not None else load_contacts()

        # Clear every row before inserting new rows.
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Add each contact as one row in the table.
        for contact in contacts_to_show:
            self.tree.insert(
                "",
                "end",
                values=(
                    contact.get("name", ""),
                    contact.get("phone", ""),
                    contact.get("address", ""),
                    contact.get("email", ""),
                ),
            )

    def add_contact(self):
        """Open the add-contact dialog with empty input fields."""
        # Open a blank form for creating a new contact.
        self._open_contact_form(title="Add Contact")

    def update_selected(self):
        """Open the edit dialog pre-filled with the selected contact's values."""
        # Get selected row ids from the table.
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a contact to update.")
            return

        # Read values from the first selected row.
        values = self.tree.item(selected[0], "values")
        selected_contact = {
            "name": values[0],
            "phone": values[1],
            "address": values[2],
            "email": values[3],
        }
        # Open form pre-filled with this contact's current values.
        self._open_contact_form(title="Update Contact", original=selected_contact)

    def delete_selected(self):
        """Delete selected contacts from storage after user confirmation."""
        # Multiple rows can be selected for deletion.
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a contact to delete.")
            return

        if not messagebox.askyesno("Confirm Delete", "Delete selected contact(s)?"):
            return

        contacts = load_contacts()
        selected_contacts = []

        # Build a list of selected contacts from table values.
        for item_id in selected:
            values = self.tree.item(item_id, "values")
            selected_contacts.append(
                {
                    "name": values[0],
                    "phone": values[1],
                    "address": values[2],
                    "email": values[3],
                }
            )

        # Remove matching contacts from the saved list.
        deleted_count = 0
        for selected_contact in selected_contacts:
            for idx, contact in enumerate(contacts):
                if contact == selected_contact:
                    contacts.pop(idx)
                    deleted_count += 1
                    break

        if save_contacts(contacts):
            self.refresh_contacts()
            messagebox.showinfo("Deleted", f"Deleted {deleted_count} contact(s).")
        else:
            messagebox.showerror("Error", "Failed to save contact changes.")

    def search_contact(self):
        """Prompt for a name fragment and show only matching contacts."""
        # askstring opens a small popup asking for text input.
        term = simpledialog.askstring("Search", "Enter name to search:")
        if term is None:
            # User clicked Cancel.
            return

        # Case-insensitive search by name.
        term = term.strip().lower()
        all_contacts = load_contacts()
        found = [c for c in all_contacts if term in c.get("name", "").lower()]

        if not found:
            messagebox.showinfo("No Results", f"No contacts found matching '{term}'.")
            return

        self.refresh_contacts(found)

    def _open_contact_form(self, title, original=None):
        """Display add/edit form and save validated values to persistent storage."""
        # Toplevel creates a child window (a dialog) on top of the main window.
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.transient(self.root)
        # grab_set keeps focus on this dialog until it is closed.
        dialog.grab_set()

        frame = ttk.Frame(dialog, padding=12)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Name:").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Label(frame, text="Phone:").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Label(frame, text="Address:").grid(row=2, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Label(frame, text="Email:").grid(row=3, column=0, sticky="w", padx=(0, 8), pady=4)

        name_var = tk.StringVar(value="" if not original else original.get("name", ""))
        phone_var = tk.StringVar(value="" if not original else original.get("phone", ""))
        address_var = tk.StringVar(value="" if not original else original.get("address", ""))
        email_var = tk.StringVar(value="" if not original else original.get("email", ""))

        name_entry = ttk.Entry(frame, textvariable=name_var, width=40)
        phone_entry = ttk.Entry(frame, textvariable=phone_var, width=40)
        address_entry = ttk.Entry(frame, textvariable=address_var, width=40)
        email_entry = ttk.Entry(frame, textvariable=email_var, width=40)

        name_entry.grid(row=0, column=1, pady=4)
        phone_entry.grid(row=1, column=1, pady=4)
        address_entry.grid(row=2, column=1, pady=4)
        email_entry.grid(row=3, column=1, pady=4)

        def on_save():
            """Validate form input and add or update the contact record."""
            # Read text entered by the user.
            name = name_var.get().strip()
            phone = phone_var.get().strip()
            address = address_var.get().strip()
            email = email_var.get().strip()

            # Validate each field before saving.
            if not validate_name(name):
                messagebox.showerror("Validation Error", "Name cannot be empty.", parent=dialog)
                return
            if not validate_phone(phone):
                messagebox.showerror("Validation Error", "Phone must contain at least 10 digits.", parent=dialog)
                return
            if not validate_address(address):
                messagebox.showerror("Validation Error", "Address cannot be empty.", parent=dialog)
                return
            if not validate_email(email):
                messagebox.showerror("Validation Error", "Enter a valid email (example: user@example.com).", parent=dialog)
                return

            # This dictionary is exactly what will be stored in JSON.
            new_contact = {
                "name": name,
                "phone": phone,
                "address": address,
                "email": email,
            }

            contacts = load_contacts()

            if original is None:
                # Add mode: append as a brand-new contact.
                contacts.append(new_contact)
            else:
                # Update mode: find and replace the original contact.
                for idx, contact in enumerate(contacts):
                    if contact == original:
                        contacts[idx] = new_contact
                        break

            if save_contacts(contacts):
                # Refresh table so the user sees the latest data immediately.
                self.refresh_contacts()
                dialog.destroy()
            else:
                messagebox.showerror("Error", "Failed to save contact.", parent=dialog)

        action_text = "Add" if original is None else "Save"
        action_button = ttk.Button(frame, text=action_text, command=on_save)
        cancel_button = ttk.Button(frame, text="Cancel", command=dialog.destroy)
        action_button.grid(row=4, column=0, pady=(10, 0), sticky="w")
        cancel_button.grid(row=4, column=1, pady=(10, 0), sticky="e")

        # Put keyboard focus in Name field when dialog opens.
        name_entry.focus_set()


def main():
    """Start the GUI contact manager."""
    # Create the main window and start Tkinter's event loop.
    root = tk.Tk()
    ContactApp(root)
    root.mainloop()

# Entry point - only run main() if script is executed directly (not imported)
if __name__ == "__main__":
    main()
