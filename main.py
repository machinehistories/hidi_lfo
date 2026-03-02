import time
import math
import random
import board
import displayio
import terminalio
import usb_midi
import analogio
import busio
import adafruit_lis3dh
import keypad
import json
import adafruit_imageload
import array

from audioio import AudioOut
from micropython import const
from adafruit_display_shapes.rect import Rect
from adafruit_display_text import label
import adafruit_midi
from adafruit_midi.control_change import ControlChange
from adafruit_midi.midi_message import MIDIUnknownEvent

# ===============================
# GLOBAL STATE
# ===============================

# Mutable state - stored in dict so modifications work without global declarations
S = {
    "clock_mode": "internal",
    "running": True,
    "bpm": 120,
    "current_preset": 0,
    "in_globals": False,
    "edit_mode": False,
    "action_mode": "save",
    "global_index": 0,
    "selected": 0,
    "param_index": 0,
}

# ===============================
# BUTTON SETUP
# ===============================

keys = keypad.ShiftRegisterKeys(
    clock=board.BUTTON_CLOCK,
    data=board.BUTTON_OUT,
    latch=board.BUTTON_LATCH,
    key_count=8,
    value_when_pressed=True
)

# 0:B, 1:A, 2:START, 3:SELECT, 4:RIGHT, 5:DOWN, 6:UP, 7:LEFT
BTN_B      = 0
BTN_A      = 1
BTN_START  = 2
BTN_SELECT = 3

# ===============================
# JOYSTICK
# ===============================

last_joy_time  = 0
JOY_DELAY      = 0.18
JOY_FAST_DELAY = 0.05
JOY_ACCEL_TIME = 0.6
joy_hold_start = 0
joy_direction  = None

joy_x = analogio.AnalogIn(board.JOYSTICK_X)
joy_y = analogio.AnalogIn(board.JOYSTICK_Y)

# ===============================
# LIGHT SENSOR
# ===============================

light_sensor = analogio.AnalogIn(board.LIGHT)

# ===============================
# IMU (LIS3DH)
# ===============================

i2c = board.I2C()

IMX_MIN = 48
IMX_MAX = 80
IMY_MIN = 48
IMY_MAX = 80

try:
    lis3dh = adafruit_lis3dh.LIS3DH_I2C(i2c, address=0x19)
except ValueError:
    lis3dh = adafruit_lis3dh.LIS3DH_I2C(i2c, address=0x18)

lis3dh.range = adafruit_lis3dh.RANGE_4_G

# ===============================
# MIDI
# ===============================

midi = adafruit_midi.MIDI(
    midi_out=usb_midi.ports[1],
    midi_in=usb_midi.ports[0],
    in_channel=None,
    out_channel=0
)

# ===============================
# COLORS
# ===============================

COLOR_OFF            = 0x101010
COLOR_SINE           = 0x00FF80
COLOR_TRI            = 0x00FF00
COLOR_RAND           = 0xFF0000
COLOR_SQR            = 0xFF00FF
COLOR_LGHT           = 0xFFFF00
COLOR_IMX            = 0x00A0FF
COLOR_IMY            = 0xFF8000
COLOR_CURSOR         = 0xFFFFFF
COLOR_PARAM_SELECTED = 0xFFFF00
COLOR_PARAM_NORMAL   = 0xFFFFFF
COLOR_RUN            = 0x00FF00
COLOR_STOP           = 0xFF0000

# ===============================
# DISPLAY
# ===============================

display  = board.DISPLAY
main     = displayio.Group()
display.root_group = main

# Load the "HIDI" Bitmap
bitmap, palette = adafruit_imageload.load(
    "image.bmp",
    bitmap=displayio.Bitmap,
    palette=displayio.Palette
)

# Create a TileGrid to hold the bitmap and add to group
tile_grid = displayio.TileGrid(bitmap, pixel_shader=palette)
main.append(tile_grid)

# Show the logo for 2 seconds
time.sleep(2.0)

# Optional: Clear the screen or proceed to your Sync UI
main.remove(tile_grid)





CELL = 25
GAP  = 4

# --- GRID ---

grid_group = displayio.Group(x=0, y=0)
main.append(grid_group)

cells = []
for row in range(4):
    for col in range(4):
        r = Rect(col*(CELL+GAP), row*(CELL+GAP), CELL, CELL, fill=0x000000)
        cells.append(r)
        grid_group.append(r)

