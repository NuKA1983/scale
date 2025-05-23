import tkinter as tk
from tkinter import ttk, messagebox
from app.db.database import get_all_trucks_mru_ordered, get_db, get_truck_by_id # Used new MRU func, added get_truck_by_id
from app.db.models import Truck 
from .truck_add_window import AddTruckWindow # To open in edit mode

class TruckListWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("View Trucks")
        self.geometry("800x450") # Wider for more data / edit button

        self.grab_set()
        self.transient(parent)

        frame = ttk.Frame(self, padding="10")
        frame.pack(expand=True, fill=tk.BOTH)

        columns = ("id", "unit_id", "company_name", "asga_id", "tare_weight", "max_weight", "last_used")
        self.tree = ttk.Treeview(frame, columns=columns, show="headings", height=15)
        
        self.tree.heading("id", text="ID")
        self.tree.heading("unit_id", text="Unit ID")
        self.tree.heading("company_name", text="Company Name")
        self.tree.heading("asga_id", text="ASGA ID")
        self.tree.heading("tare_weight", text="Tare (kg)")
        self.tree.heading("max_weight", text="Max (kg)")
        self.tree.heading("last_used", text="Last Used")

        self.tree.column("id", width=40, anchor=tk.W, stretch=False)
        self.tree.column("unit_id", width=100, anchor=tk.W)
        self.tree.column("company_name", width=200, anchor=tk.W)
        self.tree.column("asga_id", width=100, anchor=tk.W)
        self.tree.column("tare_weight", width=100, anchor=tk.E)
        self.tree.column("max_weight", width=100, anchor=tk.E)
        self.tree.column("last_used", width=120, anchor=tk.CENTER)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True) # Changed pack to LEFT

        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y) 

        button_frame = ttk.Frame(self, padding=(10, 10, 10, 10)) # Padding around buttons
        button_frame.pack(fill=tk.X)

        self.refresh_button = ttk.Button(button_frame, text="Refresh", command=self.load_trucks)
        self.refresh_button.pack(side=tk.LEFT, padx=5)
        
        self.edit_button = ttk.Button(button_frame, text="Edit Selected Truck", command=self.edit_selected_truck, state=tk.DISABLED)
        self.edit_button.pack(side=tk.LEFT, padx=5)

        self.close_button = ttk.Button(button_frame, text="Close", command=self.on_closing)
        self.close_button.pack(side=tk.RIGHT, padx=5)
        
        self.tree.bind("<<TreeviewSelect>>", self.on_truck_select_in_tree) # Event to enable/disable edit button

        self.load_trucks()

        if hasattr(self.parent, 'register_truck_list_window'):
            self.parent.register_truck_list_window(self)
        
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_truck_select_in_tree(self, event=None):
        selected_items = self.tree.selection()
        if selected_items: # If something is selected
            self.edit_button.config(state=tk.NORMAL)
        else:
            self.edit_button.config(state=tk.DISABLED)

    def edit_selected_truck(self):
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("No Selection", "Please select a truck from the list to edit.", parent=self)
            return
        
        selected_item = selected_items[0] # Get the first (and likely only) selected item
        # Assuming the 'id' is the first value in the 'values' tuple for the item
        truck_id_str = self.tree.item(selected_item, "values")[0] 
        try:
            truck_id = int(truck_id_str)
        except (ValueError, TypeError):
            messagebox.showerror("Error", "Could not retrieve valid truck ID for editing.", parent=self)
            return

        db_session = next(get_db())
        try:
            truck_to_edit = get_truck_by_id(db_session, truck_id) # Fetch the full truck object
            if truck_to_edit:
                # Open AddTruckWindow in edit mode, passing 'self' as parent
                # AddTruckWindow will handle its own db session for the update
                edit_dialog = AddTruckWindow(self, truck_to_edit=truck_to_edit) 
                self.wait_window(edit_dialog) # Wait for edit dialog to close
                # load_trucks() is called by AddTruckWindow through parent.load_trucks() after successful edit
            else:
                messagebox.showerror("Error", f"Truck with ID {truck_id} not found in database.", parent=self)
                self.load_trucks() # Refresh list in case it was deleted by another user
        finally:
            db_session.close()


    def load_trucks(self):
        self.edit_button.config(state=tk.DISABLED) # Disable button during load
        for item in self.tree.get_children():
            self.tree.delete(item)

        db_session = next(get_db())
        try:
            trucks = get_all_trucks_mru_ordered(db_session) # Use MRU ordered list
            if not trucks:
                self.tree.insert("", tk.END, values=("No trucks found.", "", "", "", "", "", ""))
            else:
                for truck in trucks:
                    last_used_str = truck.last_used_timestamp.strftime("%Y-%m-%d %H:%M") if truck.last_used_timestamp else "Never"
                    self.tree.insert("", tk.END, values=(
                        truck.id, # Storing ID directly as first value
                        truck.unit_id,
                        truck.company_name,
                        truck.asga_id if truck.asga_id else "N/A",
                        f"{truck.tare_weight:.2f}",
                        f"{truck.max_allowed_weight:.2f}",
                        last_used_str
                    ))
        except Exception as e:
            messagebox.showerror("Load Error", f"Failed to load trucks: {e}", parent=self)
        finally:
            db_session.close()

    def on_closing(self):
        if hasattr(self.parent, 'unregister_truck_list_window'):
            self.parent.unregister_truck_list_window(self)
        self.destroy()

if __name__ == '__main__':
    root = tk.Tk()
    root.title("Main App (dummy for TruckListWindow)")
    
    from app.db.database import create_db_and_tables, add_truck
    create_db_and_tables() # Ensure schema is up-to-date

    # Populate with some data for testing
    db = next(get_db())
    try:
        if not get_all_trucks_mru_ordered(db):
             add_truck(db, "TRK001", "Alpha Trans", 10500.50, 25000.00, "ASGA01")
             add_truck(db, "TRK002", "Beta Logistics", 12000.00, 28000.00)
             add_truck(db, "TRK003", "Gamma Haulers", 9800.75, 22000.50, "ASGA03")
    finally:
        db.close()

    def open_truck_list_dialog():
        dialog = TruckListWindow(root)
        # root.wait_window(dialog) # Not waiting if it's modal via grab_set

    ttk.Button(root, text="View Trucks", command=open_truck_list_dialog).pack(pady=20)
    
    root.mainloop()
