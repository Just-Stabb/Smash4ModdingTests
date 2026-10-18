# Reference resources

Spreadsheets shared by the user for future work:

- https://docs.google.com/spreadsheets/d/1FgOsGYfTD4nQo4jFGJ22nz5baU1xihT5lreNinY5nNQ/edit?gid=706249581#gid=706249581
- https://docs.google.com/spreadsheets/d/1Hx44PGtG5jcko1t_2VCE2QG_D8xzIv0LDMhCeZHGXjA/htmlview#gid=1104900741

Check these first for IDs and names (common GFX IDs, syscalls, kinetic types, status/action
lists, variables) before guessing or reverse-engineering. Common effect IDs used from MSC are
`0x1000000` + the global GFX list index (e.g. `0x17` Bomb Explosion → `0x1000017`).

Local copies: `reference/msc-note-sheet/` (MSC Note Sheet), `reference/fighter_param_attributes.csv`
(first sheet), `reference/fighter_param_vl/` (second sheet: one CSV per tab, each fighter's special
move params; downloaded 2026-10-18 with
`curl -L "https://docs.google.com/spreadsheets/d/1Hx44PGtG5jcko1t_2VCE2QG_D8xzIv0LDMhCeZHGXjA/export?format=csv&gid=GID"`).
Sm4shCommand's value tooltips are built from these (`tools/Sm4shCommand/make_tooltips.py`).