cursor = Rect(0, 0, CELL, CELL, outline=0xFFFFFF)
grid_group.append(cursor)

# --- PANEL ---

panel = displayio.Group(x=(CELL+GAP)*4, y=6)
main.append(panel)

PARAMS = ["CH","CC","SH ","MIN","MAX","OFFS","BAR"]
param_labels = []

for i, p in enumerate(PARAMS):
    lbl = label.Label(terminalio.FONT, text=p)
    lbl.y = i * 15
    panel.append(lbl)
    param_labels.append(lbl)

run_label = label.Label(terminalio.FONT, text="RUN", x=95, y=120)
main.append(run_label)

# --- GLOBALS OVERLAY ---

globals_group = displayio.Group(x=10, y=10)

clock_label  = label.Label(terminalio.FONT, text="CLK:INT")
bpm_label    = label.Label(terminalio.FONT, text="BPM:120")
preset_label = label.Label(terminalio.FONT, text="PRE:0")
action_label = label.Label(terminalio.FONT, text="SAVE")

for i, lbl in enumerate([clock_label, bpm_label, preset_label, action_label]):
    lbl.y = i * 20
    globals_group.append(lbl)

# ===============================
# LFO ENGINE
# ===============================

SHAPES     = ["OFF","SINE","TRI","RAND","SQR","LGHT","IMX","IMY"]
CLOCK_DIVS = [96, 48, 24, 12, 6, 3, 1]
DIV_LABELS = ["1BAR","1/2","1/4","1/8","1/16","1/32","1/96"]

class LFO:
    def __init__(self):
        self.channel       = 1
        self.cc            = 1
        self.shape         = 1
        self.min           = 0
        self.max           = 127
        self.offset        = 0
        self.div_index     = 2
        self.phase         = 0
        self.tick_count    = 0
        self.value         = 0
        self.light_filtered = 0.0

    def advance(self):
        self.phase = (self.phase + 0.02) % 1.0

    def compute(self):
        if self.shape == 0:
            return None
        if self.shape == 1:
            raw = (math.sin(self.phase * 2 * math.pi) + 1) / 2
        elif self.shape == 2:
            raw = abs(self.phase * 2 - 1)
        elif self.shape == 3:
            raw = random.random()
        elif self.shape == 4:
            raw = 1.0 if self.phase < 0.5 else 0.0
        elif self.shape == 5:
            alpha = 0.65
            new_val = light_sensor.value / 65535
            self.light_filtered = (alpha * new_val) + ((1 - alpha) * self.light_filtered)
            raw = self.light_filtered
        elif self.shape == 6:
            x, y, z = lis3dh.acceleration
            raw = max(0.0, min(1.0, (x + 39.2) / 78.4))
        elif self.shape == 7:
            x, y, z = lis3dh.acceleration
            raw = max(0.0, min(1.0, (y + 39.2) / 78.4))

        val = int(self.min + raw * (self.max - self.min)) + self.offset

        if self.shape == 6:
            val = (val - IMX_MIN) * 127 / (IMX_MAX - IMX_MIN)
        elif self.shape == 7:
            val = (val - IMY_MIN) * 127 / (IMY_MAX - IMY_MIN)

        self.value = max(0, min(127, int(val)))
        return self.value

lfos = []
for _ in range(16):
    lfos.append(LFO())

# ===============================
# PRESET SYSTEM
# ===============================
# Presets live in /presets.json on the CIRCUITPY drive.
# There is no separate RAM list - disk is the single source of truth.
# Human-readable format: named keys, shape and div stored as strings.
#
# To edit presets on your computer:
#   Hold START and press reset - CIRCUITPY will mount as USB.
#   Open presets.json in any text editor, make changes, save, then
#   reset normally (no button held) to return to run mode.
# ===============================

PRESETS_FILE = "/presets.json"
NUM_PRESETS  = 10   # presets 0-9

SHAPE_NAMES = SHAPES                          # ["OFF","SINE","TRI",...]
DIV_NAMES   = DIV_LABELS                      # ["1BAR","1/2","1/4",...]

def _shape_to_index(name):
    try:
        return SHAPE_NAMES.index(name)
    except ValueError:
        return 1  # default SINE

def _div_to_index(name):
    try:
        return DIV_NAMES.index(name)
    except ValueError:
        return 2  # default 1/4

