import serial
import json
from typing import Any, Dict, List

# Standard ESC/P Commands (for dot matrix)
ESC = b'\x1b'
GS = b'\x1d'
LF = b'\x0a'
CR = b'\x0d'
FF = b'\x0c'  # Form Feed

# Command: Initialize printer
CMD_INIT = ESC + b'@'
# Command: Select character font
#  - n=0: Font A (default)
#  - n=1: Font B
CMD_SELECT_FONT_A = ESC + b'M' + b'\x00'
CMD_SELECT_FONT_B = ESC + b'M' + b'\x01'

# Command: Set character size
#  - Bits 0-3: Character height magnification (1-8)
#  - Bits 4-7: Character width magnification (1-8)
#  - Example: Normal size (1x1) -> 0x00
#  - Example: Double height (1x2) -> 0x01
#  - Example: Double width (2x1) -> 0x10
#  - Example: Double width and height (2x2) -> 0x11
def set_char_size(width: int = 1, height: int = 1) -> bytes:
    """Generates the command to set character size."""
    if not (1 <= width <= 8 and 1 <= height <= 8):
        width, height = 1, 1 # Default to normal size on invalid input
    byte = ((width - 1) << 4) | (height - 1)
    return GS + b'!' + bytes([byte])

class TicketPrinter:
    """
    A class to handle printing receipts to a serial ESC/P dot-matrix printer.
    """
    def __init__(self, port: str = '/dev/ttyUSB0', baudrate: int = 9600, timeout: int = 1):
        """
        Initializes the printer.
        :param port: The serial port the printer is connected to.
        :param baudrate: The baud rate for the serial communication.
        :param timeout: The write timeout for the serial port.
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.connection = None

    def _connect(self) -> bool:
        """Establishes a connection to the serial printer."""
        try:
            self.connection = serial.Serial(
                self.port, self.baudrate, timeout=self.timeout
            )
            print(f"Successfully connected to printer at {self.port}.")
            return True
        except serial.SerialException as e:
            print(f"Error connecting to printer: {e}")
            self.connection = None
            return False

    def _disconnect(self):
        """Closes the serial connection."""
        if self.connection and self.connection.is_open:
            self.connection.close()
            print("Printer connection closed.")
        self.connection = None

    def _send_command(self, command: bytes):
        """Sends a raw byte command to the printer."""
        if self.connection:
            try:
                self.connection.write(command)
            except serial.SerialTimeoutException:
                print("Error: Write timeout while sending command to printer.")
            except Exception as e:
                print(f"An unexpected error occurred while sending command: {e}")

    def generate_formatted_lines(self, ticket_data: Dict[str, Any], layout: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Generates a list of formatted lines with their styles, ready for display or printing.

        :param ticket_data: A dictionary containing the data for the ticket.
        :param layout: A list of dictionaries defining the ticket layout.
        :return: A list of dictionaries, where each dict contains the 'text', 'font', and 'size'.
        """
        formatted_lines = []
        for line_def in layout:
            text = self._format_line(line_def, ticket_data)
            formatted_lines.append({
                "text": text,
                "font": line_def.get("font", "A"),
                "size": line_def.get("size", {"width": 1, "height": 1})
            })
        return formatted_lines

    def print_ticket(self, ticket_data: Dict[str, Any], layout: List[Dict[str, Any]]):
        """
        Formats a ticket and sends it to the physical printer.

        :param ticket_data: A dictionary containing the data for the ticket.
        :param layout: A list of dictionaries defining the ticket layout.
        """
        if not self._connect():
            return

        # Use the new method to get formatted lines with style info
        lines_to_print = self.generate_formatted_lines(ticket_data, layout)

        try:
            self._send_command(CMD_INIT)

            for line_info in lines_to_print:
                # Set font
                font = line_info.get("font", "A").upper()
                self._send_command(CMD_SELECT_FONT_B if font == "B" else CMD_SELECT_FONT_A)

                # Set character size
                size = line_info.get("size", {})
                width = size.get("width", 1)
                height = size.get("height", 1)
                self._send_command(set_char_size(width, height))

                # Print the pre-formatted text
                self._send_command(line_info["text"].encode('cp437', 'replace'))
                self._send_command(CR + LF)

                # Reset size to normal for the next line
                self._send_command(set_char_size(1, 1))

            # Eject the slip/page
            self._send_command(FF)

        finally:
            self._disconnect()

    def _format_line(self, line_def: Dict[str, Any], data: Dict[str, Any]) -> str:
        """
        Formats a single line according to its definition using str.format().
        """
        content = line_def.get("content", "")
        try:
            return content.format(**data)
        except (KeyError, ValueError) as e:
            print(f"Warning: Could not format line due to missing/bad key: {e}")
            # Return the content with placeholders intact on error
            return content

if __name__ == '__main__':
    # This is for testing the module directly
    print("Testing TicketPrinter Module...")

    # Mock ticket data
    mock_ticket = {
        "ticket_id": 12345,
        "company_name": "Big Rock Quarry",
        "unit_id": "TRUCK-01",
        "gross_weight": 25000.50,
        "tare_weight": 10000.00,
        "net_weight": 15000.50,
        "aggregate_name": "Gravel #57",
        "location_name": "Construction Site A",
        "timestamp": "2024-07-30 14:30:00",
        "operator": "John Doe"
    }

    # Load layout from the JSON file
    layout_path = '../ticket_layout.json'
    try:
        with open(layout_path, 'r') as f:
            mock_layout = json.load(f)
        print(f"Successfully loaded layout from {layout_path}")
    except FileNotFoundError:
        print(f"Error: Layout file not found at {layout_path}. Make sure you are running this from the utils directory.")
        mock_layout = [] # Fallback to empty layout
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {layout_path}.")
        mock_layout = []

    # On a real system, you would provide the correct port.
    # For this test, we can't actually connect, so this will show the error message.
    # To test fully, you would need a device on /dev/ttyUSB0 or change the port.
    printer = TicketPrinter(port='/dev/ttyUSB0')

    # We will just test the line formatting logic here without connecting
    print("\n--- Formatted Lines (for testing) ---")
    if mock_layout:
        for line_def in mock_layout:
            print(printer._format_line(line_def, mock_ticket))
    print("-------------------------------------\n")

    print("To perform a real print test, connect a printer and ensure the port is correct.")
    # Example of how it would be called:
    # if mock_layout:
    #     printer.print_ticket(mock_ticket, mock_layout)