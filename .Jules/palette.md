## 2024-05-01 - Tkinter Custom Theme Focus Accessibility
**Learning:** When using custom dark themes on top of the Tkinter 'clam' style, native focus indicators are often lost or indistinguishable from the dark background. This makes keyboard navigation inaccessible for users relying on visual focus cues.
**Action:** Always provide explicit focus state mappings in `style.map` (e.g., changing bordercolor on 'focus') and set a distinct `focuscolor` (like an accent color) for widgets like `TCheckbutton` and `TButton` to ensure clear keyboard accessibility.