def _lfo_to_dict(l):
    return {
        "channel": l.channel,
        "cc":      l.cc,
        "shape":   SHAPE_NAMES[l.shape],
        "min":     l.min,
        "max":     l.max,
        "offset":  l.offset,
        "div":     DIV_NAMES[l.div_index]
    }

def _dict_to_lfo(d, l):
    l.channel   = d.get("channel", 1)
    l.cc        = d.get("cc", 1)
    l.shape     = _shape_to_index(d.get("shape", "SINE"))
    l.min       = d.get("min", 0)
    l.max       = d.get("max", 127)
    l.offset    = d.get("offset", 0)
    l.div_index = _div_to_index(d.get("div", "1/4"))

def _default_lfo_dict():
    return {
        "channel": 1,
        "cc":      1,
        "shape":   "SINE",
        "min":     0,
        "max":     127,
        "offset":  0,
        "div":     "1/4"
    }

def _default_preset():
    result = []
    for _ in range(16):
        result.append(_default_lfo_dict())
    return result

def _build_default_file():
    """Build a complete default presets structure for all slots."""
    data = {}
    for i in range(NUM_PRESETS):
        data["preset_{}".format(i)] = _default_preset()
    return data

# Fixed key order for writing LFO dicts - avoids .items() which is unreliable in CircuitPython
LFO_KEYS = ["channel", "cc", "shape", "min", "max", "offset", "div"]

def _write_json(data):
    """Write the full presets dict to disk in human-readable format."""
    try:
        with open(PRESETS_FILE, "w") as f:
            f.write("{\n")
            for pi in range(NUM_PRESETS):
                key = "preset_{}".format(pi)
                f.write('  "' + key + '": [\n')
                lfos_list = data[key]
                for li in range(len(lfos_list)):
                    lfo_dict = lfos_list[li]
                    f.write("    {\n")
                    for ki in range(len(LFO_KEYS)):
                        k = LFO_KEYS[ki]
                        v = lfo_dict[k]
                        comma = "," if ki < len(LFO_KEYS) - 1 else ""
                        if isinstance(v, str):
                            f.write('      "' + k + '": "' + v + '"' + comma + "\n")
                        else:
                            f.write('      "' + k + '": ' + str(v) + comma + "\n")
                    lfo_comma = "," if li < len(lfos_list) - 1 else ""
                    f.write("    }" + lfo_comma + "\n")
                preset_comma = "," if pi < NUM_PRESETS - 1 else ""
                f.write("  ]" + preset_comma + "\n")
            f.write("}\n")
        return True
    except OSError as e:
        print("Write failed (USB mode active?):", e)
        return False

def _read_json():
    """Read presets.json from disk. Returns dict or None on failure."""
    try:
        with open(PRESETS_FILE, "r") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            print("presets.json corrupt (not a dict), rebuilding")
            return None
        return data
    except (OSError, ValueError) as e:
        print("Read failed:", e)
        return None

def save_preset():
    """Save current LFO state into current_preset slot and rewrite file."""
    data = _read_json()
    if data is None:
        print("Building fresh presets file")
        data = _build_default_file()

    key = "preset_{}".format(S["current_preset"])
    snap = []
    for l in lfos:
        snap.append(_lfo_to_dict(l))
    data[key] = snap

    for i in range(NUM_PRESETS):
        k = "preset_{}".format(i)
        if k not in data:
            data[k] = _default_preset()

    print("Saving preset", S["current_preset"], "shape0:", lfos[0].shape)
    _write_json(data)
    print("Save complete")

def load_preset(index):
    """Load a preset slot from disk and apply to LFOs."""
    data = _read_json()
    if data is None:
        print("No presets file found.")
        return

    key = "preset_{}".format(index)
    slot = data.get(key, None)
    if slot is None:
        print("Preset slot not found:", key)
        return

    for i, l in enumerate(lfos):
        if i < len(slot):
            _dict_to_lfo(slot[i], l)

def init_presets():
    """Create presets.json with defaults if it doesn't exist."""
    data = _read_json()
    if data is None:
        print("Creating default presets.json")
        _write_json(_build_default_file())

# Initialize preset file at startup
init_presets()

# ===============================
# UI HELPERS
# ===============================


def update_cursor():
    x = S["selected"] % 4
    y = S["selected"] // 4
    cursor.x = x * (CELL + GAP)
    cursor.y = y * (CELL + GAP)

