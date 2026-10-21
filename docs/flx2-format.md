# flx2: the in-battle HUD movie format

The battle HUD (`data/ui/info/<name>/`) uses Flash-like movies in a format with the magic `flx2`. Each
folder holds `<name>.flx` (the movie), `texlist.lst` (`TLST`, the images and where they sit on the
textures), and `img-NNNNN.nut` (the textures). Some folders use Lumen `.lm` instead. Everything is
big-endian.

Tools:

- `tools/flx.py`: read, edit and write `.flx` and `texlist.lst`, byte-exact for every sample. It also has
  `info` (dump) and `check` (round trip).
- `tools/flx_render.py`: render a frame to PNG.
- `tools/dmg_trait_badge.py`: the worked example. It adds a new clip to `dmg.flx`.

The loader is at `0x032CEFA4`. The runtime ("lumen", `0x032C8000`–`0x032DA000`) is described in the
HUD research notes.

## Model

- A movie is a list of **sprites** (movie clips). Sprite 0 is the root, drawn on the stage
  (`width × height`, normally 1920×1080).
- A sprite has frames, frame labels and **keyframes**.
  - Each frame points to one of its sprite's keyframes.
  - A keyframe is the **whole display list** of its frames, not a delta: a list of placements, front
    to back.
- A **placement** puts one of these in a child slot of the sprite:
  - an image (a `texlist.lst` symbol),
  - a sprite instance, named or unnamed,
  - a dynamic text field.

  Placements of sprites carry a transform and a colour transform. Images and texts carry neither: they
  sit at their rectangle in their own sprite, so anything that moves is an image wrapped in a sprite.
- **Slot** ("depth count" in the sprite record) identifies a child across keyframes. The same slot with
  the same character is the same instance, which keeps its own timeline state. A new character in a slot
  is a new instance.
- **Depth** orders the list. Higher depth is drawn in front, and every list is sorted by depth,
  descending. The converter gave every placement of a sprite its own depth.
- Child sprites play their own timelines.
- Frame **actions** are native code. A keyframe's action is an index into the game's per-sprite function
  table at `0x102FCEB4` (`[[0x102FCEB4 + 4*sprite] + 4*action]`, called with the instance). The bodies
  are compiled ActionScript such as `stop()` or `gotoAndPlay("ko_blink")`, and none of them are in the
  file. In `dmg.flx` that table has 0x5F entries, so **new sprites must not have actions**
  (`0xFFFF`).
- The game finds instances **by name**: `root.child("dmg_1").child("ko_mc")`, compared by interned string.
  It drives them with goto label or frame, stop, play, set visible, alpha and position.

## Header (0x68 bytes)

| off | type | |
|---|---|---|
| 0x00 | char[4] | `flx2` |
| 0x04 | u32 | background colour 0xRRGGBB (dmg 0x006600; authoring only) |
| 0x08 | u16 | fps (60) |
| 0x0A | u16×2 | stage width, height (1920×1080; `dmg_drc` is 854×480, the `aurora_*` files are 960×540) |
| 0x0E | u16×13 | section counts, in section order (below) |
| 0x28 | u16×6 | not read by the loader. They look like converter statistics (dmg: 760, 192, 945, 0, 8, 0). The 5th is non-zero only in files with text fields. `flx.py` keeps them as they are. |
| 0x34 | u32×13 | runtime pointer slots, one per section. They are 0 in the file. |

## Sections

Sections follow from 0x68 in this order. A section is present **only if its count is non-zero**. Each
one is a `u32 size` followed by `size` bytes, with records packed and the end padded to 4 bytes. There
are three *array* sections: display lists, images and strings. Each is a section of `count × u32` zeros
(the loader fills in the pointers), followed by `count` records of `u32 size` + data.

