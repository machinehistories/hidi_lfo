# hidi_lfo
grid of 16 lfos running in circuit python
PyGamer 16-LFO MIDI Controller — Controls
Joystick

Normal mode

Left / Right — Move between LFO squares
Up / Down — Move between rows

Hold A + Joystick

Up / Down — Select parameter
Left / Right — Change selected parameter value
Holding the joystick accelerates value changes.
A — Edit

Hold A to enter parameter editing mode.

Available parameters:

CH — MIDI channel 1–16
CC — MIDI CC number 0–127
SH — LFO/modulation shape
MIN — Minimum CC output
MAX — Maximum CC output
OFFS — Output offset
BAR — LFO clock division

Release A to return the joystick to grid navigation.

B — Shape Paint

Press B on a square to advance it to the next modulation shape.

Hold B + move the joystick to paint/cycle shapes across multiple squares.

Current shapes are:

OFF → SINE → TRI → RAND → SQR → LGHT → IMX → IMY

LGHT uses the PyGamer light sensor; IMX and IMY use its accelerometer axes.

START — Run / Stop

Press START to toggle all LFOs:

RUN — MIDI modulation is active
STOP — MIDI modulation is stopped

The lower-right display indicates the current state.

SELECT — Globals

Press SELECT to open/close the Globals screen.

The joystick then controls:

CLK — INT / EXT MIDI clock
BPM — Internal clock tempo
PRE — Preset 0–9
ACTION — SAVE / LOAD

Use Up / Down to select a field and Left / Right to change it.

B — Save / Load while Globals is open

With Globals open:

Select the desired PRE number.
Set ACTION to SAVE or LOAD.
Press B to execute it.

Presets store the configuration of all 16 LFOs, including channel, CC, shape, min/max, offset, and clock division.
