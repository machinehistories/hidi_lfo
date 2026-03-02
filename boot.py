import board
import digitalio
import storage
import time

# ===============================
# BOOT MODE SELECTION
# ===============================
# Hold ANY button during reset to mount CIRCUITPY as USB drive.
# This allows you to view and edit presets.json on your computer.
#
# Normal boot (no button held): filesystem is writable by CircuitPython,
# CIRCUITPY drive is NOT visible on your computer.
# ===============================

time.sleep(0.1)  # settle time

# Read PyGamer shift register buttons directly (keypad module not available in boot.py)
latch = digitalio.DigitalInOut(board.BUTTON_LATCH)
clock = digitalio.DigitalInOut(board.BUTTON_CLOCK)
data  = digitalio.DigitalInOut(board.BUTTON_OUT)

latch.direction = digitalio.Direction.OUTPUT
clock.direction = digitalio.Direction.OUTPUT
data.direction  = digitalio.Direction.INPUT

# Latch current button state
latch.value = True
time.sleep(0.02)  # longer settle for reliable reading
latch.value = False

# Clock in 8 bits
# Key index: 0:B  1:A  2:START  3:SELECT  4:RIGHT  5:DOWN  6:UP  7:LEFT
bits = 0
for i in range(8):
    clock.value = False
    time.sleep(0.02)
    if data.value:
        bits |= (1 << (7 - i))
    clock.value = True
    time.sleep(0.02)

latch.deinit()
clock.deinit()
data.deinit()

if bits != 0:
    storage.enable_usb_drive()   # any button held: CIRCUITPY visible, CircuitPython cannot write
else:
    storage.disable_usb_drive()  # no button held: CIRCUITPY hidden, CircuitPython can write



# import board
# import digitalio
# import storage
# import time
# import keypad
# # ===============================
# # BOOT MODE SELECTION
# # ===============================
# # Hold ANY button during reset to mount CIRCUITPY as USB drive.
# # This allows you to view and edit presets.json on your computer.
# #
# # Normal boot (no button held): filesystem is writable by CircuitPython,
# # CIRCUITPY drive is NOT visible on your computer.
# # ===============================
# 
# keys = keypad.ShiftRegisterKeys(
#     clock=board.BUTTON_CLOCK,
#     data=board.BUTTON_OUT,
#     latch=board.BUTTON_LATCH,
#     key_count=8,
#     value_when_pressed=True
# )
#     
# time.sleep(.5) # wait a bit to read buttons
# event = keys.events.get()
# if event:
#     storage.enable_usb_drive()   # any button held: CIRCUITPY visible, CircuitPython cannot write
# else:
#     storage.disable_usb_drive()  # no button held: CIRCUITPY hidden, CircuitPython can write