| # | count @ | record | content |
|---|---|---|---|
| 0 | 0x0E | 24 | **sprites** |
| 1 | 0x10 | variable | **transforms** |
| 2 | 0x12 | 12 | **colour transforms** |
| 3 | 0x14 | 20 | **infos**: instance names and rectangles |
| 4 | 0x16 | 16 | **text fields** |
| 5 | 0x18 | 12 | **text formats** |
| 6 | 0x1A | 8 | **keyframes** |
| 7 | 0x1C | 16 | **placements** |
| 8 | 0x1E | array | **display lists**, one per keyframe (count = keyframe count) |
| 9 | 0x20 | 8 | **labels** |
| 10 | 0x22 | 2 | **frames**: keyframe of each frame |
| 11 | 0x24 | array | **image names** |
| 12 | 0x26 | array | **strings** |

### 0 sprite (24)

`u32 name, u16 frames, u16 keyframes, u16 labels, u16 slots, u32 first frame, u32 first keyframe, u32
first label`.

- The `first` fields index the global frames, keyframes and labels tables. A sprite owns
  `[first, first + count)` of each, and the sprites' ranges follow each other in sprite order.
- `name` is a string index (0, `"undefined"`, in every sample).
- `slots` is the number of child slots the sprite uses ("depth count"). It must be greater than every
  placement slot in it.

### 1 transform (variable)

A flag byte, then the fields that are present, in this order:

| flag | field | default |
|---|---|---|
| 0x01 | f32 x | 0 |
| 0x02 | f32 y | 0 |
| 0x04 | f32 scale x | 1 |
| 0x08 | f32 scale y | scale x |
| 0x10 | u16 angle A | 0 |
| 0x20 | u16 angle B | A |

