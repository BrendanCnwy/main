import json
import os
import re

# File where all contacts are persistently stored.
# Keep CLI and GUI on one shared JSON path.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONTACTS_FILE = os.path.join(SCRIPT_DIR, "contacts.json")
LEGACY_CONTACTS_FILE = os.path.join(SCRIPT_DIR, "Project 8", "contacts.json")

# ============ VALIDATION FUNCTIONS ============

def validate_phone(phone):
    """Ensure phone number has at least 10 digits."""
    return len(re.sub(r'\D', '', phone)) >= 10

def validate_email(email):
    """Check if email matches standard format (user@domain.ext)."""
    return re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email) is not None

def validate_name(name):
    """Ensure name is not empty or whitespace."""
    return len(name.strip()) > 0

def validate_address(address):
    """Ensure address is not empty or whitespace."""
    return len(address.strip()) > 0

# ============ FILE OPERATIONS ============

def load_contacts():
    """Load all contacts from JSON file. Returns empty list if file doesn't exist."""
    source_file = CONTACTS_FILE if os.path.exists(CONTACTS_FILE) else LEGACY_CONTACTS_FILE
    if not os.path.exists(source_file):
        return []

    try:
        with open(source_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_contacts(contacts):
    """Save all contacts to JSON file with error handling."""
    try:
        with open(CONTACTS_FILE, "w", encoding="utf-8") as f:
            json.dump(contacts, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving contacts: {e}"); return False

# ============ CONTACT MANAGEMENT FUNCTIONS ============

def add_contact():
    """Add a new contact with validation for Name, Phone, Address, and Email."""
    contacts = load_contacts()
    
    # Repeatedly prompt until valid name is entered
    while True:
        name = input("Enter Name: ").strip()
        if validate_name(name):
            break
        print("⚠️  Alert: Please enter a valid name (cannot be empty).\n")
    
    # Repeatedly prompt until valid phone number is entered
    while True:
        phone = input("Enter Phone Number: ").strip()
        if validate_phone(phone):
            break
        print("⚠️  Alert: Please enter a valid phone number (minimum 10 digits).\n")
    
    # Repeatedly prompt until valid address is entered
    while True:
        address = input("Enter Address: ").strip()
        if validate_address(address):
            break
        print("⚠️  Alert: Please enter a valid address (cannot be empty).\n")
    
    # Repeatedly prompt until valid email is entered
    while True:
        email = input("Enter Email: ").strip()
        if validate_email(email):
            break
        print("⚠️  Alert: Please enter a valid email address (e.g., user@example.com).\n")
    
    # Create contact dictionary and add to contacts list
    contact = {"name": name, "phone": phone, "address": address, "email": email}
    contacts.append(contact)
    # Save to file and provide feedback
    if save_contacts(contacts):
        print(f"\n✓ Contact '{name}' saved to contacts.json successfully!\n")
    else:
        print(f"\n✗ Failed to save contact '{name}'.\n")

def display_contacts():
    """Display all contacts with detailed formatting from contacts.json."""
    contacts = load_contacts()
    # Exit early if no contacts exist
    if not contacts:
        print("\n❌ No contacts found.\n")
        return
    
    # Print header with total count
    print("\n" + "="*70)
    print(" "*20 + "SAVED CONTACTS FROM contacts.json")
    print("="*70)
    print(f"Total Contacts: {len(contacts)}\n")
    
    # Display each contact with all details
    for i, c in enumerate(contacts, 1):
        print(f"{'─'*70}\nContact #{i}\n{'─'*70}")
        # Loop through each field (name, phone, address, email) for cleaner display
        for key in ['name', 'phone', 'address', 'email']:
            print(f"  {key.title()}:     {c.get(key, 'N/A')}")
    
    print("\n" + "="*70 + "\n")

def search_contact():
    """Search for contacts by partial name match (case-insensitive)."""
    contacts = load_contacts()
    if not contacts:
        print("\n❌ No contacts found.\n")
        return
    
    # Get search term and filter contacts by partial name match
    search_name = input("Enter name to search: ").strip().lower()
    found = [c for c in contacts if search_name in c['name'].lower()]
    
    # Exit early if no matches found
    if not found:
        print(f"\n❌ No contacts found matching '{search_name}'.\n")
        return
    
    # Display matching contacts
    print("\n" + "="*70)
    print(f" "*15 + f"SEARCH RESULTS FOR '{search_name}'")
    print("="*70 + "\n")
    
    for i, c in enumerate(found, 1):
        print(f"Contact #{i}\n{'─'*70}")
        for key in ['name', 'phone', 'address', 'email']:
            print(f"  {key.title()}:     {c.get(key, 'N/A')}")
        print()
    
    print("="*70 + "\n")

def delete_contact():
    """Delete one or more contacts by partial name match with confirmation."""
    contacts = load_contacts()
    if not contacts:
        print("\n❌ No contacts found.\n")
        return
    
    # Get search term and identify matching contacts
    search_name = input("Enter name of contact to delete: ").strip().lower()
    initial_count = len(contacts)
    
    # Filter out matching contacts (keep non-matching ones)
    updated_contacts = [c for c in contacts if search_name not in c['name'].lower()]
    
    # Exit if no matches found
    if len(updated_contacts) == initial_count:
        print(f"\n❌ No contacts found matching '{search_name}'.\n")
        return
    
    deleted_count = initial_count - len(updated_contacts)
    
    # Ask user for confirmation before deleting
    confirm = input(f"\nDelete {deleted_count} contact(s)? (y/n): ").strip().lower()
    if confirm not in ('y', 'yes'):
        print("❌ Deletion cancelled.\n")
        return
    
    # Remove contacts and save to file
    if save_contacts(updated_contacts):
        print(f"✓ {deleted_count} contact(s) deleted successfully from contacts.json!\n")
    else:
        print("✗ Failed to delete contact(s).\n")

def update_contact():
    """Find a contact by name and allow updating its fields."""
    contacts = load_contacts()
    if not contacts:
        print("\n❌ No contacts found.\n")
        return
    
    search_name = input("Enter name of contact to update: ").strip().lower()
    matches = [c for c in contacts if search_name in c['name'].lower()]
    if not matches:
        print(f"\n❌ No contacts found matching '{search_name}'.\n")
        return
    
    # If multiple matches, show list and pick one
    chosen = None
    if len(matches) > 1:
        print("\nMultiple contacts found:\n")
        for idx, c in enumerate(matches, 1):
            print(f"{idx}. {c['name']} - {c.get('phone','')} - {c.get('email','')}")
        sel = input("Select number to update: ").strip()
        if sel.isdigit() and 1 <= int(sel) <= len(matches):
            chosen = matches[int(sel)-1]
        else:
            print("Invalid selection. Aborting update.\n")
            return
    else:
        chosen = matches[0]
    
    # Update fields one by one; blank input leaves value unchanged
    print("Leave blank to keep current value.")
    new_name = input(f"Name [{chosen['name']}]: ").strip() #name update
    if new_name and validate_name(new_name):
        chosen['name'] = new_name
    new_phone = input(f"Phone [{chosen['phone']}]: ").strip() #phone number update
    if new_phone:
        if validate_phone(new_phone):
            chosen['phone'] = new_phone
        else:
            print("Invalid phone format, keeping old value.") #phone number failsafe
    new_address = input(f"Address [{chosen['address']}]: ").strip() #address update
    if new_address and validate_address(new_address):
        chosen['address'] = new_address
    new_email = input(f"Email [{chosen['email']}]: ").strip() #email update
    if new_email:
        if validate_email(new_email):
            chosen['email'] = new_email
        else:
            print("Invalid email format, keeping old value.") #email failsafe
    
    if save_contacts(contacts):
        print("\n✓ Contact updated successfully!\n") #confirmation of successful update
    else:
        print("\n✗ Failed to save updated contact.\n") #confirmation of failed update

def main():
    """Main program loop for contact management."""
    print("Welcome to the Contact Management System!")
    while True:
        print("\nOptions:")
        print("add")
        print("delete")
        print("view")
        print("search")
        print("exit")
        choice = input("Enter option: ").strip().lower()
        if choice == "add":
            add_contact()
        elif choice == "view":
            display_contacts()
        elif choice == "search":
            search_contact()
        elif choice == "delete":
            delete_contact()
        elif choice == "exit":
            print("Goodbye!")
            break
        else:
            print("Invalid option. Please try again.")

# Entry point - only run main() if script is executed directly (not imported)
if __name__ == "__main__":
    main()
