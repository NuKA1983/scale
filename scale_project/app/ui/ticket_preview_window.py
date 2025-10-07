import tkinter as tk
from tkinter import ttk
from typing import Any, Dict, List
import json

from app.utils.ticket_printer import TicketPrinter

class TicketPreviewWindow(tk.Toplevel):
    """
    A window to display a preview of what the printed ticket will look like.
    """
    def __init__(self, parent, ticket_data: Dict[str, Any], layout: List[Dict[str, Any]]):
        super().__init__(parent)
        self.title("Ticket Preview")
        self.geometry("400x550")
        self.resizable(False, False)
        self.grab_set()
        self.transient(parent)

        self.ticket_data = ticket_data
        self.layout = layout

        # A base font size for the preview
        self.base_font_size = 10
        # Use a monospaced font to better simulate a dot-matrix printer
        self.font_family = "Courier"

        self._build_ui()

    def _build_ui(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(expand=True, fill="both")

        # Create a canvas and a scrollbar for the ticket content
        canvas = tk.Canvas(main_frame, borderwidth=0, background="#ffffff")
        ticket_frame = ttk.Frame(canvas, padding="10", style="White.TFrame")
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        canvas.create_window((4,4), window=ticket_frame, anchor="nw")

        ticket_frame.bind("<Configure>", lambda event, canvas=canvas: canvas.configure(scrollregion=canvas.bbox("all")))

        ttk.Style().configure("White.TFrame", background="white")

        # Generate the lines to be displayed
        # We don't need a full printer object, just the method, so we can call it statically
        # if we refactor TicketPrinter to not require an instance for generate_formatted_lines.
        # For now, we'll just instantiate it.
        printer = TicketPrinter()
        formatted_lines = printer.generate_formatted_lines(self.ticket_data, self.layout)

        # Display the lines
        for line_info in formatted_lines:
            text = line_info["text"]
            size_info = line_info.get("size", {})
            width_mult = size_info.get("width", 1)
            height_mult = size_info.get("height", 1)

            # Approximate the printer font size
            font_size = int(self.base_font_size * height_mult)
            font_weight = "bold" if width_mult > 1 else "normal"

            font = (self.font_family, font_size, font_weight)

            lbl = ttk.Label(ticket_frame, text=text, font=font, background="white")
            lbl.pack(anchor="w", padx=5, pady=1)

        # --- Action Buttons ---
        button_frame = ttk.Frame(self, padding=(10, 5))
        button_frame.pack(fill="x", side="bottom")

        close_button = ttk.Button(button_frame, text="Close", command=self.destroy)
        close_button.pack(side="right")

if __name__ == '__main__':
    import os

    # This block allows for direct testing of the preview window
    root = tk.Tk()
    root.title("Main App (dummy for Preview)")

    # Mock data for testing
    mock_ticket_data = {
        "ticket_id": 9876,
        "company_name": "Test Quarry Inc.",
        "unit_id": "TEST-TRUCK-01",
        "gross_weight": 30000.00,
        "tare_weight": 12000.00,
        "net_weight": 18000.00,
        "aggregate_name": "Washed Sand",
        "location_name": "Downtown Project",
        "timestamp": "2024-08-01 10:00:00",
        "operator": "Jane Smith"
    }

    # Load layout from the JSON file using a path relative to this script
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        layout_path = os.path.join(script_dir, '..', 'ticket_layout.json')
        with open(layout_path, 'r') as f:
            mock_layout_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Could not find layout file at {os.path.abspath(layout_path)}")
        mock_layout_data = []
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {os.path.abspath(layout_path)}")
        mock_layout_data = []


    def open_preview():
        if mock_layout_data:
            preview = TicketPreviewWindow(root, mock_ticket_data, mock_layout_data)
        else:
            print("Cannot open preview, layout data is missing.")

    # A button on the dummy root window to launch the preview
    launch_button = ttk.Button(root, text="Open Ticket Preview", command=open_preview)
    launch_button.pack(pady=20, padx=20)

    root.mainloop()