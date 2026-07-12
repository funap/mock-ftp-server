## 2024-05-18 - Added pointer cursor to Tkinter buttons
**Learning:** Default Tkinter buttons and checkbuttons lack standard visual hover cues (like the pointer cursor) common in web and modern desktop applications, making them feel less interactive.
**Action:** When building or updating Tkinter UIs, explicitly add `cursor="hand2"` to interactive widgets (e.g., `ttk.Button`, `ttk.Checkbutton`) to provide immediate, intuitive visual feedback to users that the element is clickable.