def update_panel():
    l = lfos[S["selected"]]
    vals = [l.channel, l.cc, SHAPES[l.shape], l.min, l.max, ("+" + str(l.offset) if l.offset > 0 else str(l.offset)), DIV_LABELS[l.div_index]]
    for i, v in enumerate(vals):
        param_labels[i].text = PARAMS[i] + "" + str(v)
        param_labels[i].color = COLOR_PARAM_SELECTED if i == S["param_index"] else COLOR_PARAM_NORMAL

def update_grid():
    for i, l in enumerate(lfos):
        intensity = min(255, l.value * 2)

        if l.shape == 0:
            color = COLOR_OFF
        elif l.shape == 1:
            color = (intensity << 8) | intensity
        elif l.shape == 2:
            color = (intensity << 8)
        elif l.shape == 3:
            color = (intensity << 16)
        elif l.shape == 4:
            color = (intensity << 16) | intensity
        elif l.shape == 5:
            color = (intensity << 16) | (intensity << 8)
        elif l.shape in (6, 7):
            base = COLOR_IMX if l.shape == 6 else COLOR_IMY
            r = ((base >> 16) & 0xFF) * intensity // 255
            g = ((base >> 8)  & 0xFF) * intensity // 255
            b = (base & 0xFF)          * intensity // 255
            color = (r << 16) | (g << 8) | b

        cells[i].fill = color

def update_run_indicator():
    if S["running"]:
        run_label.text  = "RUN"
        run_label.color = COLOR_RUN
    else:
        run_label.text  = "STOP"
        run_label.color = COLOR_STOP

def update_globals_display():
    clock_label.text  = "CLK:" + ("INT" if S["clock_mode"] == "internal" else "EXT")
    bpm_label.text    = "BPM:" + str(S["bpm"])
    preset_label.text = "PRE:" + str(S["current_preset"])
    action_label.text = "ACTION:" + ("SAVE" if S["action_mode"] == "save" else "LOAD")

    for i, lbl in enumerate([clock_label, bpm_label, preset_label, action_label]):
        lbl.color = 0xFFFF00 if i == S["global_index"] else 0xFFFFFF

# ===============================
# CLOCK
# ===============================

internal_timer = time.monotonic()
clock_counter  = 0
display_timer  = time.monotonic()

# ===============================
# BUTTON STATE
# ===============================

pressed_buttons = set()

# ===============================
# MAIN LOOP
# ===============================

