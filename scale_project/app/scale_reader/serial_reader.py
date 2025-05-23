import serial
import time
import re
from .scale_emulator import ScaleEmulator

class ScaleReader:
    def __init__(self, port=None, baudrate=9600, timeout=1, use_emulator=False):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.use_emulator = use_emulator
        self.ser = None
        self.emulator = None

        if self.use_emulator:
            self.emulator = ScaleEmulator()
            print("Using Scale Emulator.")
        elif self.port is None:
            raise ValueError("Serial port must be specified if not using emulator.")
        
    def connect(self) -> bool:
        if self.use_emulator:
            print("Emulator connected (simulated).")
            return True
        
        if self.ser is not None and self.ser.is_open:
            print("Already connected.")
            return True
            
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
            print(f"Connected to serial port: {self.port}")
            return True
        except serial.SerialException as e:
            print(f"Error connecting to serial port {self.port}: {e}")
            self.ser = None
            return False

    def disconnect(self):
        if self.use_emulator:
            print("Emulator disconnected (simulated).")
            return

        if self.ser and self.ser.is_open:
            self.ser.close()
            print(f"Disconnected from serial port: {self.port}")
        else:
            print("Not connected to any serial port.")

    def parse_weight_data(self, data_string: str) -> float | None:
        # Expected format: "ST,GS,+00123.45kg\r\n"
        # Regex to capture the signed float value
        match = re.search(r"([+-]\d+\.\d+)", data_string)
        if match:
            try:
                weight = float(match.group(1))
                return weight
            except ValueError:
                print(f"Error converting weight to float from: {match.group(1)}")
                return None
        else:
            # print(f"Could not parse weight from data: '{data_string.strip()}'") # Too verbose for normal operation
            return None

    def read_weight(self) -> float | None:
        if self.use_emulator:
            if self.emulator:
                simulated_data = self.emulator.get_simulated_reading()
                # print(f"Emulator raw: {simulated_data.strip()}") # for debugging
                return self.parse_weight_data(simulated_data)
            else:
                print("Emulator not initialized!") # Should not happen if __init__ is correct
                return None

        if not self.ser or not self.ser.is_open:
            print("Serial port not connected.")
            if not self.connect(): # Try to auto-reconnect
                return None
        
        try:
            line = self.ser.readline().decode('ascii', errors='ignore').strip()
            if line:
                # print(f"Serial raw: {line}") # for debugging
                return self.parse_weight_data(line)
            return None
        except serial.SerialException as e:
            print(f"Error reading from serial port: {e}")
            return None
        except Exception as e:
            print(f"An unexpected error occurred during serial read: {e}")
            return None

if __name__ == '__main__':
    print("Testing ScaleReader with Emulator...")
    # Test with Emulator
    reader_emulator = ScaleReader(use_emulator=True)
    if reader_emulator.connect():
        for i in range(5):
            weight = reader_emulator.read_weight()
            if weight is not None:
                print(f"Emulator Reading {i+1}: {weight:.2f} kg")
            else:
                print(f"Emulator Reading {i+1}: Failed to get weight")
            time.sleep(0.5)
        reader_emulator.disconnect()

    print("\nTesting ScaleReader with Serial Port (requires a loopback or actual device)...")
    # Test with a real serial port - replace 'COM_PORT' or '/dev/ttyUSB0' with your actual port
    # For automated testing without a real device, this part might be tricky.
    # One common method is to use a "loopback" connector: connect TX to RX on a serial port.
    # Then, what you write to the port, you can read back.
    # For this example, we'll just show how it would be called.
    # To actually test this, you'd need a scale or another program writing to the other end of the serial port.
    
    # Example serial port name - replace with your actual port for testing
    # On Windows: "COM3", "COM4", etc.
    # On Linux: "/dev/ttyUSB0", "/dev/ttyS0", etc.
    # On macOS: "/dev/cu.usbserial-XXXX", "/dev/cu.Bluetooth-Incoming-Port", etc.
    
    TEST_SERIAL_PORT = None # Set to a port like "/dev/ttyS10" or "COM5" if you have a virtual pair for testing
                            # or if you have a real device. For CI, this will likely be None.

    if TEST_SERIAL_PORT:
        print(f"\nAttempting to test with serial port: {TEST_SERIAL_PORT}")
        print("NOTE: This requires a device/emulator sending data on this port in the format 'ST,GS,+XXXXX.XXkg\\r\\n'")
        
        reader_serial = ScaleReader(port=TEST_SERIAL_PORT, baudrate=9600, timeout=2)
        if reader_serial.connect():
            print("Waiting for data (5 readings)...")
            for i in range(5):
                weight = reader_serial.read_weight()
                if weight is not None:
                    print(f"Serial Reading {i+1}: {weight:.2f} kg")
                else:
                    print(f"Serial Reading {i+1}: No data or parse error.")
                time.sleep(1) # Wait for data
            reader_serial.disconnect()
        else:
            print(f"Could not connect to serial port {TEST_SERIAL_PORT}. Skipping serial test.")
    else:
        print("\nTEST_SERIAL_PORT not set. Skipping direct serial port test.")
        print("To test with a real or virtual serial port, set TEST_SERIAL_PORT in the script.")

    print("\nScaleReader Test Finished.")
