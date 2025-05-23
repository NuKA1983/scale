import time
import random

class ScaleEmulator:
    def __init__(self, initial_weight=100.0, fluctuation=1.0, increment_step=0.5):
        self.current_weight = initial_weight
        self.fluctuation = fluctuation
        self.increment_step = increment_step # For a slightly more predictable change over time
        self.counter = 0

    def get_simulated_reading(self) -> str:
        # Simulate some minor weight fluctuation
        noise = random.uniform(-self.fluctuation, self.fluctuation)
        
        # Simulate a general trend (e.g., weight increasing as a truck is loaded)
        # This makes the simulated data a bit more interesting than pure random noise around a fixed point.
        # We'll make it increment for a while, then maybe decrement, or reset.
        if self.counter < 50: # Simulate loading for 50 readings
            self.current_weight += self.increment_step
        elif self.counter < 70: # Simulate some stabilization or slight decrease
             self.current_weight -= self.increment_step / 2
        else: # Reset or change trend
            self.current_weight = 100.0 + random.uniform(-10,10) # Reset to a new base
            self.counter = 0
            
        self.counter +=1
        
        effective_weight = self.current_weight + noise
        
        if effective_weight < 0:
            effective_weight = 0.0
            
        # Format: "ST,GS,+00123.45kg\r\n" (ensure fixed length for weight part)
        # ST = Status (e.g., Stable)
        # GS = Gross Weight Sign (e.g., Positive)
        # Using a common format: <STX>+1234.56kg<CR><LF> or similar
        # Let's use the suggested "ST,GS,+00123.45kg\r\n"
        # The format specifier `0=+10.2f` means:
        # 0: pad with zeros
        # =: place the sign (+/-) right after the padding
        # +: always show the sign
        # 10: total width of 10 characters (including sign, digits, decimal point)
        # .2f: 2 decimal places
        return f"ST,GS,{effective_weight:0=+10.2f}kg\r\n"

if __name__ == '__main__':
    emulator = ScaleEmulator(initial_weight=500.0, fluctuation=0.5, increment_step=10.0)
    print("Starting Scale Emulator Test...")
    for i in range(20): # Test with 20 readings
        reading = emulator.get_simulated_reading()
        print(f"Reading {i+1}: {reading.strip()}") # .strip() to remove \r\n for cleaner console output
        time.sleep(0.2) # Simulate readings at 0.2 second intervals

    print("\nTesting with different initial weight and fluctuation:")
    emulator2 = ScaleEmulator(initial_weight=1234.5, fluctuation=0.05, increment_step=0.1)
    for i in range(10):
        reading = emulator2.get_simulated_reading()
        print(f"Reading {i+1}: {reading.strip()}")
        time.sleep(0.2)
    print("\nEmulator Test Finished.")
