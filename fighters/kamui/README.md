# Corrin (kamui, fighter kind 0x39)

Trait: Rush (docs/character-traits.md). `kamui.c`: her MSC.

## Trail textures

How trail textures work and how to add one: docs/acmd-params/effects.md "Trail textures: where they come from,
and adding one". Her vanilla ones: 240 / 241 `TexKamuiSwordTrace` / `TexKamuiSwordTraceAdd` (her sword:
`Sword_Glow` on joint 0x19, the blade from (0, 0.1, 0) to (0, 14, 0), BlendMode 0xB, Shader 1, blade flare
0x3390001) and 252 - 259 `TexKamuiSpearTrace` ... `07` (her spear trails, `Sword_Glow2`), in
`fighter/kamui/effect/kamui/trail/`.

### Cyan trail v1 (`corrin_cyan_trail_v1.zip`, over Greninja beetle safety; exe_v46z_gkb21; Sm4shCommand v1.7.31)

The user's picture (`trail_src/cyan_v1.png`, from `kamui_in/trail1/preview.png`: 50 x 50 RGBA, a cyan /
light-blue gradient) as a new trail texture pair for her `Sword_Glow` / `Sword_Glow2`:

| id | name | file | |
|---|---|---|---|
| 272 (0x110) | `TexKamuiSwordTraceCyan` | `effect/kamui/trail/TexKamuiSwordTraceCyan.nut` | the trail (Texture1) |
| 273 (0x111) | `TexKamuiSwordTraceCyanAdd` | `effect/kamui/trail/TexKamuiSwordTraceCyanAdd.nut` | its glow (Texture2) |

- **The picture**: 50 x 50 is not a trail texture size (the game's are 128 x 128) and it is smooth, so most
  likely a thumbnail of a larger picture; it is what we have. It is already laid out as a vanilla trail texture
  (transparent on the left = the tail end, opaque light cyan on the right = the blade), so it is used as is,
  only scaled to 128 x 128 (bicubic, in premultiplied alpha so the transparent column's black doesn't bleed in;
  a smooth gradient loses nothing at 2.56 x). Unlike her vanilla texture it doesn't fade across the blade (V),
  so the trail is a full band from hilt to tip; a version with soft edges is a one-line change to the picture.
- **The pair** (`tools/kamui_trail_build.py`): as her vanilla pair, NTP3, one texture, texture id 0, 128 x 128,
  one mip (headers byte for byte as hers); the trail DXT5 (the picture), the Add DXT1 = the picture's colour x
  its alpha x 0.3 (a soft glow of the same colour, as her vanilla Add is a dim copy of her orange; 0.3 is my
  choice: 0.5 turns the blade end white, 0 is the picture alone; `--add-gain`).
- **The ids** (`tools/kamui_trail_cave.py`): the executable's trail-name table (trail_table_cave.py's copy, 271
  names) re-laid out with the two names after its own: 272 / 273. Only the table's words in
  `[0x04B9B000, 0x04B9C000)` change. In the release chain as `tools/gekkouga_clone_cave.py`'s feature `ktrail`
  (RELEASE; the one exe the user installs, so every later Greninja build keeps it): **exe_v46z_gkb21** =
  exe_v46z_gkb20 + these words (gkb20 is RELEASE - ktrail, byte for byte; gkb21 is byte for byte gkb20 with
  `kamui_trail_cave.py` applied), with its A_release diag build (S4BR names gkb21). On gkb20 and older, 272 / 273
  must not be used (an id past the table reads garbage as a name pointer).
- **Sm4shCommand v1.7.31**: the names in the Hitbox Viewer's table (`TrailNames.cs`: it draws the trail from the
  `.nut` in her trail folder) and in `Tooltips/trails.txt` (hovering 272 / 0x110 in a texture parameter names it;
  with Corrin open her own entry comes first, with how to use it); `Sword_Glow` / `Sword_Glow2`'s help and
  examples (her forward tilt and up air with 272 / 273, her neutral air's `Sword_Glow2`).
- **Preview**: `kamui_in/trail1/trail_preview.png` (`tools/trail_preview.py`: her vanilla pair against the new
  one on a forward tilt's arc, BlurLength 8, the game's shader 1, no bloom).
- **Checks (gkb21)**: gkb20 rebuilds byte for byte without ktrail (release and diag); `gekkouga_clone_cave_test`
  392 / 0 (release), 434 / 0 (diag); import_call_check 0 on both; `supamario_ui_cave_test` (outline5 -> gkb21 + its
  diag) 0 failures; `kamui_trail_cave_test` on gkb21 0 failures (applying it again changes no byte), TtTest 32 / 0.
- **Test**: `tools/kamui_trail_cave_test.py BASE.rpx WORK [--sm4shcommand RUN_DIR]` (the table over the base and
  the game's own lookup code run on it, nothing else changed, the textures, Sm4shCommand's names / tooltips /
  help / examples).
- **Not confirmed in game.** Approximated: the Add's strength (0.3, above); the look in game also has the stage's
  lighting and bloom the preview doesn't.

Use (effect script, e.g. her forward tilt): her own `Sword_Glow` with `Texture1=272, Texture2=273` in place of
`0xF0, 0xF1`, everything else as hers.
