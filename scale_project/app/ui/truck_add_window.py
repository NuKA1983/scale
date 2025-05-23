import tkinter as tk
from tkinter import ttk, messagebox
from app.db.database import add_truck, update_truck, get_db # Added update_truck
from app.db.models import Truck # For type hinting

class AddTruckWindow(tk.Toplevel):
    def __init__(self, parent, truck_to_edit: Truck | None = None): # Accept truck_to_edit
        super().__init__(parent)
        self.parent = parent
        self.truck_to_edit = truck_to_edit
        self.truck_id_for_edit = None # Store ID if editing

        if self.truck_to_edit:
            self.title("Edit Truck")
            self.truck_id_for_edit = self.truck_to_edit.id
        else:
            self.title("Add New Truck")
            
        self.geometry("400x280") # Slightly taller for potential messages or if fields wrap
        self.resizable(False, False)

        self.grab_set()
        self.transient(parent)

        frame = ttk.Frame(self, padding="10")
        frame.pack(expand=True, fill=tk.BOTH)

        ttk.Label(frame, text="Unit ID:").grid(row=0, column=0, sticky="w", pady=5)
        self.unit_id_entry = ttk.Entry(frame, width=30)
        self.unit_id_entry.grid(row=0, column=1, sticky="ew", pady=5)
        # For simplicity, Unit ID is editable. In a real app, this might be restricted or have warnings.

        ttk.Label(frame, text="Company Name:").grid(row=1, column=0, sticky="w", pady=5)
        self.company_name_entry = ttk.Entry(frame, width=30)
        self.company_name_entry.grid(row=1, column=1, sticky="ew", pady=5)

        ttk.Label(frame, text="ASGA ID (Optional):").grid(row=2, column=0, sticky="w", pady=5)
        self.asga_id_entry = ttk.Entry(frame, width=30)
        self.asga_id_entry.grid(row=2, column=1, sticky="ew", pady=5)

        ttk.Label(frame, text="Tare Weight (kg):").grid(row=3, column=0, sticky="w", pady=5)
        self.tare_weight_entry = ttk.Entry(frame, width=30)
        self.tare_weight_entry.grid(row=3, column=1, sticky="ew", pady=5)

        ttk.Label(frame, text="Max Allowed Weight (kg):").grid(row=4, column=0, sticky="w", pady=5)
        self.max_weight_entry = ttk.Entry(frame, width=30)
        self.max_weight_entry.grid(row=4, column=1, sticky="ew", pady=5)
        
        frame.columnconfigure(1, weight=1)

        button_frame = ttk.Frame(self, padding="10")
        button_frame.pack(fill=tk.X)

        self.save_button = ttk.Button(button_frame, text="Save", command=self.save_truck)
        self.save_button.pack(side=tk.RIGHT, padx=5)

        self.cancel_button = ttk.Button(button_frame, text="Cancel", command=self.destroy)
        self.cancel_button.pack(side=tk.RIGHT)
        
        if self.truck_to_edit:
            self._populate_fields()

        self.unit_id_entry.focus_set()

    def _populate_fields(self):
        if self.truck_to_edit:
            self.unit_id_entry.insert(0, self.truck_to_edit.unit_id)
            self.company_name_entry.insert(0, self.truck_to_edit.company_name)
            if self.truck_to_edit.asga_id:
                self.asga_id_entry.insert(0, self.truck_to_edit.asga_id)
            self.tare_weight_entry.insert(0, str(self.truck_to_edit.tare_weight))
            self.max_weight_entry.insert(0, str(self.truck_to_edit.max_allowed_weight))

    def save_truck(self):
        unit_id = self.unit_id_entry.get().strip()
        company_name = self.company_name_entry.get().strip()
        asga_id = self.asga_id_entry.get().strip() # Will be converted to None if empty by DB func
        tare_weight_str = self.tare_weight_entry.get().strip()
        max_weight_str = self.max_weight_entry.get().strip()

        if not unit_id:
            messagebox.showerror("Validation Error", "Unit ID cannot be empty.", parent=self); self.unit_id_entry.focus_set(); return
        if not company_name:
            messagebox.showerror("Validation Error", "Company Name cannot be empty.", parent=self); self.company_name_entry.focus_set(); return

        try:
            tare_weight = float(tare_weight_str)
            if tare_weight <= 0: raise ValueError("Tare weight must be positive.")
        except ValueError:
            messagebox.showerror("Validation Error", "Tare Weight must be a valid positive number.", parent=self); self.tare_weight_entry.focus_set(); return

        try:
            max_allowed_weight = float(max_weight_str)
            if max_allowed_weight <= 0: raise ValueError("Max Allowed Weight must be positive.")
            if max_allowed_weight <= tare_weight:
                messagebox.showerror("Validation Error", "Max Allowed Weight must be greater than Tare Weight.", parent=self); self.max_weight_entry.focus_set(); return
        except ValueError:
            messagebox.showerror("Validation Error", "Max Allowed Weight must be a valid positive number.", parent=self); self.max_weight_entry.focus_set(); return

        data_to_save = {
            "unit_id": unit_id,
            "company_name": company_name,
            "asga_id": asga_id, # DB function handles converting '' to None
            "tare_weight": tare_weight,
            "max_allowed_weight": max_allowed_weight
        }

        db_session = next(get_db())
        try:
            if self.truck_id_for_edit is not None: # Edit mode
                updated_truck = update_truck(
                    db_session=db_session,
                    truck_id=self.truck_id_for_edit,
                    **data_to_save
                )
                if updated_truck:
                    messagebox.showinfo("Success", f"Truck '{unit_id}' updated successfully!", parent=self)
                    if hasattr(self.parent, 'refresh_truck_list_if_open'): # For TruckListWindow
                        self.parent.refresh_truck_list_if_open()
                    elif hasattr(self.parent, 'load_trucks'): # For direct parent if it's TruckListWindow itself
                        self.parent.load_trucks()
                    self.destroy()
                else:
                    messagebox.showerror("Database Error", f"Failed to update truck '{unit_id}'.\nCheck logs. Unit ID or ASGA ID might conflict.", parent=self)
            else: # Add mode
                new_truck = add_truck(db_session=db_session, **data_to_save)
                if new_truck:
                    messagebox.showinfo("Success", f"Truck '{unit_id}' added successfully!", parent=self)
                    if hasattr(self.parent, 'refresh_truck_list_if_open'):
                        self.parent.refresh_truck_list_if_open()
                    elif hasattr(self.parent, 'load_trucks'):
                         self.parent.load_trucks()
                    self.destroy()
                else:
                    messagebox.showerror("Database Error", f"Failed to add truck '{unit_id}'.\nCheck logs. It might already exist.", parent=self)
        finally:
            db_session.close()

