from machine import Pin
from time import sleep_ms


# I used these keys on the 'CCCN4052A' hand piece:
KEYS = [
    ['1', '2', '3'],      # Row 1
    ['4', '5', '6'],      # Row 2
    ['7', '8', '9'],      # Row 3
    ['*', '0', '#'],      # Row 4
    ['CL', 'A', 'HF'],    # Row 5
    ['MR', 'UP', '']      # Row 6
]


class Associate2KKeypad:
    def __init__(self,
                 col1_pin,
                 col2_pin,
                 col3_pin,
                 row1_pin,
                 row2_pin,
                 row3_pin,
                 row4_pin,
                 row5_pin,
                 row6_pin):

        # Rows as outputs:
        self.row_pins = [row1_pin, row2_pin, row3_pin, row4_pin, row5_pin, row6_pin]
        self.rows = [Pin(pin, Pin.OUT) for pin in self.row_pins]

        for r in self.rows:
            r.value(1)

        # Columns as inputs:
        self.col_pins = [col1_pin, col2_pin, col3_pin]

        self.cols = [Pin(pin, Pin.IN, Pin.PULL_UP) for pin in self.col_pins]

    def scan_keypad(self):
        for row_idx, row_pin in enumerate(self.rows):
            # Pull current row LOW
            row_pin.value(0)

            for col_idx, col_pin in enumerate(self.cols):
                # Check if button is pulling column LOW
                if col_pin.value() == 0:
                    # Retrieve the label from map
                    try:
                        char = KEYS[row_idx][col_idx]
                    except IndexError:
                        char = "ERROR"

                    # Debounce: wait for release
                    while col_pin.value() == 0:
                        sleep_ms(100)

                    row_pin.value(1)
                    return char

            # Reset row to HIGH
            row_pin.value(1)
        return None


if __name__ == "__main__":
    keypad = Associate2KKeypad(7, 10, 11, 12,
                               13, 6, 5, 4, 3)
    while 1:
        key = keypad.scan_keypad()
        if key:
            print(f"Key: {key}")
        sleep_ms(200)
