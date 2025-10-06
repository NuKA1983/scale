import argparse
import serial
import time
import sys

def list_ports():
    """Lists serial port names."""
    import serial.tools.list_ports
    ports = serial.tools.list_ports.comports()
    if not ports:
        print("No serial ports found.")
        return

    print("Available serial ports:")
    for port, desc, hwid in sorted(ports):
        print(f"- {port}: {desc} [{hwid}]")

def main():
    parser = argparse.ArgumentParser(
        description="A tool to test serial communication with a scale or other serial device.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""\
Example usage:
  # Test a serial port on Linux with common settings
  python serial_tester.py /dev/ttyUSB0 -b 9600

  # Test a serial port on Windows with different settings
  python serial_tester.py COM3 -b 4800 --parity O --bits 7

  # List all available serial ports
  python serial_tester.py --list-ports
"""
    )
    parser.add_argument(
        "port",
        nargs='?',
        default=None,
        help="The serial port to connect to (e.g., /dev/ttyUSB0 on Linux, COM3 on Windows)."
    )
    parser.add_argument(
        "-b", "--baudrate",
        type=int,
        default=9600,
        help="The baud rate for the serial connection (default: 9600)."
    )
    parser.add_argument(
        "--bits",
        type=int,
        default=8,
        choices=[5, 6, 7, 8],
        help="The number of data bits (default: 8)."
    )
    parser.add_argument(
        "--parity",
        default="N",
        choices=["N", "E", "O", "M", "S"],
        help="Parity setting: N=None, E=Even, O=Odd, M=Mark, S=Space (default: N)."
    )
    parser.add_argument(
        "--stopbits",
        type=float,
        default=1,
        choices=[1, 1.5, 2],
        help="The number of stop bits (default: 1)."
    )
    parser.add_argument(
        "--list-ports",
        action="store_true",
        help="List all available serial ports and exit."
    )

    args = parser.parse_args()

    if args.list_ports:
        list_ports()
        sys.exit(0)

    if args.port is None:
        parser.error("The 'port' argument is required unless --list-ports is specified.")

    print(f"Attempting to connect to {args.port} with the following settings:")
    print(f"  - Baudrate: {args.baudrate}")
    print(f"  - Data Bits: {args.bits}")
    print(f"  - Parity: {args.parity}")
    print(f"  - Stop Bits: {args.stopbits}")
    print("\nPress Ctrl+C to exit.")

    try:
        ser = serial.Serial(
            port=args.port,
            baudrate=args.baudrate,
            bytesize={8: serial.EIGHTBITS, 7: serial.SEVENBITS, 6: serial.SIXBITS, 5: serial.FIVEBITS}[args.bits],
            parity={'N': serial.PARITY_NONE, 'E': serial.PARITY_EVEN, 'O': serial.PARITY_ODD, 'M': serial.PARITY_MARK, 'S': serial.PARITY_SPACE}[args.parity],
            stopbits={1: serial.STOPBITS_ONE, 1.5: serial.STOPBITS_ONE_POINT_FIVE, 2: serial.STOPBITS_TWO}[args.stopbits],
            timeout=1
        )
    except serial.SerialException as e:
        print(f"\nError: Could not open port '{args.port}'.")
        print(f"Details: {e}")
        print("Please check the port name and ensure you have the correct permissions.")
        sys.exit(1)
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
        sys.exit(1)


    print(f"\nSuccessfully connected to {ser.name}. Waiting for data...")

    try:
        while True:
            if ser.in_waiting > 0:
                # Read all available bytes
                raw_data = ser.read(ser.in_waiting)

                # --- Display Raw Data ---
                # 1. As text (with non-printable characters replaced)
                text_repr = "".join(c if ' ' <= c <= '~' else repr(c)[1:-1].replace("\\r", "CR").replace("\\n", "LF\n") for c in raw_data.decode('latin1'))

                # 2. As hexadecimal
                hex_repr = ' '.join(f'{b:02X}' for b in raw_data)

                print(f"[{time.strftime('%H:%M:%S')}] RX ({len(raw_data)} bytes):")
                print(f"  - Text: {text_repr}")
                print(f"  - Hex:  {hex_repr}")
                print("-" * 20)

            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nExiting program.")
    finally:
        if ser.is_open:
            ser.close()
            print(f"Serial port {ser.name} closed.")

if __name__ == "__main__":
    main()