- Angles are 0x10000 = 360°, clockwise on screen (y points down).
- A alone is a rotation.
- With both angles, A is Flash's skewX (the y axis's angle) and B is skewY (the x axis's angle).
  `0x33 … 0, 0x8000` mirrors horizontally; `0x33 … 0x8000, 0` mirrors vertically. This was checked on
  `go_us_en`'s mirrored quarters.
- The matrix is `a = sx·cos B, b = sx·sin B, c = −sy·sin A, d = sy·cos A`.
- Flag combinations seen: 0x03, 0x07, 0x0F, 0x13, 0x17, 0x1F, 0x33, 0x37, 0x3F.
- Records are **byte-packed** (not aligned). Placements reference a transform by its **byte offset**
  into this section.

### 2 colour transform (12)

`u8 mul[4], s16 add[4]`, channels A R G B.

- `out = in × mul / 100 + add`, with add in 0–255 units.
- mul goes up to 200; `100 100 100 100` is identity.
- Alpha fades are mul A 0–100.

### 3 info (20)

`u32 name, f32 x, y, w, h`. `name` is a string index or `0xFFFFFFFF`.

- Named entries, with a zero rect, give a sprite placement its **instance name**.
- Unnamed entries are the **quad of an image** or the **box of a text field**, in the sprite's
  coordinates. The image is stretched to it.
- Entries are shared, deduplicated.

### 4 text field (16) and 5 text format (12)

Text field: `u32 name, u16 width, u16 height, u32 1, u32 format`.

- `name` is the message / variable string, e.g. `STR201$66` or `MmenFigN_Fox$12`.
- `format` indexes section 5.

Text format: `u32 text, u32 0xRRGGBBSS, u8 align?, u8 ?, u8 ?, u8 0`.

- `text` is the authoring text: often the name of the image the game renders the text into
  (`inf_dmg_mii_n_rep_01`), sometimes Shift-JIS sample text.
- `RRGGBB` is the colour and `SS` the font size.
- Text placements sit in the info box. The rendered text is a run-time texture.

### 6 keyframe (8)

`u16 action, u16 count, u32 list`.

- `action` is `0xFFFF` or the native action index.
- `count` is the number of entries in the display list.
- `list` is the index of that list in section 8. It always equals the keyframe's own index.

### 7 placement (16)

`u16 kind, u16 slot, u16 char, u16 depth, u16 blend, u16 transform, u16 colour, u16 info`. `0xFFFF` = none.

| kind | char | transform / colour | info |
|---|---|---|---|
| 0 image | image index (section 11) | none | its quad |
| 1 sprite | sprite index | yes | none |
| 2 named sprite | sprite index | yes | named entry: the instance name |
| 4 text | text field index | none | its box |

- `transform` is a byte offset into section 1.
- `blend` is 0, or 9 on glow and flash effects, where it looks additive.
- Placements are global and shared: identical placements are stored once, even across sprites.

### 8 display list

Per keyframe: `count × u16` placement indices, front (highest depth) first, padded to 4 bytes.

### 9 label (8), 10 frame (2)

- Label: `u32 frame (0-based, within the sprite), u32 string`.
- Frame: `u16`, the keyframe index relative to the sprite's first keyframe. A static run of frames
  repeats the same keyframe.

### 11 images, 12 strings

Records of `u32 size` + text, NUL-terminated and zero-padded to 4 bytes (size includes the padding).

- Images are the symbol names looked up **by name** in `texlist.lst`. Their order differs from the
  texlist.
- Strings are Shift-JIS. String 0 is `"undefined"`.
- Labels, instance names, text names and sprite names all point into the strings. Equal strings are
  stored once.

## texlist.lst (TLST)

| off | |
|---|---|
| 0x00 | `TLST` |
| 0x04 | u32 texture slot count |
| 0x08 | u16 image count |
| 0x0A | u16 slot table offset (0x10) |
| 0x0C | u16 image table offset |
| 0x0E | u16 name table offset |
| 0x10 | u32 per slot: **0** = the texture is the file `img-NNNNN.nut` in the folder, where NNNNN is the slot number. **0x01000000** = the texture is supplied at run time (fighter portraits, stock icons, series marks, rendered text). |
| image table | 32 bytes per image: `u32 name, u32 name (same offset), f32 u0, v0, u1, v1, u16 w, u16 h, u16 slot, u16 0` |
| name table | NUL-terminated names in image order, then 0–3 bytes of padding |

- UVs are 0–1 with the origin at the top left. w and h are the image's size in pixels.
- The loader (`0x03091A70`) loads **every `*.nut` in the folder**. It takes the slot from the five
  digits of the file name (`0x0289A7F8` parses `img-NNNNN`), and the slot must be below the slot count.
  Then, for each flx image, it looks the texlist entry up by name (`0x0289AC60`).
- Each `.nut` in the samples holds one texture. The formats seen are:
  - BC3: colour art (one file is RGBA8).
  - BC5: R = luminance, G = alpha (the damage digits; tinted by colour transforms).
  - BC4: alpha only (white).
- A texture's GIDX id must be unique in the game. The UI uses 0x28000000–0x28006395, and
  `tools/add_stage.py` uses 0x2800FF00 and up.

## dmg.flx (damage panel)

- **Root** (sprite 0) has one label per layout: `init`, `dmg_1`…`dmg_8` (by player count), `dmg_emy`,
  `dmg_emy_2..4`, `stadium`, `dmg_emy_r`, `dmg_rest`, `dmg_fgr_1/2`. Each layout places named panel
  instances **`dmg_1`…`dmg_8`** (y = 930).
- The panel sprites are one per layout. All of them have the same 14 children:

  | sprite | layouts |
  |---|---|
  | 1 | 5–8 players |
  | 2 | small panels of the `dmg_emy*` layouts |
  | 3 | 1–2 players, stadium |
  | 4 | 3–4 players |

- The 14 children of a panel (sprite indices):

| instance | sprite | content |
|---|---|---|
| `area_mc` | 18 / 20 / 23 / 24 | player colour plate (`com_area_N`, run time) |
| `mark_mc` | 17 | series mark (run time), labels `chr_1..8` |
| `face_bg_mc`, `face_mc` | 16, 15 | portrait background / portrait (`inf_dmg_face_rep_0N`, run time) |
| `lv_mc` | 14 | CPU level (`pos_1`, `pos_2`, `off`), digits in sprite 30 |
| `name_bg_mc`, `name_col_mc` | 13, 11 | name plate (labels `col_1..8`, `master`, `crazy`, ...), Mii name text |
| `num_mc` | 12 / 19 / 22 | **damage percent**: `num_1..3` = digit count; `col_1` (ones) … `col_3`, `col_4` = `%`; each digit is `col_mc/col_mc/{base_mc, grd_mc, ln_mc}` (sprites 94 / 93 / 92) with labels `num_0..9` |
| `stock_mc` | 10 / 21 | stock icons (`p_1..8`, `stock_0..2`, `coin_0..5`), icons in sprite 38 (`com_stock_20_rep_0N`, run time) |
| `mnd_mc` | 9 | **Shulk's Monado arts**: labels `in`, `select`, `press`, `out_loop_5..1`; children `press_mc` (33), `mode_mc` (34), `after_mc` / `before_mc` (36), `in_1..3` (35). Each has labels `mode_1..5` = jump, speed, shield, buster, smash (`inf_dmg_monado_mode_*`). |
| `sp_mc` | 8 | `sel_dg_1..4` (31) / `base_dg_1..4` (32) cells with the `inf_sp_g_*` / `inf_sp_d_*` / `inf_sp_e_*` art. A game-mode element, not a fighter gauge. |
| `score_mc` | 7 | score digits (`score_1..5`) |
| `ko_mc` | 6 | **Little Mac's KO meter**: labels `num_0..num_10` (chevrons `inf_dmg_ko_set_0..a`), `ko`, `ko_blink`, `off`. KO burst: sprites 27–29 (`inf_dmg_ko_2..4`). |
| `shtdwn_mc` | 5 | shutdown / point popups `pt_p` (25), `pt_m` (26) |

Renders of the samples: `flx_render.py` with, for example, `ko_mc=num_7` or `col_1/*=num_4`.

## Adding a clip

`tools/dmg_trait_badge.py` adds the Kirby trait badge. The steps are:

1. **Images.** Append the names to the flx images (`Flx.add_image`). Add one texlist entry per image
   (`Tlst.add(name, slot, x, y, w, h, tex_w, tex_h)`), using the same name.
   - The pixels can go in a **new texture**: append a texlist slot with flag 0 and write
     `img-<slot>.nut` (`nut.write_ntwu`, unique GIDX id).
   - Or they can go in **free space of an existing file texture**: re-encode it with `nut.py replace`
     and point the entries' UVs there. dmg's atlases are nearly full, so the badge uses a new
     texture.
2. **Sprite.** Use `Flx.add_sprite(frames, labels)`. It appends the frames, keyframes, display lists,
   labels and the sprite record, and sets the slot count.
   - Each frame is a list of placements. An image placement is `Flx.image_place(name, w, h)`; it adds
     the info quad.
   - Keyframe actions stay `0xFFFF`.
   - Appending at the end shifts no existing index.
3. **Instance.** `Flx.sprite_place(sprite, 'trait_mc', Transform.make(x, y, scale))` adds the transform,
   colour and named info (the string). `Flx.insert_place(parent, place)` then gives it a new slot
   (= the parent's slot count, which is raised), a depth above everything, and inserts it into every
   keyframe list of the parent at its depth.
4. `flx.write` recomputes every count, size, offset (transform offsets included) and the keyframe list
   indices. The unknown header words are left alone.

The badge adds sprite **0x5F**: 6 frames (`normal`, `rush`, `zoning`, `strike`, `juggernaut`,
`technical`), one 256×64 image each, with no actions. `trait_mc` is placed in panel sprites 1–4 at:

| panel sprite | trait_mc (x, y), scale |
|---|---|
| 1 | (−2, −52), 0.4 |
| 2 | (−30, −27), 0.4 |
| 3 | (24, −58), 0.5 |
| 4 | (24, −58), 0.5 |

That is above the damage percent and right of the CPU level, in the band Little Mac's KO meter uses.
The images are `inf_dmg_trait_<name>` on the new texture slot 133, `img-00133.nut` (BC3 256×512,
badges 80 px apart, GIDX 0x2800FE00).

The clip has no `stop()`, so it loops through its 6 frames and is visible until the game code goes to a
frame, stops it, and hides it for other fighters.

## Unknowns

- Header 0x28–0x33: six u16s the loader does not read.
- Text format bytes 1–3 (alignment and similar).
- Blend values other than 0 and 9 (none occur).
- Texlist name padding: 0–3 bytes, kept as read.
