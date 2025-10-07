# Raspberry Pi 400 GPIO Pinout for Serial Communication

This document provides the necessary pinout information for connecting a serial device, such as a scale, to the Raspberry Pi 400's GPIO header.

## GPIO Header Orientation

The GPIO header is a 40-pin connector on the back of the Raspberry Pi 400. The pin numbering starts at 1 in the top-left corner (closest to the SD card slot) and ends at 40 in the bottom-right.

```
      +-----+-----+
 3.3V |  1  |  2  | 5V
SDA.1 |  3  |  4  | 5V
SCL.1 |  5  |  6  | Ground
GPCLK0|  7  |  8  | UART TXD (GPIO 14)
Ground|  9  | 10  | UART RXD (GPIO 15)
GPIO17| 11  | 12  | GPIO18 (PCM_CLK)
GPIO27| 13  | 14  | Ground
GPIO22| 15  | 16  | GPIO23
 3.3V | 17  | 18  | GPIO24
 MOSI | 19  | 20  | Ground
 MISO | 21  | 22  | GPIO25
 SCLK | 23  | 24  | SPI_CE0
Ground| 25  | 26  | SPI_CE1
SDA.0 | 27  | 28  | SCL.0
GPIO5 | 29  | 30  | Ground
GPIO6 | 31  | 32  | GPIO12 (PWM0)
GPIO13| 33  | 34  | Ground
PCM_FS| 35  | 36  | GPIO16
GPIO26| 37  | 38  | PCM_DIN
Ground| 39  | 40  | PCM_DOUT
      +-----+-----+
```

## Serial (UART) Connection

For serial communication, you will use the UART (Universal Asynchronous Receiver/Transmitter) pins. On the Raspberry Pi, these are accessible via the GPIO header.

The primary UART is `/dev/ttyAMA0`. After enabling the serial port, it may also be available as `/dev/serial0`.

**Required Pins:**

| Pin # | BCM (GPIO) | Name     | Purpose                  |
|-------|------------|----------|--------------------------|
| 8     | GPIO 14    | UART TXD | Transmit Data            |
| 10    | GPIO 15    | UART RXD | Receive Data             |
| 6,9,14| N/A        | GND      | Ground                   |

**How to Connect Your Scale:**

1.  **Ground Connection (GND):** Connect a ground pin from the Raspberry Pi's GPIO header to the ground (GND) pin on your scale's serial interface. This is crucial for a stable connection. You can use any of the ground pins (e.g., pin 6, 9, or 14).

2.  **Transmit Data (TX):** Connect the Raspberry Pi's **TXD** pin (GPIO 14, Physical Pin 8) to the **RXD** (Receive) pin on your scale.

3.  **Receive Data (RX):** Connect the Raspberry Pi's **RXD** pin (GPIO 15, Physical Pin 10) to the **TXD** (Transmit) pin on your scale.

**Important:** The logic levels for the Raspberry Pi's GPIO are 3.3V. If your scale uses a different voltage level (e.g., 5V or RS-232 with +/- 12V), you **must** use a logic level shifter or an appropriate adapter (like a MAX3232 for RS-232) to prevent damage to your Raspberry Pi.

## Enabling the Serial Port

Before you can use the serial port, you may need to enable it and configure it correctly.

1.  Run `sudo raspi-config`.
2.  Navigate to `3 Interface Options`.
3.  Navigate to `I6 Serial Port`.
4.  When asked "Would you like a login shell to be accessible over serial?", answer **No**.
5.  When asked "Would you like the serial port hardware to be enabled?", answer **Yes**.
6.  Exit `raspi-config` and reboot your Raspberry Pi when prompted.

After rebooting, the serial port will be available for your Python script at `/dev/serial0`.