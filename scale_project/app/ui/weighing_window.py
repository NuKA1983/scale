import tkinter as tk
from tkinter import ttk, messagebox
import json
# Updated imports for hybrid DB logic
from app.db.database import (get_all_trucks_mru_ordered, search_trucks,
                             get_all_aggregate_types, get_all_delivery_locations,
                             add_audit_log_entry, get_db, get_truck_by_id,
                             get_weight_ticket_by_id, get_local_db)
from app.db.db_hybrid import create_ticket_locally, sync_pending_tickets
from app.db.models import Truck, AggregateType, DeliveryLocation, WeightTicket
from app.utils.ticket_printer import TicketPrinter
from .ticket_preview_window import TicketPreviewWindow

class WeighingWindow(tk.Toplevel):
    def __init__(self, parent, scale_reader, update_interval_ms=500):
        super().__init__(parent)
        self.parent = parent
        self.scale_reader = scale_reader
        self.update_interval_ms = update_interval_ms

        self.title("New Weighing Ticket")
        self.geometry("700x600")
        self.resizable(False, False)

        self.grab_set()
        self.transient(parent)

        self.selected_truck_obj: Truck | None = None
        self.current_scale_weight: float | None = None
        self.last_saved_ticket_id: int | None = None
        self.ticket_layout = self._load_ticket_layout()
        self.trucks_map = {}

        # Remote session for master data (trucks, materials, etc.)
        self.db_session = next(get_db())
        # Load non-truck data once from remote DB
        self.aggregate_types_map = {a.name: a for a in get_all_aggregate_types(self.db_session)}
        self.delivery_locations_map = {dl.name: dl for dl in get_all_delivery_locations(self.db_session)}
        
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(expand=True, fill=tk.BOTH)

        # --- UI elements (unchanged) ---
        live_weight_frame = ttk.LabelFrame(main_frame, text="Live Scale Data", padding="10")
        live_weight_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        
        ttk.Label(live_weight_frame, text="Current Scale Weight:").pack(side=tk.LEFT, padx=5)
        self.live_weight_var = tk.StringVar(value="--.-- kg")
        ttk.Label(live_weight_frame, textvariable=self.live_weight_var, font=('Helvetica', 14, 'bold')).pack(side=tk.LEFT, padx=5)

        truck_frame = ttk.LabelFrame(main_frame, text="Truck Details", padding="10")
        truck_frame.grid(row=1, column=0, sticky="ewns", padx=5, pady=5)

        ttk.Label(truck_frame, text="Search Truck:").grid(row=0, column=0, sticky="w", pady=2)
        self.truck_search_var = tk.StringVar()
        self.truck_search_entry = ttk.Entry(truck_frame, textvariable=self.truck_search_var, width=25)
        self.truck_search_entry.grid(row=0, column=1, sticky="ew", pady=2, padx=5)
        self.truck_search_entry.bind("<Return>", self.perform_truck_search)

        self.search_button = ttk.Button(truck_frame, text="Search", command=self.perform_truck_search)
        self.search_button.grid(row=0, column=2, padx=5, pady=2)

        ttk.Label(truck_frame, text="Select Truck:").grid(row=1, column=0, sticky="w", pady=2)
        self.truck_combo_var = tk.StringVar()
        self.truck_combo = ttk.Combobox(truck_frame, textvariable=self.truck_combo_var, state="readonly", width=35)
        self.truck_combo.grid(row=1, column=1, columnspan=2, sticky="ew", pady=2, padx=5)
        self.truck_combo.bind("<<ComboboxSelected>>", self.on_truck_selected)

        ttk.Label(truck_frame, text="Tare Weight:").grid(row=2, column=0, sticky="w", pady=2)
        self.tare_weight_var = tk.StringVar(value="--.-- kg")
        ttk.Label(truck_frame, textvariable=self.tare_weight_var, font=('Helvetica', 10, 'bold')).grid(row=2, column=1, columnspan=2, sticky="w", pady=2, padx=5)
        
        self.load_trucks_into_combobox()

        material_frame = ttk.LabelFrame(main_frame, text="Material & Destination", padding="10")
        material_frame.grid(row=2, column=0, sticky="ewns", padx=5, pady=5)

        ttk.Label(material_frame, text="Select Aggregate:").grid(row=0, column=0, sticky="w", pady=2)
        self.aggregate_combo_var = tk.StringVar()
        self.aggregate_combo = ttk.Combobox(material_frame, textvariable=self.aggregate_combo_var, values=list(self.aggregate_types_map.keys()), state="readonly", width=30)
        self.aggregate_combo.grid(row=0, column=1, sticky="ew", pady=2, padx=5)

        ttk.Label(material_frame, text="Select Location:").grid(row=1, column=0, sticky="w", pady=2)
        self.location_combo_var = tk.StringVar()
        self.location_combo = ttk.Combobox(material_frame, textvariable=self.location_combo_var, values=list(self.delivery_locations_map.keys()), state="readonly", width=30)
        self.location_combo.grid(row=1, column=1, sticky="ew", pady=2, padx=5)
        
        weights_frame = ttk.LabelFrame(main_frame, text="Weight Information", padding="10")
        weights_frame.grid(row=1, column=1, rowspan=2, sticky="ewns", padx=5, pady=5)

        ttk.Label(weights_frame, text="Gross Weight (kg):").grid(row=0, column=0, sticky="w", pady=2)
        self.gross_weight_var = tk.StringVar()
        self.gross_weight_entry = ttk.Entry(weights_frame, textvariable=self.gross_weight_var, width=15)
        self.gross_weight_entry.grid(row=0, column=1, sticky="ew", pady=2, padx=5)
        self.gross_weight_var.trace_add("write", lambda *_: self.recalculate_net_weight())

        ttk.Button(weights_frame, text="Capture Gross", command=self.capture_gross_weight).grid(row=0, column=2, pady=2, padx=5)
        
        ttk.Label(weights_frame, text="Net Weight (kg):").grid(row=1, column=0, sticky="w", pady=2)
        self.net_weight_var = tk.StringVar(value="--.-- kg")
        ttk.Label(weights_frame, textvariable=self.net_weight_var, font=('Helvetica', 12, 'bold')).grid(row=1, column=1, columnspan=2, sticky="w", pady=2, padx=5)
        
        ttk.Label(weights_frame, text="Operator Name:").grid(row=2, column=0, sticky="w", pady=2)
        self.operator_name_var = tk.StringVar()
        self.operator_name_entry = ttk.Entry(weights_frame, textvariable=self.operator_name_var, width=20)
        self.operator_name_entry.grid(row=2, column=1, columnspan=2, sticky="ew", pady=2, padx=5)

        action_frame = ttk.Frame(main_frame, padding="10")
        action_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=10)
        
        self.cancel_button = ttk.Button(action_frame, text="Close", command=self.on_closing)
        self.cancel_button.pack(side=tk.RIGHT, padx=5)

        self.print_button = ttk.Button(action_frame, text="Print Ticket", command=self.print_last_ticket, state=tk.DISABLED)
        self.print_button.pack(side=tk.RIGHT, padx=5)

        self.preview_button = ttk.Button(action_frame, text="Preview Ticket", command=self.preview_last_ticket, state=tk.DISABLED)
        self.preview_button.pack(side=tk.RIGHT, padx=5)

        self.save_button = ttk.Button(action_frame, text="Record Weighing", command=self.save_ticket, style="Accent.TButton")
        self.save_button.pack(side=tk.RIGHT, padx=5)
        ttk.Style().configure("Accent.TButton", font=('Helvetica', 10, 'bold'), foreground="green")

        main_frame.columnconfigure(0, weight=1); main_frame.columnconfigure(1, weight=1)
        truck_frame.columnconfigure(1, weight=1)
        material_frame.columnconfigure(1, weight=1)
        weights_frame.columnconfigure(1, weight=1)

        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.update_live_weight_display()

    def _load_ticket_layout(self):
        try:
            with open("scale_project/app/ticket_layout.json", 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            messagebox.showerror("Error", f"Could not load ticket layout file: {e}", parent=self)
            return []

    def load_trucks_into_combobox(self, trucks_list: list[Truck] | None = None):
        current_selection_key = None
        if self.selected_truck_obj:
            current_selection_key = f"{self.selected_truck_obj.company_name} - {self.selected_truck_obj.unit_id} ({self.selected_truck_obj.id})"

        if trucks_list is None:
            # Master truck list is read from remote DB via self.db_session
            trucks = get_all_trucks_mru_ordered(self.db_session)
        else:
            trucks = trucks_list
        
        self.trucks_map = {f"{t.company_name} - {t.unit_id} ({t.id})": t for t in trucks}
        self.truck_combo['values'] = list(self.trucks_map.keys())
        
        if not self.trucks_map:
            self.truck_combo_var.set("")
            self.selected_truck_obj = None
            self.tare_weight_var.set("--.-- kg")
        elif current_selection_key and current_selection_key in self.trucks_map:
            self.truck_combo_var.set(current_selection_key)
        else:
            self.truck_combo_var.set("") 
            self.selected_truck_obj = None
            self.tare_weight_var.set("--.-- kg")
        
        self.recalculate_net_weight()

    def perform_truck_search(self, event=None):
        search_term = self.truck_search_var.get().strip()
        if not search_term:
            self.load_trucks_into_combobox()
        else:
            # Search is performed on remote DB
            found_trucks = search_trucks(self.db_session, search_term)
            self.load_trucks_into_combobox(found_trucks)

    def update_live_weight_display(self):
        weight = self.scale_reader.read_weight()
        if weight is not None:
            self.current_scale_weight = weight
            self.live_weight_var.set(f"{weight:0=+8.2f} kg")
        else:
            self.current_scale_weight = None
            self.live_weight_var.set("N/A")
        self.after(self.update_interval_ms, self.update_live_weight_display)

    def on_truck_selected(self, event=None):
        selected_key = self.truck_combo_var.get()
        self.selected_truck_obj = self.trucks_map.get(selected_key)
        if self.selected_truck_obj:
            self.tare_weight_var.set(f"{self.selected_truck_obj.tare_weight:.2f} kg")
        else:
            self.tare_weight_var.set("--.-- kg")
        self.recalculate_net_weight()
        self.print_button.config(state=tk.DISABLED)
        self.preview_button.config(state=tk.DISABLED)

    def capture_gross_weight(self):
        if self.current_scale_weight is not None:
            self.gross_weight_var.set(f"{self.current_scale_weight:.2f}")
        else:
            messagebox.showwarning("Scale Error", "Could not read weight from scale.", parent=self)
            self.gross_weight_var.set("")
        self.recalculate_net_weight()

    def recalculate_net_weight(self):
        try:
            gross_str = self.gross_weight_var.get()
            if not gross_str: self.net_weight_var.set("--.-- kg"); return
            gross = float(gross_str)
            if self.selected_truck_obj and self.selected_truck_obj.tare_weight is not None:
                tare = self.selected_truck_obj.tare_weight
                net = gross - tare
                self.net_weight_var.set(f"{net:.2f} kg")
            else: self.net_weight_var.set("--.-- kg (Select Truck)")
        except ValueError: self.net_weight_var.set("Invalid Gross Wt.")
        except Exception: self.net_weight_var.set("Error")
        self.print_button.config(state=tk.DISABLED)
        self.preview_button.config(state=tk.DISABLED)

    def save_ticket(self):
        # --- Validation logic (unchanged) ---
        if not self.selected_truck_obj:
            messagebox.showerror("Validation Error", "Please select a truck.", parent=self); return
        selected_agg_name = self.aggregate_combo_var.get()
        selected_agg_obj = self.aggregate_types_map.get(selected_agg_name)
        if not selected_agg_obj:
            messagebox.showerror("Validation Error", "Please select an aggregate type.", parent=self); return
        selected_loc_name = self.location_combo_var.get()
        selected_loc_obj = self.delivery_locations_map.get(selected_loc_name)
        if not selected_loc_obj:
            messagebox.showerror("Validation Error", "Please select a delivery location.", parent=self); return
        try:
            gross_weight = float(self.gross_weight_var.get())
            if gross_weight <= 0:
                messagebox.showerror("Validation Error", "Gross weight must be a positive number.", parent=self); return
        except ValueError:
            messagebox.showerror("Validation Error", "Invalid gross weight entered.", parent=self); return

        tare_weight_at_weighing = self.selected_truck_obj.tare_weight
        net_weight = gross_weight - tare_weight_at_weighing

        if net_weight < 0:
             messagebox.showerror("Validation Error", f"Net weight ({net_weight:.2f} kg) cannot be negative.", parent=self); return
        
        if self.selected_truck_obj.max_allowed_weight > 0 and gross_weight > self.selected_truck_obj.max_allowed_weight:
            if not messagebox.askyesno("Weight Warning", 
                                       f"Gross weight ({gross_weight:.2f} kg) exceeds max allowed ({self.selected_truck_obj.max_allowed_weight:.2f} kg).\nProceed anyway?", 
                                       parent=self): return
        operator_name = self.operator_name_var.get().strip() or None

        # --- New Hybrid DB Logic ---
        local_db_session = next(get_local_db())
        try:
            ticket = create_ticket_locally(
                local_db=local_db_session,
                truck_id=self.selected_truck_obj.id,
                aggregate_type_id=selected_agg_obj.id,
                delivery_location_id=selected_loc_obj.id,
                gross_weight=gross_weight,
                tare_weight_at_weighing=tare_weight_at_weighing,
                net_weight=net_weight,
                operator_name=operator_name,
                ticket_printed=False
            )

            if ticket:
                self.last_saved_ticket_id = ticket.id
                add_audit_log_entry(
                    db_session=local_db_session, table_name="WeightTickets", record_id=ticket.id,
                    action="INSERT", changed_by=operator_name, new_values=ticket
                )
                messagebox.showinfo("Success", f"Weight Ticket #{ticket.id} saved locally!", parent=self)
                self.print_button.config(state=tk.NORMAL)
                self.preview_button.config(state=tk.NORMAL)

                # Update UI before attempting sync, which might take a moment
                self.update()

                # Attempt to sync immediately
                sync_success, sync_fail = sync_pending_tickets()
                if sync_success > 0 and sync_fail == 0:
                    messagebox.showinfo("Sync Status", f"Ticket #{ticket.id} successfully synced to the remote server.", parent=self)
                elif sync_fail > 0:
                    messagebox.showwarning("Sync Status", f"Ticket #{ticket.id} saved locally, but failed to sync to the remote server. It will be retried later.", parent=self)

                # Reload MRU trucks from remote and clear form
                self.perform_truck_search()
                self.clear_form(clear_search=False)
                self.truck_search_entry.focus_set()
            else:
                self.last_saved_ticket_id = None
                self.print_button.config(state=tk.DISABLED)
                self.preview_button.config(state=tk.DISABLED)
                messagebox.showerror("Database Error", "Failed to save weight ticket locally. Check logs.", parent=self)
        finally:
            local_db_session.close()

    def _create_ticket_data_dict(self, ticket: WeightTicket) -> dict:
        # This function needs the full ticket object with relationships.
        # The ticket from the local DB will have these.
        return {
            "ticket_id": ticket.id,
            "company_name": ticket.truck.company_name,
            "unit_id": ticket.truck.unit_id,
            "gross_weight": ticket.gross_weight,
            "tare_weight": ticket.tare_weight_at_weighing,
            "net_weight": ticket.net_weight,
            "aggregate_name": ticket.aggregate_type.name,
            "location_name": ticket.delivery_location.name,
            "timestamp": ticket.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            "operator": ticket.operator_name or "N/A"
        }

    def preview_last_ticket(self):
        if self.last_saved_ticket_id is None:
            messagebox.showwarning("Preview Error", "No ticket has been saved yet.", parent=self); return
        if not self.ticket_layout:
            messagebox.showerror("Preview Error", "Ticket layout is missing or invalid.", parent=self); return

        local_db = next(get_local_db())
        try:
            # Ticket data is fetched from the local DB for preview/print
            ticket = get_weight_ticket_by_id(local_db, self.last_saved_ticket_id)
            if not ticket:
                messagebox.showerror("Preview Error", f"Could not find ticket #{self.last_saved_ticket_id} in the local database.", parent=self)
                return
            ticket_data = self._create_ticket_data_dict(ticket)
            TicketPreviewWindow(self, ticket_data, self.ticket_layout)
        finally:
            local_db.close()

    def print_last_ticket(self):
        if self.last_saved_ticket_id is None:
            messagebox.showwarning("Print Error", "No ticket has been saved yet.", parent=self); return
        if not self.ticket_layout:
            messagebox.showerror("Print Error", "Ticket layout is missing or invalid.", parent=self); return

        local_db = next(get_local_db())
        try:
            ticket = get_weight_ticket_by_id(local_db, self.last_saved_ticket_id)
            if not ticket:
                messagebox.showerror("Print Error", f"Could not find ticket #{self.last_saved_ticket_id} in the local database.", parent=self)
                return

            ticket_data = self._create_ticket_data_dict(ticket)
            printer = TicketPrinter(port='/dev/ttyUSB0') # TODO: Make port configurable

            try:
                printer.print_ticket(ticket_data, self.ticket_layout)
                ticket.ticket_printed = True
                local_db.commit()
                messagebox.showinfo("Print Success", f"Ticket #{ticket.id} sent to printer.", parent=self)
            except Exception as e:
                messagebox.showerror("Printer Error", f"An error occurred while printing: {e}", parent=self)
        finally:
            local_db.close()

    def clear_form(self, clear_search=True):
        if clear_search:
            self.truck_search_var.set('')
        
        self.truck_combo_var.set('')
        self.aggregate_combo_var.set('')
        self.location_combo_var.set('')
        self.gross_weight_var.set('')
        self.operator_name_var.set('')
        self.tare_weight_var.set("--.-- kg")
        self.net_weight_var.set("--.-- kg")
        self.selected_truck_obj = None
        self.print_button.config(state=tk.DISABLED)
        self.preview_button.config(state=tk.DISABLED)
        self.last_saved_ticket_id = None

    def on_closing(self):
        if self.db_session:
            self.db_session.close(); print("WeighingWindow: Remote DB session closed.")
        self.destroy()

if __name__ == '__main__':
    # ... (Test setup largely same as before)
    # This test setup will need adjustment to work with the dual-db system,
    # specifically creating master data on the "remote" and then running the window.
    # For now, it will likely fail if the remote DB isn't configured and running.
    import random
    from app.db.database import initialize_databases as create_db_and_tables

    class MockScaleReader:
        def __init__(self): self.weight = 1234.56
        def read_weight(self): self.weight += random.uniform(-5, 5); return self.weight
        def connect(self): return True
        def disconnect(self): pass

    root = tk.Tk()
    root.title("Main App (dummy for WeighingWindow)")
    create_db_and_tables() # Initializes both local and remote DBs

    # Populate remote DB with master data for the test
    db = next(get_db()) # get_db() defaults to remote
    try:
        if not get_all_trucks_mru_ordered(db):
            from app.db.database import add_truck
            add_truck(db, "DUMMY01", "Alpha Co", 1000, 5000, "ASGA01")
            add_truck(db, "DUMMY02", "Beta Inc", 2000, 10000, "ASGA02")
            add_truck(db, "GAMMA03", "Gamma LLC", 1500, 7500)
        if not get_all_aggregate_types(db):
            from app.db.database import add_aggregate_type
            add_aggregate_type(db, "Sand", "Fine Sand")
        if not get_all_delivery_locations(db):
            from app.db.database import add_delivery_location
            add_delivery_location(db, "Site A", "123 Main St")
    finally:
        db.close()

    mock_reader = MockScaleReader()
    
    def open_weighing_dialog():
        dialog = WeighingWindow(root, mock_reader)

    ttk.Button(root, text="Open Weighing Window", command=open_weighing_dialog).pack(pady=20)
    root.mainloop()