while True:

    # --- MIDI RECEIVE ---
    msg = midi.receive()
    if msg:
        if isinstance(msg, MIDIUnknownEvent):
            status = msg.status
            if status == 0xF8:    # clock tick
                S["clock_mode"] = "external"
                clock_counter += 1
            elif status == 0xFA:  # start
                S["running"] = True
            elif status == 0xFC:  # stop
                S["running"] = False

    # --- CLOCK ENGINE ---
    if S["running"]:
        if S["clock_mode"] == "internal":
            interval = 60 / S["bpm"] / 24
            if time.monotonic() - internal_timer >= interval:
                internal_timer = time.monotonic()
                clock_counter += 1

        if clock_counter > 0:
            cc_accumulator = {}

            for l in lfos:
                l.tick_count += clock_counter
                if l.tick_count >= CLOCK_DIVS[l.div_index]:
                    l.tick_count = 0
                    l.advance()
                    val = l.compute()
                    if val is not None:
                        key = (l.channel - 1, l.cc)
                        cc_accumulator[key] = cc_accumulator.get(key, 0) + val

            for (ch, cc), total in cc_accumulator.items():
                total = max(0, min(127, total))
                midi.send(ControlChange(cc, int(total), channel=ch))

            clock_counter = 0

    # --- GRID UPDATE ---
    update_grid()

    # --- BUTTON EVENTS ---
    event = keys.events.get()
    if event:
        if event.pressed:
            pressed_buttons.add(event.key_number)

            if event.key_number == BTN_SELECT:
                S["in_globals"] = not S["in_globals"]
                if S["in_globals"]:
                    main.append(globals_group)
                    update_globals_display()
                else:
                    main.remove(globals_group)

            elif not S["in_globals"]:
                if event.key_number == BTN_START:
                    S["running"] = not S["running"]
                    update_run_indicator()
                elif event.key_number == BTN_A:
                    S["edit_mode"] = True
                elif event.key_number == BTN_B:
                    l = lfos[S["selected"]]
                    l.shape = (l.shape + 1) % len(SHAPES)

            else:
                if event.key_number == BTN_A:
                    S["edit_mode"] = True
                elif event.key_number == BTN_B:
                    if S["action_mode"] == "save":
                        save_preset()
                    else:
                        load_preset(S["current_preset"])

        else:
            pressed_buttons.discard(event.key_number)
            if event.key_number == BTN_A:
                S["edit_mode"] = False

    # --- JOYSTICK ---
    x   = joy_x.value
    y   = joy_y.value
    now = time.monotonic()

    direction = None
    if x < 20000:   direction = "left"
    elif x > 45000: direction = "right"
    elif y < 20000: direction = "up"
    elif y > 45000: direction = "down"

    if direction != joy_direction:
        joy_direction  = direction
        joy_hold_start = now

    if direction and now - last_joy_time > (JOY_FAST_DELAY if now - joy_hold_start > JOY_ACCEL_TIME else JOY_DELAY):

        step = 5 if now - joy_hold_start > JOY_ACCEL_TIME else 1

        if not S["in_globals"]:

            if not S["edit_mode"]:
                moved = False
                if direction == "left":  S["selected"] = (S["selected"] - 1) % 16; moved = True
                elif direction == "right": S["selected"] = (S["selected"] + 1) % 16; moved = True
                elif direction == "up":   S["selected"] = (S["selected"] - 4) % 16; moved = True
                elif direction == "down": S["selected"] = (S["selected"] + 4) % 16; moved = True

                if moved:
                    update_cursor()
                    if BTN_B in pressed_buttons:
                        l = lfos[S["selected"]]
                        l.shape = (l.shape + 1) % len(SHAPES)

            else:
                l = lfos[S["selected"]]
                if direction == "up":
                    S["param_index"] = (S["param_index"] - 1) % len(PARAMS)
                elif direction == "down":
                    S["param_index"] = (S["param_index"] + 1) % len(PARAMS)
                elif direction == "left":
                    if S["param_index"] == 0: l.channel   = max(1,       l.channel   - step)
                    elif S["param_index"] == 1: l.cc       = max(0,       l.cc        - step)
                    elif S["param_index"] == 2: l.shape    = (l.shape - 1) % len(SHAPES)
                    elif S["param_index"] == 3: l.min      = max(0,       l.min       - step)
                    elif S["param_index"] == 4: l.max      = max(l.min,   l.max       - step)
                    elif S["param_index"] == 5: l.offset   = max(-64,     l.offset    - step)
                    elif S["param_index"] == 6: l.div_index = max(0,      l.div_index - 1)
                elif direction == "right":
                    if S["param_index"] == 0: l.channel   = min(16,      l.channel   + step)
                    elif S["param_index"] == 1: l.cc       = min(127,     l.cc        + step)
                    elif S["param_index"] == 2: l.shape    = (l.shape + 1) % len(SHAPES)
                    elif S["param_index"] == 3: l.min      = min(l.max,   l.min       + step)
                    elif S["param_index"] == 4: l.max      = min(127,     l.max       + step)
                    elif S["param_index"] == 5: l.offset   = min(64,      l.offset    + step)
                    elif S["param_index"] == 6: l.div_index = min(len(CLOCK_DIVS) - 1, l.div_index + 1)

        else:
            if direction == "up":
                S["global_index"] = (S["global_index"] - 1) % 4
            elif direction == "down":
                S["global_index"] = (S["global_index"] + 1) % 4
            elif direction == "left":
                if S["global_index"] == 0:
                    S["clock_mode"] = "internal" if S["clock_mode"] == "external" else "external"
                elif S["global_index"] == 1:
                    S["bpm"] = max(30, S["bpm"] - step)
                elif S["global_index"] == 2:
                    S["current_preset"] = max(0, S["current_preset"] - step)
                elif S["global_index"] == 3:
                    S["action_mode"] = "load"
            elif direction == "right":
                if S["global_index"] == 0:
                    S["clock_mode"] = "internal" if S["clock_mode"] == "external" else "external"
                elif S["global_index"] == 1:
                    S["bpm"] = min(300, S["bpm"] + step)
                elif S["global_index"] == 2:
                    S["current_preset"] = min(NUM_PRESETS - 1, S["current_preset"] + step)
                elif S["global_index"] == 3:
                    S["action_mode"] = "save"

            update_globals_display()

        last_joy_time = now

    if time.monotonic() - display_timer >= 0.01:
        display_timer = time.monotonic()
        update_panel()
        update_run_indicator()