if __name__ == '__main__':
    root = tk.Tk()
    root.title("Main App (dummy)")

    # Mock DB for testing AddTruckWindow in edit mode
    mock_truck_instance = Truck(id=1, unit_id="TEST01", company_name="Test Company", 
                                asga_id="ASGA01", tare_weight=1000.0, max_allowed_weight=5000.0)

    class MockDBSession:
        def add(self, obj): pass; def commit(self): pass; def refresh(self, obj): pass; def rollback(self): pass
        def close(self): print("Mock DB Session closed.")
        def query(self, model): return self # Simplistic query mock
        def filter(self, criterion): return self
        def first(self): return mock_truck_instance if self.is_edit_test else None
        is_edit_test = False # Control this for testing add vs edit

    def mock_get_db_atw(): # Suffix atw for AddTruckWindow
        print("Mock get_db_atw called")
        session = MockDBSession()
        # To simulate finding a truck for edit mode:
        # For a real test, you might set a flag or check truck_id_for_edit
        if current_test_is_edit_mode: 
            session.is_edit_test = True
        yield session

    original_get_db_atw = get_db
    original_add_truck_atw = add_truck
    original_update_truck_atw = update_truck
    current_test_is_edit_mode = False


    def mock_add_truck_atw(db_session, **kwargs):
        print(f"Mock add_truck_atw called with: {kwargs['unit_id']}")
        if kwargs['unit_id'] == "EXISTS": return None
        return Truck(id=2, **kwargs)

    def mock_update_truck_atw(db_session, truck_id, **kwargs):
        print(f"Mock update_truck_atw called for ID {truck_id} with: {kwargs['unit_id']}")
        if kwargs['unit_id'] == "CONFLICT": return None # Simulate unique constraint conflict
        # Return a new instance to simulate update
        updated_data = mock_truck_instance.__dict__.copy() # start with original
        updated_data.update(kwargs)
        updated_data.pop('_sa_instance_state', None) # remove SQLAlchemy state
        return Truck(**updated_data)


    import app.db.database
    app.db.database.get_db = mock_get_db_atw
    app.db.database.add_truck = mock_add_truck_atw
    app.db.database.update_truck = mock_update_truck_atw
    
    class MockParent: # To test callback
        def refresh_truck_list_if_open(self):
            print("MockParent: refresh_truck_list_if_open called")
        def load_trucks(self): # If parent is TruckListWindow itself
             print("MockParent: load_trucks called")


    mock_parent_window = MockParent()

    def open_add_truck_dialog():
        global current_test_is_edit_mode
        current_test_is_edit_mode = False
        dialog = AddTruckWindow(mock_parent_window) # Pass mock parent
        root.wait_window(dialog)

    def open_edit_truck_dialog():
        global current_test_is_edit_mode
        current_test_is_edit_mode = True # So mock_get_db finds the truck
        dialog = AddTruckWindow(mock_parent_window, truck_to_edit=mock_truck_instance) # Pass mock parent
        root.wait_window(dialog)

    ttk.Button(root, text="Add Truck", command=open_add_truck_dialog).pack(pady=10)
    ttk.Button(root, text="Edit Truck (Test)", command=open_edit_truck_dialog).pack(pady=10)
    
    try:
        root.mainloop()
    finally:
        app.db.database.get_db = original_get_db_atw
        app.db.database.add_truck = original_add_truck_atw
        app.db.database.update_truck = original_update_truck_atw
        print("Restored original DB functions for AddTruckWindow.")
