import tkinter as tk
from tkinter import ttk, messagebox, Text
from app.db.database import add_aggregate_type, update_aggregate_type, get_db # Added update_aggregate_type
from app.db.models import AggregateType # For type hinting

class AddAggregateTypeWindow(tk.Toplevel):
    def __init__(self, parent, aggregate_type_to_edit: AggregateType | None = None): # Accept aggregate_type_to_edit
        super().__init__(parent)
        self.parent = parent
        self.aggregate_type_to_edit = aggregate_type_to_edit
        self.aggregate_type_id_for_edit = None

        if self.aggregate_type_to_edit:
            self.title("Edit Aggregate Type")
            self.aggregate_type_id_for_edit = self.aggregate_type_to_edit.id
        else:
            self.title("Add New Aggregate Type")
            
        self.geometry("450x280") 
        self.resizable(False, False)

        self.grab_set()
        self.transient(parent)

        frame = ttk.Frame(self, padding="10")
        frame.pack(expand=True, fill=tk.BOTH)

        ttk.Label(frame, text="Name:").grid(row=0, column=0, sticky="w", pady=5)
        self.name_entry = ttk.Entry(frame, width=40)
        self.name_entry.grid(row=0, column=1, sticky="ew", pady=5)

        ttk.Label(frame, text="Description (Optional):").grid(row=1, column=0, sticky="nw", pady=5)
        self.description_text = Text(frame, width=30, height=5, relief=tk.SOLID, borderwidth=1)
        self.description_text.configure(font=self.name_entry.cget('font'))
        self.description_text.grid(row=1, column=1, sticky="ew", pady=5)
        
        frame.columnconfigure(1, weight=1)

        button_frame = ttk.Frame(self, padding="10")
        button_frame.pack(fill=tk.X)

        self.save_button = ttk.Button(button_frame, text="Save", command=self.save_aggregate_type)
        self.save_button.pack(side=tk.RIGHT, padx=5)

        self.cancel_button = ttk.Button(button_frame, text="Cancel", command=self.destroy)
        self.cancel_button.pack(side=tk.RIGHT)
        
        if self.aggregate_type_to_edit:
            self._populate_fields()

        self.name_entry.focus_set()

    def _populate_fields(self):
        if self.aggregate_type_to_edit:
            self.name_entry.insert(0, self.aggregate_type_to_edit.name)
            if self.aggregate_type_to_edit.description:
                self.description_text.insert("1.0", self.aggregate_type_to_edit.description)

    def save_aggregate_type(self):
        name = self.name_entry.get().strip()
        description = self.description_text.get("1.0", tk.END).strip()

        if not name:
            messagebox.showerror("Validation Error", "Name cannot be empty.", parent=self)
            self.name_entry.focus_set()
            return

        data_to_save = {
            "name": name,
            "description": description if description else None
        }

        db_session = next(get_db())
        try:
            if self.aggregate_type_id_for_edit is not None: # Edit mode
                updated_agg_type = update_aggregate_type(
                    db_session=db_session,
                    aggregate_type_id=self.aggregate_type_id_for_edit,
                    **data_to_save
                )
                if updated_agg_type:
                    messagebox.showinfo("Success", f"Aggregate Type '{name}' updated successfully!", parent=self)
                    # Notify parent to refresh list
                    if hasattr(self.parent, 'refresh_aggregate_type_list_if_open'): # For MainWindow
                        self.parent.refresh_aggregate_type_list_if_open()
                    elif hasattr(self.parent, 'load_aggregate_types'): # For AggregateTypeListWindow
                        self.parent.load_aggregate_types()
                    self.destroy()
                else:
                    messagebox.showerror("Database Error", f"Failed to update Aggregate Type '{name}'.\nName might already exist. Check logs.", parent=self)
            else: # Add mode
                new_aggregate_type = add_aggregate_type(db_session=db_session, **data_to_save)
                if new_aggregate_type:
                    messagebox.showinfo("Success", f"Aggregate Type '{name}' added successfully!", parent=self)
                    if hasattr(self.parent, 'refresh_aggregate_type_list_if_open'):
                        self.parent.refresh_aggregate_type_list_if_open()
                    elif hasattr(self.parent, 'load_aggregate_types'):
                        self.parent.load_aggregate_types()
                    self.destroy()
                else:
                    messagebox.showerror("Database Error", f"Failed to add Aggregate Type '{name}'.\nIt might already exist. Check logs.", parent=self)
        finally:
            db_session.close()

if __name__ == '__main__':
    root = tk.Tk()
    root.title("Main App (dummy for AddAggregateTypeWindow)")

    mock_agg_type_instance = AggregateType(id=1, name="Sand", description="Fine construction sand")
    current_test_is_edit_mode_at = False # AT for AggregateType

    class MockDBSession:
        def add(self, obj): pass; def commit(self): pass; def refresh(self, obj): pass; def rollback(self): pass
        def close(self): print("Mock DB Session (AddAggType) closed.")
        def query(self, model): return self
        def filter(self, criterion): return self
        def first(self): return mock_agg_type_instance if current_test_is_edit_mode_at else None

    def mock_get_db_aatw(): # AATW for AddAggregateTypeWindow
        print("Mock get_db_aatw called")
        session = MockDBSession()
        yield session

    original_get_db_aatw = get_db
    original_add_agg_type_aatw = add_aggregate_type
    original_update_agg_type_aatw = update_aggregate_type

    def mock_add_agg_type(db_session, **kwargs):
        print(f"Mock add_aggregate_type called with: {kwargs['name']}")
        if kwargs['name'] == "EXISTS": return None
        return AggregateType(id=2, **kwargs)

    def mock_update_agg_type(db_session, aggregate_type_id, **kwargs):
        print(f"Mock update_aggregate_type called for ID {aggregate_type_id} with: {kwargs['name']}")
        if kwargs['name'] == "CONFLICT": return None
        updated_data = mock_agg_type_instance.__dict__.copy()
        updated_data.update(kwargs)
        updated_data.pop('_sa_instance_state', None)
        return AggregateType(**updated_data)

    import app.db.database
    app.db.database.get_db = mock_get_db_aatw
    app.db.database.add_aggregate_type = mock_add_agg_type
    app.db.database.update_aggregate_type = mock_update_agg_type
    
    class MockParentAT:
        def refresh_aggregate_type_list_if_open(self): print("MockParentAT: refresh_aggregate_type_list_if_open called")
        def load_aggregate_types(self): print("MockParentAT: load_aggregate_types called")

    mock_parent_at_window = MockParentAT()

    def open_add_agg_type_dialog():
        global current_test_is_edit_mode_at; current_test_is_edit_mode_at = False
        dialog = AddAggregateTypeWindow(mock_parent_at_window)
        root.wait_window(dialog)

    def open_edit_agg_type_dialog():
        global current_test_is_edit_mode_at; current_test_is_edit_mode_at = True
        dialog = AddAggregateTypeWindow(mock_parent_at_window, aggregate_type_to_edit=mock_agg_type_instance)
        root.wait_window(dialog)

    ttk.Button(root, text="Add Aggregate Type", command=open_add_agg_type_dialog).pack(pady=10)
    ttk.Button(root, text="Edit Aggregate Type (Test)", command=open_edit_agg_type_dialog).pack(pady=10)
    
    try: root.mainloop()
    finally:
        app.db.database.get_db = original_get_db_aatw
        app.db.database.add_aggregate_type = original_add_agg_type_aatw
        app.db.database.update_aggregate_type = original_update_agg_type_aatw
        print("Restored original DB functions for AddAggregateTypeWindow.")
