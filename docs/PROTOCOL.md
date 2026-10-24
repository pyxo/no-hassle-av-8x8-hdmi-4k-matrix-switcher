# Manufacturer evidence and boundaries

Primary source: user-uploaded **8x8 HDMI Matrix.txt**, recovered from the referenced ChatGPT conversation's attachment. The original was inspected in full on October 24, 2026; it was not altered. Its filename identifies an 8×8 matrix but does not establish an exact model number.

The file specifies UDP (not TCP), port 5000, ASCII (not hexadecimal bytes), and RS232 at 115200, 8, 1, N. It gives all 64 physical routes and eight all-output routes. Physical outputs 1–4 are addressed as `00`–`03`; physical outputs 5–8 as `11`–`14`. All-output routing uses `04`. Input values run `00`–`07`.

A single line for output 2 / input 6 omits the otherwise consistent space before `!`. The client uses the canonical spaced form `@T 01 05 !` consistent with every other routing entry. Exact spacing acceptance on that hardware remains untested. The file says some control systems may need a carriage return; it does not require one for UDP. The user's existing UDP command uses `echo -n`, so UDP sends no CR/LF. The added serial connection defaults to the same format and offers an explicit CR option for that documented caveat.

Reboot is documented as `@T 50 !`. Power and factory-restore commands are present in the source but deliberately have no implementation in this MVP. No route query, acknowledgement, telemetry, firmware query, or response parser is documented; none is implemented. The absence of those commands from this file is not proof that no model or firmware supports them.

The prior user report confirms only selected output-1 routes and a reboot command were used in existing shell actions. This development session performed no live hardware operations. The command-reference mapping is verified against the file; automated tests verify software encodes it, not that the connected matrices execute it.
