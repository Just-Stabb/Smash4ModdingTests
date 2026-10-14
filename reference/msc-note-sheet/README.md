# MSC Note Sheet (snapshot)

A CSV copy of every tab of the community **MSC Note Sheet** for Smash 4 (Wii U):

https://docs.google.com/spreadsheets/d/1-Fv8UyW2eTCjDfRnN3ObRD9e6ig4zmlhU_IzCDWh86Q

Snapshot taken 2026-10-14. The Google Sheet is the source of truth and the credit
for its contents goes to the people named in its "Found by" / "Documented by"
columns. Re-download a tab with:

```
curl -L -o Variables.csv "https://docs.google.com/spreadsheets/d/1-Fv8UyW2eTCjDfRnN3ObRD9e6ig4zmlhU_IzCDWh86Q/export?format=csv&gid=1558983544"
```

| File | Tab | gid | What's in it |
|---|---|---|---|
| `Actions_Fighters.csv` | Actions [Fighters] | 695606465 | Action (status) IDs: Wait=0x0, Fall=0xE, SpecialFall=0x10, ... |
| `Complex_CMDs.csv` | Complex CMDs | 182368183 | Syscall sub-commands (opcode + args) for each module |
| `GlobalVars_Fighters.csv` | GlobalVars [Fighters] | 1688614302 | Meaning of fighter global variables 0x0-0x3D |
| `Cmn_Scripts_Fighters.csv` | Cmn Scripts [Fighters] | 1328226474 | What the common `script_N` functions do |
| `Cmn_Scripts_Weapons.csv` | Cmn Scripts [Weapons] | 647018965 | Same for weapons/articles |
| `Variables.csv` | Variables | 1558983544 | Work/param variable IDs (`0xXYZZZZZZ`), key at the bottom |
| `Var_operations.csv` | Var operations | 2090927365 | `sys_16` / `sys_17` WorkModule operations (get/set/flag) |
| `STrans_ID.csv` | STrans ID | 1823030803 | Status transition IDs (`0x1E......`) |
| `STransGroup_ID.csv` | STransGroup ID | 519700953 | Status transition group IDs (`0x1F......`) |
| `Syscalls.csv` | Syscalls | 1909700739 | Syscall number -> module |
| `Inputs.csv` / `Inputs2.csv` | Inputs / Inputs2 | 83238330 / 912531798 | Input global vars and bitmasks |
| `Kinetic_Types.csv` | Kinetic Types | 60035255 | Kinetic handler IDs |
| `Global_GFX_IDs.csv` | Global GFX IDs | 1664318682 | Common effect IDs |
| `Actions_Kirby_Copy_Abilities.csv` | Actions [Kirby Copy Abilities] | 481517161 | Kirby copy action IDs |
| `MSC_CommonTranslated.csv` | MSC CommonTranslated | 0 | Function names for the common script table |
| `ASM_General_Notes.csv` | ASM + General Notes | 1995035336 | Interpreter / syscall table addresses |
| `Other.csv` | Other | 1146291539 | Misc notes, action-script keys, decompiled fighter `main()` |
