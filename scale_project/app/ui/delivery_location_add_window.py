import tkinter as tk
from tkinter import ttk, messagebox, Text
from app.db.database import add_delivery_location, update_delivery_location, get_db # Added update_delivery_location
from app.db.models import DeliveryLocation # For type hinting

class AddDeliveryLocationWindow(tk.Toplevel):
    def __init__(self, parent, delivery_location_to_edit: DeliveryLocation | None = None): # Accept delivery_location_to_edit
        super().__init__(parent)
        self.parent = parent
        self.delivery_location_to_edit = delivery_location_to_edit
        self.delivery_location_id_for_edit = None

        if self.delivery_location_to_edit:
            self.title("Edit Delivery Location")
            self.delivery_location_id_for_edit = self.delivery_location_to_edit.id
        else:
            self.title("Add New Delivery Location")
            
        self.geometry("450x280")
        self.resizable(False, False)

        self.grab_set()
        self.transient(parent)

        frame = ttk.Frame(self, padding="10")
        frame.pack(expand=True, fill=tk.BOTH)

        ttk.Label(frame, text="Name:").grid(row=0, column=0, sticky="w", pady=5)
        self.name_entry = ttk.Entry(frame, width=40)
        self.name_entry.grid(row=0, column=1, sticky="ew", pady=5)

        ttk.Label(frame, text="Address (Optional):").grid(row=1, column=0, sticky="nw", pady=5)
        self.address_text = Text(frame, width=30, height=5, relief=tk.SOLID, borderwidth=1)
        self.address_text.configure(font=self.name_entry.cget('font'))
        self.address_text.grid(row=1, column=1, sticky="ew", pady=5)
        
        frame.columnconfigure(1, weight=1)

        button_frame = ttk.Frame(self, padding="10")
        button_frame.pack(fill=tk.X)

        self.save_button = ttk.Button(button_frame, text="Save", command=self.save_delivery_location)
        self.save_button.pack(side=tk.RIGHT, padx=5)

        self.cancel_button = ttk.Button(button_frame, text="Cancel", command=self.destroy)
        self.cancel_button.pack(side=tk.RIGHT)
        
        if self.delivery_location_to_edit:
            self._populate_fields()

        self.name_entry.focus_set()

    def _populate_fields(self):
        if self.delivery_location_to_edit:
            self.name_entry.insert(0, self.delivery_location_to_edit.name)
            if self.delivery_location_to_edit.address:
                self.address_text.insert("1.0", self.delivery_location_to_edit.address)

    def save_delivery_location(self):
        name = self.name_entry.get().strip()
        address = self.address_text.get("1.0", tk.END).strip()

        if not name:
            messagebox.showerror("Validation Error", "Name cannot be empty.", parent=self)
            self.name_entry.focus_set()
            return

        data_to_save = {
            "name": name,
            "address": address if address else None
        }

        db_session = next(get_db())
        try:
            if self.delivery_location_id_for_edit is not None: # Edit mode
                updated_loc = update_delivery_location(
                    db_session=db_session,
                    delivery_location_id=self.delivery_location_id_for_edit,
                    **data_to_save
                )
                if updated_loc:
                    messagebox.showinfo("Success", f"Delivery Location '{name}' updated successfully!", parent=self)
                    if hasattr(self.parent, 'refresh_delivery_location_list_if_open'): # For MainWindow
                        self.parent.refresh_delivery_location_list_if_open()
                    elif hasattr(self.parent, 'load_delivery_locations'): # For DeliveryLocationListWindow
                        self.parent.load_delivery_locations()
                    self.destroy()
                else:
                    messagebox.showerror("Database Error", f"Failed to update Delivery Location '{name}'.\nName might already exist. Check logs.", parent=self)
            else: # Add mode
                new_location = add_delivery_location(db_session=db_session, **data_to_save)
                if new_location:
                    messagebox.showinfo("Success", f"Delivery Location '{name}' added successfully!", parent=self)
                    if hasattr(self.parent, 'refresh_delivery_location_list_if_open'):
                        self.parent.refresh_delivery_location_list_if_open()
                    elif hasattr(self.parent, 'load_delivery_locations'):
                         self.parent.load_delivery_locations()
                    self.destroy()
                else:
                    messagebox.showerror("Database Error", f"Failed to add Delivery Location '{name}'.\nIt might already exist. Check logs.", parent=self)
        finally:
            db_session.close()

if __name__ == '__main__':
    root = tk.Tk()
    root.title("Main App (dummy for AddDeliveryLocationWindow)")

    mock_loc_instance = DeliveryLocation(id=1, name="Site Alpha", address="123 Test Dr")
    current_test_is_edit_mode_dl = False # DL for DeliveryLocation

    class MockDBSession:
        def add(self, obj): pass; def commit(self): pass; def refresh(self, obj): pass; def rollback(self): pass
        def close(self): print("Mock DB Session (AddDelLoc) closed.")
        def query(self, model): return self
        def filter(self, criterion): return self
        def first(self): return mock_loc_instance if current_test_is_edit_mode_dl else None

    def mock_get_db_adlw(): # ADLW for AddDeliveryLocationWindow
        print("Mock get_db_adlw called")
        session = MockDBSession()
        yield session

    original_get_db_adlw = get_db
    original_add_del_loc_adlw = add_delivery_location
    original_update_del_loc_adlw = update_delivery_location

    def mock_add_del_loc(db_session, **kwargs):
        print(f"Mock add_delivery_location called with: {kwargs['name']}")
        if kwargs['name'] == "EXISTS": return None
        return DeliveryLocation(id=2, **kwargs)

    def mock_update_del_loc(db_session, delivery_location_id, **kwargs):
        print(f"Mock update_delivery_location called for ID {delivery_location_id} with: {kwargs['name']}")
        if kwargs['name'] == "CONFLICT": return None
        updated_data = mock_loc_instance.__dict__.copy()
        updated_data.update(kwargs)
        updated_data.pop('_sa_instance_state', None)
        return DeliveryLocation(**updated_data)

    import app.db.database
    app.db.database.get_db = mock_get_db_adlw
    app.db.database.add_delivery_location = mock_add_del_loc
    app.db.database.update_delivery_location = mock_update_del_loc
    
    class MockParentDL:
        def refresh_delivery_location_list_if_open(self): print("MockParentDL: refresh_delivery_location_list_if_open called")
        def load_delivery_locations(self): print("MockParentDL: load_delivery_locations called")

    mock_parent_dl_window = MockParentDL()

    def open_add_del_loc_dialog():
        global current_test_is_edit_mode_dl; current_test_is_edit_mode_dl = False
        dialog = AddDeliveryLocationWindow(mock_parent_dl_window)
        root.wait_window(dialog)

    def open_edit_del_loc_dialog():
        global current_test_is_edit_mode_dl; current_test_is_edit_mode_dl = True
        dialog = AddDeliveryLocationWindow(mock_parent_dl_window, delivery_location_to_edit=mock_loc_instance)
        root.wait_window(dialog)

    ttk.Button(root, text="Add Delivery Location", command=open_add_del_loc_dialog).pack(pady=10)
    ttk.Button(root, text="Edit Delivery Location (Test)", command=open_edit_del_loc_dialog).pack(pady=10)
    
    try: root.mainloop()
    finally:
        app.db.database.get_db = original_get_db_adlw
        app.db.database.add_delivery_location = original_add_del_loc_adlw
        app.db.database.update_delivery_location = original_update_del_loc_adlw
        print("Restored original DB functions for AddDeliveryLocationWindow.")
