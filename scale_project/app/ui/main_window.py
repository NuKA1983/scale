import tkinter as tk
from tkinter import ttk, Menu
from app.scale_reader import ScaleReader
from .truck_add_window import AddTruckWindow
from .truck_list_window import TruckListWindow
from .aggregate_type_add_window import AddAggregateTypeWindow
from .aggregate_type_list_window import AggregateTypeListWindow
from .delivery_location_add_window import AddDeliveryLocationWindow
from .delivery_location_list_window import DeliveryLocationListWindow
from .weighing_window import WeighingWindow # New import
from app.db.database import create_db_and_tables 

class MainApplicationWindow(tk.Tk):
    def __init__(self, update_interval_ms=500):
        super().__init__()

        self.title("Scale Application - Main")
        self.geometry("550x250") # Adjusted size for new button

        self.update_interval_ms = update_interval_ms
        self.active_truck_list_window = None
        self.active_aggregate_type_list_window = None
        self.active_delivery_location_list_window = None
        self.active_weighing_window = None # To manage the weighing window instance

        create_db_and_tables() 
        print("Database tables ensured to be created if they didn't exist.")

        self.scale_reader = ScaleReader(use_emulator=True) # This is passed to WeighingWindow
        if not self.scale_reader.connect():
            print("Failed to connect to scale emulator.")

        menubar = Menu(self)
        self.config(menu=menubar)

        # --- File Menu ---
        file_menu = Menu(menubar, tearoff=0)
        file_menu.add_command(label="Exit", command=self.on_closing)
        menubar.add_cascade(label="File", menu=file_menu)

        # --- Weighing Menu (or could be a top-level menu) ---
        weighing_menu = Menu(menubar, tearoff=0)
        weighing_menu.add_command(label="New Weighing Ticket", command=self.open_weighing_window)
        menubar.add_cascade(label="Weighing", menu=weighing_menu)

        # --- Manage Menu ---
        manage_menu = Menu(menubar, tearoff=0)
        manage_menu.add_command(label="Add New Truck", command=self.open_add_truck_window)
        manage_menu.add_command(label="View Trucks", command=self.open_truck_list_window)
        manage_menu.add_separator()
        manage_menu.add_command(label="Add New Aggregate Type", command=self.open_add_aggregate_type_window)
        manage_menu.add_command(label="View Aggregate Types", command=self.open_aggregate_type_list_window)
        manage_menu.add_separator()
        manage_menu.add_command(label="Add New Delivery Location", command=self.open_add_delivery_location_window)
        manage_menu.add_command(label="View Delivery Locations", command=self.open_delivery_location_list_window)
        menubar.add_cascade(label="Manage", menu=manage_menu)
        
        # --- GUI Elements ---
        style = ttk.Style(self)
        style.configure('TLabel', font=('Helvetica', 12))
        style.configure('Weight.TLabel', font=('Helvetica', 20, 'bold'), foreground='blue')
        style.configure('Status.TLabel', font=('Helvetica', 10))
        style.configure('Big.TButton', font=('Helvetica', 12, 'bold'), padding=10)


        main_frame = ttk.Frame(self, padding="10 10 10 10")
        main_frame.pack(expand=True, fill=tk.BOTH)
        
        # Live weight display in main window
        live_weight_frame = ttk.Frame(main_frame)
        live_weight_frame.pack(pady=10)
        ttk.Label(live_weight_frame, text="Current Scale Weight:", style='TLabel').pack(side=tk.LEFT, padx=5)
        self.weight_value_var = tk.StringVar(value="--.-- kg")
        self.weight_display_label = ttk.Label(live_weight_frame, textvariable=self.weight_value_var, style='Weight.TLabel')
        self.weight_display_label.pack(side=tk.LEFT, padx=5)

        # Prominent "New Weighing Ticket" Button
        new_ticket_button = ttk.Button(main_frame, text="Create New Weighing Ticket", 
                                       command=self.open_weighing_window, style='Big.TButton')
        new_ticket_button.pack(pady=20, fill=tk.X, padx=50)
        
        # Status bar
        self.status_var = tk.StringVar(value="Initializing...")
        self.status_bar = ttk.Label(main_frame, textvariable=self.status_var, style='Status.TLabel', anchor="w")
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X, pady=(5,0), padx=5)
        
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.status_var.set("Connected to Scale Emulator. DB Initialized.")
        self.update_weight_display()

    def update_weight_display(self):
        weight = self.scale_reader.read_weight()
        if weight is not None:
            self.weight_value_var.set(f"{weight:0=+8.2f} kg")
        else:
            self.weight_value_var.set("N/A")
            # self.status_var.set("Error reading scale / No data") # Avoid overriding other status
        self.after(self.update_interval_ms, self.update_weight_display)

    # --- Weighing Window Management ---
    def open_weighing_window(self):
        if self.active_weighing_window and self.active_weighing_window.winfo_exists():
            self.active_weighing_window.lift()
            self.active_weighing_window.focus_set()
        else:
            # Pass the scale_reader instance to the WeighingWindow
            self.active_weighing_window = WeighingWindow(self, self.scale_reader, self.update_interval_ms)
            # No wait_window() if we want to interact with main window while weighing is open,
            # but WeighingWindow uses grab_set() to be modal.

    # --- Truck Window Management ---
    def open_add_truck_window(self):
        add_window = AddTruckWindow(self)
        add_window.wait_window()

    def open_truck_list_window(self):
        if self.active_truck_list_window and self.active_truck_list_window.winfo_exists():
            self.active_truck_list_window.lift()
            self.active_truck_list_window.focus_set()
        else:
            self.active_truck_list_window = TruckListWindow(self)
            
    def refresh_truck_list_if_open(self):
        if self.active_truck_list_window and self.active_truck_list_window.winfo_exists():
            self.active_truck_list_window.load_trucks()
            
    def register_truck_list_window(self, window_instance):
        self.active_truck_list_window = window_instance
        
    def unregister_truck_list_window(self, window_instance):
        if self.active_truck_list_window == window_instance:
            self.active_truck_list_window = None

    # --- Aggregate Type Window Management ---
    def open_add_aggregate_type_window(self):
        add_agg_window = AddAggregateTypeWindow(self)
        add_agg_window.wait_window()

    def open_aggregate_type_list_window(self):
        if self.active_aggregate_type_list_window and self.active_aggregate_type_list_window.winfo_exists():
            self.active_aggregate_type_list_window.lift()
            self.active_aggregate_type_list_window.focus_set()
        else:
            self.active_aggregate_type_list_window = AggregateTypeListWindow(self)

    def refresh_aggregate_type_list_if_open(self):
        if self.active_aggregate_type_list_window and self.active_aggregate_type_list_window.winfo_exists():
            self.active_aggregate_type_list_window.load_aggregate_types()

    def register_aggregate_type_list_window(self, window_instance):
        self.active_aggregate_type_list_window = window_instance
        
    def unregister_aggregate_type_list_window(self, window_instance):
        if self.active_aggregate_type_list_window == window_instance:
            self.active_aggregate_type_list_window = None

    # --- Delivery Location Window Management ---
    def open_add_delivery_location_window(self):
        add_loc_window = AddDeliveryLocationWindow(self)
        add_loc_window.wait_window()

    def open_delivery_location_list_window(self):
        if self.active_delivery_location_list_window and self.active_delivery_location_list_window.winfo_exists():
            self.active_delivery_location_list_window.lift()
            self.active_delivery_location_list_window.focus_set()
        else:
            self.active_delivery_location_list_window = DeliveryLocationListWindow(self)

    def refresh_delivery_location_list_if_open(self):
        if self.active_delivery_location_list_window and self.active_delivery_location_list_window.winfo_exists():
            self.active_delivery_location_list_window.load_delivery_locations()

    def register_delivery_location_list_window(self, window_instance):
        self.active_delivery_location_list_window = window_instance
        
    def unregister_delivery_location_list_window(self, window_instance):
        if self.active_delivery_location_list_window == window_instance:
            self.active_delivery_location_list_window = None

    def on_closing(self):
        print("Closing application...")
        if self.scale_reader:
            self.scale_reader.disconnect()
        
        # Explicitly destroy any open Toplevel windows
        if self.active_weighing_window and self.active_weighing_window.winfo_exists():
            self.active_weighing_window.destroy() # WeighingWindow manages its own DB session
        if self.active_truck_list_window and self.active_truck_list_window.winfo_exists():
            self.active_truck_list_window.destroy()
        if self.active_aggregate_type_list_window and self.active_aggregate_type_list_window.winfo_exists():
            self.active_aggregate_type_list_window.destroy()
        if self.active_delivery_location_list_window and self.active_delivery_location_list_window.winfo_exists():
            self.active_delivery_location_list_window.destroy()
            
        # Generic catch-all for any other Toplevels that might have been missed by specific handlers
        # (e.g., Add* windows are modal and should be closed before this, but good for safety)
        for child in self.winfo_children():
            if isinstance(child, tk.Toplevel) and child.winfo_exists():
                child.destroy()
        self.destroy()

if __name__ == '__main__':
    app = MainApplicationWindow(update_interval_ms=1000)
    app.mainloop()
