## 2024-07-16 - Tkinter Dark Theme Focus States
**Learning:** In Tkinter dark themes (specifically using the 'clam' style), setting the `focuscolor` to match the dark background hides the keyboard focus indicator. Additionally, buttons need explicit `focus` state mappings for properties like `bordercolor` to show active focus during keyboard navigation.
**Action:** Always map the `focus` state to a distinct accent color for interactive ttk widgets (like `TCheckbutton` and `TButton`) when building custom themes to ensure keyboard accessibility.
