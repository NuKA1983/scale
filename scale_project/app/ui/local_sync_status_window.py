import tkinter as tk
from tkinter import ttk, messagebox
from app.db.db_hybrid import get_recent_local_tickets, sync_pending_tickets

class LocalSyncStatusWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Local Transaction Sync Status (Last 24 Hours)")
        self.geometry("800x500")
        self.transient(parent)
        self.grab_set()

        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(expand=True, fill=tk.BOTH)

        # --- Treeview to display tickets ---
        columns = ("ticket_id", "timestamp", "truck_unit", "net_weight", "sync_status")
        self.tree = ttk.Treeview(main_frame, columns=columns, show="headings")

        self.tree.heading("ticket_id", text="Ticket ID")
        self.tree.heading("timestamp", text="Timestamp")
        self.tree.heading("truck_unit", text="Truck Unit ID")
        self.tree.heading("net_weight", text="Net Weight (kg)")
        self.tree.heading("sync_status", text="Sync Status")

        self.tree.column("ticket_id", width=80, anchor=tk.CENTER)
        self.tree.column("timestamp", width=150)
        self.tree.column("truck_unit", width=120)
        self.tree.column("net_weight", width=120, anchor=tk.E)
        self.tree.column("sync_status", width=100, anchor=tk.CENTER)

        # --- Styling for sync status ---
        self.tree.tag_configure('synced', foreground='green')
        self.tree.tag_configure('pending', foreground='orange')

        self.tree.pack(expand=True, fill=tk.BOTH, side=tk.TOP)

        # --- Action Buttons ---
        button_frame = ttk.Frame(main_frame, padding=(0, 10, 0, 0))
        button_frame.pack(fill=tk.X, side=tk.BOTTOM)

        self.close_button = ttk.Button(button_frame, text="Close", command=self.destroy)
        self.close_button.pack(side=tk.RIGHT, padx=5)

        self.refresh_button = ttk.Button(button_frame, text="Refresh List", command=self.load_tickets)
        self.refresh_button.pack(side=tk.RIGHT, padx=5)

        self.sync_button = ttk.Button(button_frame, text="Sync Pending Tickets", command=self.run_sync, style="Accent.TButton")
        self.sync_button.pack(side=tk.LEFT, padx=5)

        self.load_tickets()

    def load_tickets(self):
        """Clears the treeview and loads the most recent local tickets."""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        recent_tickets = get_recent_local_tickets()
        if not recent_tickets:
            self.tree.insert("", tk.END, values=("", "No recent local transactions found.", "", "", ""))
            return

        for ticket in recent_tickets:
            status_text = "Synced" if ticket.synced_to_remote else "Pending"
            tag = "synced" if ticket.synced_to_remote else "pending"

            # Relationships like ticket.truck might be expired if the session is closed.
            # The get_recent_local_tickets function gets a new session and closes it.
            # For this UI, we will rely on IDs stored on the ticket itself. A more complex
            # app might need to re-fetch related objects.
            truck_unit_id = ticket.truck.unit_id if ticket.truck else f"Truck ID: {ticket.truck_id}"

            self.tree.insert(
                "",
                tk.END,
                values=(
                    ticket.id,
                    ticket.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    truck_unit_id,
                    f"{ticket.net_weight:.2f}",
                    status_text
                ),
                tags=(tag,)
            )

    def run_sync(self):
        """Runs the sync process and shows results."""
        self.sync_button.config(state=tk.DISABLED)
        self.refresh_button.config(state=tk.DISABLED)
        self.update() # Ensure UI updates before blocking call

        messagebox.showinfo("Syncing...", "Attempting to sync pending tickets with the remote server. This may take a moment.", parent=self)

        successful_syncs, failed_syncs = sync_pending_tickets()

        self.sync_button.config(state=tk.NORMAL)
        self.refresh_button.config(state=tk.NORMAL)

        if successful_syncs == 0 and failed_syncs == 0:
            messagebox.showinfo("Sync Complete", "No pending tickets were found to sync.", parent=self)
        elif failed_syncs > 0:
            messagebox.showerror("Sync Error", f"Sync process finished.\n\nSuccessfully synced: {successful_syncs}\nFailed to sync: {failed_syncs}\n\nPlease check the logs and your network connection.", parent=self)
        else:
            messagebox.showinfo("Sync Complete", f"Successfully synced {successful_syncs} pending ticket(s).", parent=self)

        self.load_tickets() # Refresh the list to show new statuses