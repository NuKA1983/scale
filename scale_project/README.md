# Scale Interface Project

This project is a Python-based application for interfacing with a scale, managing truck data, aggregate types, delivery locations, and weight tickets. It includes a database to store this information and an audit log to track changes.

## Hardware Setup and Serial Testing

### Connecting the Scale

Before running the application, you must connect your scale to the Raspberry Pi. For detailed instructions on the GPIO pinout and how to wire the serial connection, please refer to the [PINOUT.md](PINOUT.md) file.

### Testing the Serial Connection

If you are unsure of the correct communication parameters (baud rate, parity, etc.) for your scale, you can use the provided serial tester tool.

This tool will help you receive and inspect the raw data coming from your scale, allowing you to determine the correct settings.

**How to run the tester:**
```bash
python tools/serial_tester.py <your_serial_port> [options]
```

**Example:**
```bash
python tools/serial_tester.py /dev/serial0 -b 9600
```

For a full list of options and available ports, run:
```bash
python tools/serial_tester.py --help
```
To list available ports:
```bash
python tools/serial_tester.py --list-ports
```
