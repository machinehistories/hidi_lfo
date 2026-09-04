# hidi_lfo
# PyGamer 16-LFO MIDI Controller

## Controls

### Joystick

**Normal mode** - **Left / Right** --- Move between LFO squares. - **Up
/ Down** --- Move between rows.

**Hold A + Joystick** - **Up / Down** --- Select a parameter. - **Left /
Right** --- Change the selected parameter value. - Holding the joystick
accelerates value changes.

### A --- Edit

Hold **A** to enter parameter editing mode. Release **A** to return the
joystick to grid navigation.

Parameters:

-   **CH** --- MIDI channel 1--16
-   **CC** --- MIDI CC number 0--127
-   **SH** --- Modulation shape
-   **MIN** --- Minimum CC output
-   **MAX** --- Maximum CC output
-   **OFFS** --- Output offset
-   **BAR** --- Clock division

### B --- Shape Paint

Press **B** on a square to advance it to the next modulation shape.

Hold **B** while moving the joystick to paint/cycle shapes across
multiple squares.

Current shapes:

`OFF → SINE → TRI → RAND → SQR → LGHT → IMX → IMY`

-   **OFF** --- No CC output
-   **SINE** --- Sine-wave modulation
-   **TRI** --- Triangle-wave modulation
-   **RAND** --- Random modulation
-   **SQR** --- Square-wave modulation
-   **LGHT** --- PyGamer light sensor mapped to MIDI CC
-   **IMX** --- PyGamer accelerometer X-axis mapped to MIDI CC
-   **IMY** --- PyGamer accelerometer Y-axis mapped to MIDI CC

### START --- Run / Stop

Press **START** to toggle modulation playback.

-   **RUN** --- MIDI modulation is active.
-   **STOP** --- MIDI modulation is stopped.
-   **REPL** --- hold the start button on startup to enable serial connection.

The lower-right display shows the current state.

### SELECT --- Globals

Press **SELECT** to open or close the Globals screen.

Use **Up / Down** to select a global setting and **Left / Right** to
change it.

Globals:

-   **CLK** --- `INT` or `EXT` MIDI clock
-   **BPM** --- Internal clock tempo
-   **PRE** --- Preset 0--9
-   **ACTION** --- `SAVE` or `LOAD`

### Saving and Loading Presets

With the Globals screen open:

1.  Set **PRE** to the desired preset slot (0--9).
2.  Select **ACTION**.
3.  Choose `SAVE` or `LOAD` with Left / Right.
4.  Press **B** to execute the selected action.

Each preset stores the configuration of all 16 LFOs:

-   MIDI channel
-   MIDI CC number
-   Shape
-   Minimum
-   Maximum
-   Offset
-   Clock division

Presets are stored in `presets.json`.

## Quick Reference

  Control          Action
  ---------------- --------------------------------
  Joystick         Navigate 4×4 LFO grid
  A + Up/Down      Select parameter
  A + Left/Right   Adjust parameter
  B                Cycle shape on current square
  B + Joystick     Paint/cycle shapes across grid
  START            Run / Stop
  SELECT           Open / close Globals
  B in Globals     Execute SAVE or LOAD

