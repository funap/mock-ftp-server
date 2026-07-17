## 2024-05-15 - Tkinter Keyboard Navigation Focus States
**Learning:** Tkinter's 'clam' theme with custom dark palettes often drops clear focus indicators for interactive elements like buttons and checkbuttons, making keyboard navigation difficult for screen reader and keyboard-only users.
**Action:** Always explicitly map `('focus', ...)` states in `style.map` for `TButton` and set `focuscolor` for `TCheckbutton` when applying custom themes to ensure keyboard accessibility is maintained.
