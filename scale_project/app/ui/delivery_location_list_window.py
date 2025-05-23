import tkinter as tk
from tkinter import ttk, messagebox
from app.db.database import get_all_delivery_locations, get_db # Removed get_delivery_location_by_name
from app.db.models import DeliveryLocation 
from .delivery_location_add_window import AddDeliveryLocationWindow # To open in edit mode

class DeliveryLocationListWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("View Delivery Locations")
        self.geometry("650x400") # Wider for edit button

        self.grab_set()
        self.transient(parent)

        frame = ttk.Frame(self, padding="10")
        frame.pack(expand=True, fill=tk.BOTH)

        columns = ("id", "name", "address") # Added ID for fetching for edit
        self.tree = ttk.Treeview(frame, columns=columns, show="headings", height=12)
        
        self.tree.heading("id", text="ID")
        self.tree.heading("name", text="Name")
        self.tree.heading("address", text="Address")

        self.tree.column("id", width=40, anchor=tk.W, stretch=False)
        self.tree.column("name", width=150, anchor=tk.W)
        self.tree.column("address", width=350, anchor=tk.W)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        button_frame = ttk.Frame(self, padding=(10, 10, 10, 10))
        button_frame.pack(fill=tk.X)

        self.refresh_button = ttk.Button(button_frame, text="Refresh", command=self.load_delivery_locations)
        self.refresh_button.pack(side=tk.LEFT, padx=5)

        self.edit_button = ttk.Button(button_frame, text="Edit Selected", command=self.edit_selected_delivery_location, state=tk.DISABLED)
        self.edit_button.pack(side=tk.LEFT, padx=5)

        self.close_button = ttk.Button(button_frame, text="Close", command=self.on_closing)
        self.close_button.pack(side=tk.RIGHT, padx=5)
        
        self.tree.bind("<<TreeviewSelect>>", self.on_delivery_location_select_in_tree)

        self.load_delivery_locations()

        if hasattr(self.parent, 'register_delivery_location_list_window'):
            self.parent.register_delivery_location_list_window(self)
        
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_delivery_location_select_in_tree(self, event=None):
        selected_items = self.tree.selection()
        if selected_items:
            self.edit_button.config(state=tk.NORMAL)
        else:
            self.edit_button.config(state=tk.DISABLED)

    def edit_selected_delivery_location(self):
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("No Selection", "Please select a delivery location to edit.", parent=self)
            return
        
        selected_item = selected_items[0]
        loc_id_str = self.tree.item(selected_item, "values")[0]
        try:
            loc_id = int(loc_id_str)
        except (ValueError, TypeError):
            messagebox.showerror("Error", "Could not retrieve valid ID for editing.", parent=self)
            return

        db_session = next(get_db())
        try:
            # Fetch the DeliveryLocation object by ID
            loc_to_edit = db_session.query(DeliveryLocation).filter(DeliveryLocation.id == loc_id).first()

            if loc_to_edit:
                edit_dialog = AddDeliveryLocationWindow(self, delivery_location_to_edit=loc_to_edit)
                self.wait_window(edit_dialog)
                # load_delivery_locations is called by AddDeliveryLocationWindow via parent.load_delivery_locations()
            else:
                messagebox.showerror("Error", f"Delivery Location with ID {loc_id} not found.", parent=self)
                self.load_delivery_locations() # Refresh list
        finally:
            db_session.close()

    def load_delivery_locations(self):
        self.edit_button.config(state=tk.DISABLED)
        for item in self.tree.get_children():
            self.tree.delete(item)

        db_session = next(get_db())
        try:
            locations = get_all_delivery_locations(db_session)
            if not locations:
                self.tree.insert("", tk.END, values=("No delivery locations found.", "", ""))
            else:
                for loc in locations:
                    self.tree.insert("", tk.END, values=(
                        loc.id, # Store ID
                        loc.name,
                        loc.address if loc.address else "N/A",
                    ))
        except Exception as e:
            messagebox.showerror("Load Error", f"Failed to load delivery locations: {e}", parent=self)
        finally:
            db_session.close()

    def on_closing(self):
        if hasattr(self.parent, 'unregister_delivery_location_list_window'):
            self.parent.unregister_delivery_location_list_window(self)
        self.destroy()

if __name__ == '__main__':
    root = tk.Tk()
    root.title("Main App (dummy for DelLocListWindow)")

    from app.db.database import create_db_and_tables, add_delivery_location
    create_db_and_tables()

    db = next(get_db())
    try:
        if not get_all_delivery_locations(db):
            add_delivery_location(db, "Site Alpha", "123 Test Dr")
            add_delivery_location(db, "Site Beta", "456 Production Ave")
            add_delivery_location(db, "Remote Yard C", None)
    finally:
        db.close()
    
    def open_delivery_location_list_dialog():
        dialog = DeliveryLocationListWindow(root)

    ttk.Button(root, text="View Delivery Locations", command=open_delivery_location_list_dialog).pack(pady=20)
    
    root.mainloop()
