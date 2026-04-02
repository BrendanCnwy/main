import pandas as pd
import os
from datetime import datetime
import matplotlib.pyplot as plt

# Configuration
# This is the file that will store all expense data on disk.
FILE_NAME = "expenses.csv"


def initialize_df():
    """Create the CSV file if it does not already exist.

    If the file exists, load the contents into a Pandas DataFrame.
    If it does not exist, create an empty CSV with the correct columns.
    """
    if os.path.exists(FILE_NAME):
        # Load existing expenses from the CSV file.
        return pd.read_csv(FILE_NAME)
    else:
        # Create a new empty DataFrame with the right column names.
        columns = ["Date", "Category", "Description", "Amount"]
        df = pd.DataFrame(columns=columns)
        df.to_csv(FILE_NAME, index=False)
        return df


def add_expense(category, description, amount):
    """Add a new expense to the CSV file."""
    # Read the current data from the file.
    df = pd.read_csv(FILE_NAME)

    new_entry = {
        # Record the exact date and time when the expense was added.
        "Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Category": category,
        "Description": description,
        # Convert the typed amount to a number so it can be summed later.
        "Amount": float(amount)
    }

    # Create a one-row DataFrame and append it to the existing data.
    df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
    df.to_csv(FILE_NAME, index=False)
    print("\n✅ Expense added successfully!")


def view_expenses():
    """Show all expenses saved in the file."""
    df = pd.read_csv(FILE_NAME)
    if df.empty:
        # If there is no data yet, tell the user.
        print("\n📭 No expenses recorded yet.")
        return

    print("\n--- Expense List ---")
    # Reset index for display so rows are numbered from 0 cleanly.
    print(df.reset_index(drop=True))
    print(f"\nTotal records: {len(df)}")


def view_summary():
    """Print summary statistics for the saved expenses."""
    df = pd.read_csv(FILE_NAME)

    if df.empty:
        print("\n📭 No expenses recorded yet.")
        return

    # Show the raw expense table first.
    print("\n--- Current Expenses ---")
    print(df)

    # Calculate totals using the Amount column.
    total = df["Amount"].sum()
    average = df["Amount"].mean()

    print(f"\n💰 Total Spent: ${total:.2f}")
    print(f"📊 Average Expense: ${average:.2f}")

    # Group the expenses by category and add up each category.
    print("\n--- Spending by Category ---")
    print(df.groupby("Category")["Amount"].sum())


def edit_expense():
    """Allow the user to update an existing expense entry."""
    df = pd.read_csv(FILE_NAME)
    if df.empty:
        print("\n📭 No expenses recorded yet.")
        return

    print("\n--- Edit Expense ---")
    print(df)

    # Ask the user which row should be changed.
    try:
        loc = int(input("Enter index to edit: "))
    except ValueError:
        print("Invalid index.")
        return

    if loc not in df.index:
        print("Index not found.")
        return

    # Load the current row so we can show existing values.
    row = df.loc[loc]
    category = input(f"Category [{row['Category']}]: ") or row["Category"]
    description = input(f"Description [{row['Description']}]: ") or row["Description"]
    amount_input = input(f"Amount [{row['Amount']}]: ")
    amount = float(amount_input) if amount_input else float(row["Amount"])

    # Replace the old values with the new ones.
    df.at[loc, "Category"] = category
    df.at[loc, "Description"] = description
    df.at[loc, "Amount"] = amount
    df.to_csv(FILE_NAME, index=False)

    print("\n✅ Expense updated successfully!")
    view_summary()


def delete_expense():
    """Remove one expense row from the CSV file."""
    df = pd.read_csv(FILE_NAME)
    if df.empty:
        print("\n📭 No expenses recorded yet.")
        return

    print("\n--- Delete Expense ---")
    print(df)

    try:
        loc = int(input("Enter index to delete: "))
    except ValueError:
        print("Invalid index.")
        return

    if loc not in df.index:
        print("Index not found.")
        return

    # Drop the chosen row and re-number the remaining rows.
    df = df.drop(index=loc).reset_index(drop=True)
    df.to_csv(FILE_NAME, index=False)
    print("\n✅ Expense deleted successfully!")
    view_summary()


def sort_expenses():
    """Sort the saved expenses by date, category, description, or amount."""
    df = pd.read_csv(FILE_NAME)
    if df.empty:
        print("\n📭 No expenses recorded yet.")
        return

    print("\nSort by:\n1. Date\n2. Category\n3. Description\n4. Amount")
    choice = input("Choose sort field: ")
    field_map = {
        "1": "Date",
        "2": "Category",
        "3": "Description",
        "4": "Amount"
    }

    field = field_map.get(choice)
    if not field:
        print("Invalid choice.")
        return

    # Ask whether the user wants ascending or descending order.
    order = input("Ascending? (y/n): ").lower().startswith("y")

    if field == "Date":
        # Convert the Date column from text into real date objects.
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

    # Sort the DataFrame by the chosen column.
    df = df.sort_values(by=field, ascending=order).reset_index(drop=True)

    if field == "Date":
        # Convert the dates back to readable text format.
        df["Date"] = df["Date"].dt.strftime("%Y-%m-%d %H:%M:%S")

    df.to_csv(FILE_NAME, index=False)
    print(f"\n✅ Expenses sorted by {field} ({'ascending' if order else 'descending'}).")
    view_expenses()


def plot_expenses():
    """Make a pie chart of expense totals by category."""
    df = pd.read_csv(FILE_NAME)
    if df.empty:
        print("\n📭 No expenses recorded yet.")
        return

    # Add up the amounts for each category.
    category_totals = df.groupby("Category")["Amount"].sum()

    # Create a chart that shows how the total is split across categories.
    plt.figure(figsize=(8, 8))
    plt.pie(category_totals, labels=category_totals.index, autopct="%1.1f%%", startangle=90)
    plt.title("Total Expense by Category")
    plt.axis("equal")
    plt.show()


def main():
    """Show the menu and let the user choose commands."""
    initialize_df()

    while True:
        # Print the menu options every time the user returns.
        print("\n--- 📈 Expense Tracker CLI ---")
        print("1. Add Expense")
        print("2. View Expenses")
        print("3. View Summary")
        print("4. Edit Expense")
        print("5. Delete Expense")
        print("6. Sort Expense List")
        print("7. Plot Expenses")
        print("8. Exit")

        choice = input("Select an option: ").strip()

        # If the user just presses Enter, do not print an error message.
        if choice == "":
            continue

        if choice == "1":
            cat = input("Enter Category (e.g., Food, Rent, Fun): ")
            desc = input("Short Description: ")
            amt = input("Amount: ")
            add_expense(cat, desc, amt)
        elif choice == "2":
            view_expenses()
        elif choice == "3":
            view_summary()
        elif choice == "4":
            edit_expense()
        elif choice == "5":
            delete_expense()
        elif choice == "6":
            sort_expenses()
        elif choice == "7":
            plot_expenses()
        elif choice == "8":
            print("Goodbye!")
            break
        else:
            # This message appears if the user types anything other than 1-8.
            print("Invalid choice, try again.")


if __name__ == "__main__":
    # Only run the program when this file is executed directly.

    main()