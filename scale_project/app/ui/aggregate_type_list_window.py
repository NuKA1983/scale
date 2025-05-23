import tkinter as tk
from tkinter import ttk, messagebox
from app.db.database import get_all_aggregate_types, get_db, get_aggregate_type_by_name # Added for edit
from app.db.models import AggregateType 
from .aggregate_type_add_window import AddAggregateTypeWindow # To open in edit mode

class AggregateTypeListWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("View Aggregate Types")
        self.geometry("650x400") # Wider for edit button

        self.grab_set()
        self.transient(parent)

        frame = ttk.Frame(self, padding="10")
        frame.pack(expand=True, fill=tk.BOTH)

        columns = ("id", "name", "description") # Added ID for fetching for edit
        self.tree = ttk.Treeview(frame, columns=columns, show="headings", height=12)
        
        self.tree.heading("id", text="ID")
        self.tree.heading("name", text="Name")
        self.tree.heading("description", text="Description")

        self.tree.column("id", width=40, anchor=tk.W, stretch=False)
        self.tree.column("name", width=150, anchor=tk.W)
        self.tree.column("description", width=350, anchor=tk.W) 
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        button_frame = ttk.Frame(self, padding=(10, 10, 10, 10))
        button_frame.pack(fill=tk.X)

        self.refresh_button = ttk.Button(button_frame, text="Refresh", command=self.load_aggregate_types)
        self.refresh_button.pack(side=tk.LEFT, padx=5)

        self.edit_button = ttk.Button(button_frame, text="Edit Selected", command=self.edit_selected_aggregate_type, state=tk.DISABLED)
        self.edit_button.pack(side=tk.LEFT, padx=5)

        self.close_button = ttk.Button(button_frame, text="Close", command=self.on_closing)
        self.close_button.pack(side=tk.RIGHT, padx=5)
        
        self.tree.bind("<<TreeviewSelect>>", self.on_aggregate_type_select_in_tree)

        self.load_aggregate_types()

        if hasattr(self.parent, 'register_aggregate_type_list_window'):
            self.parent.register_aggregate_type_list_window(self)
        
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_aggregate_type_select_in_tree(self, event=None):
        selected_items = self.tree.selection()
        if selected_items:
            self.edit_button.config(state=tk.NORMAL)
        else:
            self.edit_button.config(state=tk.DISABLED)

    def edit_selected_aggregate_type(self):
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("No Selection", "Please select an aggregate type to edit.", parent=self)
            return
        
        selected_item = selected_items[0]
        # Assuming 'id' is the first value in the 'values' tuple
        agg_type_id_str = self.tree.item(selected_item, "values")[0]
        try:
            agg_type_id = int(agg_type_id_str)
        except (ValueError, TypeError):
            messagebox.showerror("Error", "Could not retrieve valid ID for editing.", parent=self)
            return

        db_session = next(get_db())
        try:
            # Need a get_aggregate_type_by_id function, or use name if ID isn't directly stored/retrieved well
            # For now, assuming we can get it by ID (which is better)
            # If get_aggregate_type_by_id doesn't exist, we'd need to add it.
            # Let's assume models.py and database.py have get_by_id for AggregateType
            agg_type_to_edit = db_session.query(AggregateType).filter(AggregateType.id == agg_type_id).first()

            if agg_type_to_edit:
                edit_dialog = AddAggregateTypeWindow(self, aggregate_type_to_edit=agg_type_to_edit)
                self.wait_window(edit_dialog)
                # load_aggregate_types() is called by AddAggregateTypeWindow via parent.load_aggregate_types()
            else:
                messagebox.showerror("Error", f"Aggregate Type with ID {agg_type_id} not found.", parent=self)
                self.load_aggregate_types() # Refresh list
        finally:
            db_session.close()


    def load_aggregate_types(self):
        self.edit_button.config(state=tk.DISABLED)
        for item in self.tree.get_children():
            self.tree.delete(item)

        db_session = next(get_db())
        try:
            aggregate_types = get_all_aggregate_types(db_session)
            if not aggregate_types:
                self.tree.insert("", tk.END, values=("No aggregate types found.", "", ""))
            else:
                for agg_type in aggregate_types:
                    self.tree.insert("", tk.END, values=(
                        agg_type.id, # Store ID
                        agg_type.name,
                        agg_type.description if agg_type.description else "N/A",
                    ))
        except Exception as e:
            messagebox.showerror("Load Error", f"Failed to load aggregate types: {e}", parent=self)
        finally:
            db_session.close()

    def on_closing(self):
        if hasattr(self.parent, 'unregister_aggregate_type_list_window'):
            self.parent.unregister_aggregate_type_list_window(self)
        self.destroy()

if __name__ == '__main__':
    root = tk.Tk()
    root.title("Main App (dummy for AggTypeListWindow)")

    from app.db.database import create_db_and_tables, add_aggregate_type
    create_db_and_tables()

    db = next(get_db())
    try:
        if not get_all_aggregate_types(db):
            add_aggregate_type(db, "Sand", "Fine construction sand")
            add_aggregate_type(db, "Gravel", "Coarse construction gravel")
            add_aggregate_type(db, "Crushed Stone", None)
    finally:
        db.close()
    
    def open_aggregate_type_list_dialog():
        dialog = AggregateTypeListWindow(root)

    ttk.Button(root, text="View Aggregate Types", command=open_aggregate_type_list_dialog).pack(pady=20)
    
    root.mainloop()
