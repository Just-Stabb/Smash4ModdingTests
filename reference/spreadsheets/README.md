# Community Smash 4 parameter spreadsheets

Uploaded by the user (2026-11-13). The `.xlsx` files are the originals; `csv/` has one CSV per sheet
(`<workbook>__<sheet>.csv`, values only), so they can be grepped and read by tools.

| Workbook | What it holds |
|---|---|
| `Sm4sh_params.xlsx` | `fighter_param` / `_common` / `_etc` / `_equipment_ability` / `_power_up`, `battle_object`, `melee_boot_parameter`, `CollisionAttribute_cafe`, `AnimMove`, **ACMD events** (the command list), Item IDs, `enemy_param`, Enemy IDs, hitbox fields (Hitbox, Element, SFX Type, Type, Hit Bits, Facing Restriction), ledge / item grabboxes, `event_param`, the AI params, special moves' landing lag, projectile lifetimes, stages |
| `animcmd_item_params.xlsx` | items' animcmd `param.bin` (per item), with notes and a content summary |
| `Item_Common_Param.xlsx` | `item_common_param.bin` and its bitfield (#47) |

Check these before guessing a parameter's meaning or an ACMD command's arguments (also
`reference/fighter_param_attributes.csv`, `reference/params/`).
