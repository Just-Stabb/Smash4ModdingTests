# fighter_param_vl: per-fighter variable-list params

`param/fighter/fighter_param_vl_<name>.bin` holds everything about a fighter that isn't in the
shared stat table (`fighter_param.bin`, the fighter_param write-up): per-motion values,
hurtboxes and other shapes, the special-move params (one block per custom slot), the "category
4" block (often Final Smash values), and fighter-specific blocks, including the params of the
fighter's articles (projectiles, items). Found by static analysis of `cross_f.rpx` (memory
addresses) and the vanilla param dump.

How sure each fact is:
- **(code)**: read in the executable or an MSC script (address / function given).
- **(emulated)**: the game's own parser was run in an emulator on every vanilla file.
- **(inferred)**: worked out from the data.

Files:

| File | What |
|---|---|
| `tools/fighter_param_vl.py` | dump / get / set / new / check / test, with the exact layout per fighter and labels from the CSVs |
| `reference/params/vl/vl_schema.json` | the layout of every fighter kind's file (recovered from the game's parser) |
| `reference/params/vl/<Character>.csv` | the community sheets (`reference/fighter_param_vl/`) aligned to the layout, with IDs checked, the 4th slot added, new descriptions, a confidence and the evidence for each value |
| `reference/params/vl/General.csv` | the groups every fighter has (1-16 and the category-4 block) |

Related: `docs/params/fighter_files.md` (shapes: hurtboxes, ground box, ledge boxes, attach
points, motions; `tools/vl_shapes.py`), `docs/native-notes.md` (WorkModule), the
fighter_param write-up.

---

## 1. File format (code)

Generic param stream, big-endian:

- Header: `FF FF 00 00`, then a u32 count of named tags (0 in every vl file). If the first byte
  isn't `FF` the game rewinds and parses the stream with no header (`0x033B452C`).
- Values: a type byte and the data. The type numbers, from the game's readers
  (`0x033B53E8`-`0x033B5444` and the width table `0x1019C258`):

| Type | Value | Width class |
|---|---|---|
| 1 | s8 | byte |
| 2 | u8 | byte |
| 3 | s16 | half |
| 4 | u16 | half |
| 5 | u32 | word |
| 6 | s32 | word |
| 7 | f32 | word |
| 8 | string (u32 length + bytes) | - |
| 0x20 | vector: u32 entry count, then the entries | - |

(`tools/s4param.py` labels 1 / 2 and 3 / 4 the other way round; the game only checks the width
inside packed structs, so it doesn't matter for vl files.)

**The file has no layout of its own.** There are no group sizes or field names: the reader is a
C++ serialization framework (`0x033B3900`-`0x033B5D84`) driven by a describe function compiled
for each fighter kind. Members are read in order:

- **vector** (`0x033B5448`): token `0x20` + count, then `count` entries, each read by the
  element's describe function (op 2); the element can itself contain vectors;
- **packed struct** (`0x033B5500`): fields described by a nibble string in `.rodata` (low 2
  bits: 0 byte, 1 half, 2 word, 3 = padding / end; high 2 bits: repeat - 1; nibble `F` ends).
  Each field must be a value token of the right width (`0x033B4D58`), otherwise the archive's
  error flag is set and **everything after it is skipped**;
- **scalars** of a fixed type.

**Manifold confirms / adds** (Manifold by Fitz Null, zlib License,
https://gitlab.com/fitz.lol/manifold, `scripts/decode_param_format.js`; checked against
`0x033B5500`):
- Nibble `i` is `byte[i >> 1] >> (4 * (i & 1))`: **low nibble first**.
- A type-3 nibble with repeat 1-3 **skips that many bytes of the output struct** (alignment
  padding). It reads no token from the stream. Repeat 4 (`F`) ends the struct.
- A field whose token has the wrong width is not stored, and **the output pointer doesn't move**.
  Besides the error flag, every later field of that struct lands one field early.

Manifold's example string `42 27 38 0E 6B CC F0` decodes as:
- `u32, u8 x2`, 2 bytes of padding;
- `u32, u8 x3`, 1 byte of padding;
- `u32 x4, u8`, 3 bytes of padding;
- `u32 x2, u8 x9`;
- end.

So the fields of every struct are mandatory and only vector counts are free. A struct that
follows a vector has no marker of its own: in the token stream it looks like extra values at the
end of the previous "group", which is why the community sheets have rows with odd IDs after
group 16 (the category 4 block) and why `s4param.py` can't split some groups.

**(emulated)** The analysis script `emu_vl.py` (section 10) maps the RPX into Unicorn, runs each kind's
constructor (below) with the file as the stream, hooks the allocator and the stream read, and logs
every member visit. Every vanilla file (65 kinds) is consumed to the last byte with no error;
the visits give `vl_schema.json`.

## 2. How the game loads it (code)

- `0x02EA6BC4(mgr, kind)`, called from fighter creation `0x02E11C60`; `mgr = *0x102FF448`.
  Path = `"param/fighter/" + name + ".bin"`, names `0x10353DB4` (kind-indexed: `miifighter` = 0,
  Kirby 8 ... `miienemyg` 0x40). Refcount at `mgr + 0x1220 + 4*kind`.
- A 65-case switch (`0x02EA6CB4`) calls the kind's constructor (`0x02E902D8` for kind 0 ...,
  list: section 10, `cases.py`): it builds the struct (vector members set up with
  `0x033B3D94(member, entry size, element fn)`), stores the describe callback in its
  descriptor and parses. The struct pointer goes to `mgr + 0x111C + 4*kind` (and
  `[mgr+0x2574] + 0x320 + 4*kind`). `mgr + 0x1734 + 4*kind` = its group 5 (hurtboxes);
  `mgr + 0x1838 + kind*0x24` = attach-point lists (groups 9, 10). Some kinds also copy a pointer
  from another param table (`0x02EA8D50`).
- `testfighter` has a file but no kind: it is never loaded.
- `0x02EA9008` copies group 1 into the motion table.

## 3. Layout

Every kind's struct starts with the same 16 vectors (groups 1-16 of the community numbering) and
a block at `+0x140`; fighter-specific members follow. Vector = 0x14 bytes `{element fn, entry
size, count, data, flag}`.

| Member | Offset | Group | Entry | What |
|---|---|---|---|---|
| m0 | 0x00 | 1 | 6 x u8 | per motion (count = motion count) |
| m1 | 0x14 | 2 | 2 words | idle (Wait) animation odds |
| m2 | 0x28 | 3 | 2 words | crouch idle odds |
| m3 | 0x3C | 4 | u32 + 3 f32 | ground box (ECB) bones |
| m4 | 0x50 | 5 | 12 words | hurtboxes |
| m5 | 0x64 | 6 | u32 | 3 unknown values |
| m6 | 0x78 | 7 | 4 f32 | ledge-grab boxes |
| m7 | 0x8C | 8 | 5 words | Final Smash aura bones |
| m8 | 0xA0 | 9 | 7 words | attach points (joint IDs 10000+n) |
| m9 | 0xB4 | 10 | 7 words | attach points (11000+n) |
| m10 | 0xC8 | 11 | 7 words | unknown |
| m11 | 0xDC | 12 | 6 words | special-param modifiers |
| m12 | 0xF0 | 13 | per kind | **neutral special**, 4 entries = custom slots |
| m13 | 0x104 | 14 | per kind | **side special** |
| m14 | 0x118 | 15 | per kind | **up special** |
| m15 | 0x12C | 16 | per kind | **down special** |
| m16 | 0x140 | (after 16) | per kind | **category 4 block** (struct or one scalar; PAC-MAN has none) |
| m17+ | | 17+ | | fighter-specific (see below) |

Fields of every group: `reference/params/vl/General.csv` (with evidence); groups 4, 5, 7, 9, 10
in detail: `docs/params/fighter_files.md` section 3.

Group numbers: the N-th `0x20` marker of the vanilla file. Nested vectors get their own numbers
(Kirby's jump block m17 is groups 17-19: four floats, then a 5-entry and a 12-entry vector), and a
struct member never gets one. The tool accepts `g<N>` as an alias.

Fighter-specific members are vectors (lists, or 4-entry per-custom-slot blocks), structs and
scalars. Two kinds:

- **article (weapon) param blocks**: 194 accessor functions map 186 members of 55 kinds to
  their articles (`role: weapon` in the schema, e.g. Kirby m18 `starmissile`, m19
  `finalcutter`, m20 `hammer`, m21 `stone`). See section 4.
- the rest: read directly by the fighter's own native code (section 5), e.g. the multi-jump
  block (Kirby, Meta Knight, Pit, Dark Pit, Dedede, Jigglypuff, Charizard).

### Per kind

Words of each WorkModule block (category 4 = m16, 5-8 = one entry of m12-m15), from the
size tables `0x1012F638` (u16 per kind, category 4) and `0x1012F6BC` / `F700` / `F744` / `F788`
(u8 per kind, categories 5-8). "MSC here" = a vanilla decompile was available for this work.

| Kind | Name (CSV) | Members | Cat 4 / 5 / 6 / 7 / 8 (words) | Weapon blocks (member: article) | MSC here |
|---|---|---|---|---|---|
| 0x00 | miifighter (Mii_Brawler) | 20 | 9 / 10 / 36 / 21 / 29 | m17:hat, m18:ironball |  |
| 0x01 | miiswordsman (Mii_Swordsman) | 31 | 1 / 15 / 42 / 31 / 27 | m20:hat, m22:chakram, m25:lightshuriken, m28:tornadoshot |  |
| 0x02 | miigunner (Mii_Gunner) | 49 | 9 / 13 / 16 / 32 / 23 | m18:hat, m20:rapidshot_bullet, m22:gunnercharge, m25:miimissile, m28:supermissile, m31:grenadelauncher, m34:flamepillar, m37:stealthbomb, m39:stealthbomb_s, m40:bottomshoot, m41:groundbomb, m43:attackairf_bullet, m45:laser, m47:fullthrottle |  |
| 0x03 | mario (Mario) | 24 | 1 / 1 / 5 / 11 / 4 | m18:fireball, m20:pump, m21:pumpwater, m22:hugeflame | yes |
| 0x04 | donkey (Donkey_Kong) | 19 | 32 / 3 / 5 / 10 / 3 | m17:soundeffect |  |
| 0x05 | link (Link) | 27 | 12 / 5 / 2 / 10 / 1 | m18:boomerang, m19:bowarrow, m20:clawshotall/clawshot, m21:navy |  |
| 0x06 | samus (Samus) | 35 | 9 / 4 / 6 / 8 / 20 | m18:gbeam/gbeam, m19:cshot, m22:missile, m25:supermissile, m28:bomb, m30:laser, m32:laser2, m34:gun |  |
| 0x07 | yoshi (Yoshi) | 32 | 26 / 1 / 33 / 12 / 3 | m20:tamago, m21:star, m30:firebreath, m31:firecannon |  |
| 0x08 | kirby (Kirby) | 23 | 1 / 34 / 9 / 7 / 11 | m18:starmissile, m19:finalcutter, m20:hammer, m21:stone | yes |
| 0x09 | fox (Fox) | 26 | 2 / 5 / 16 / 16 / 6 | m19:blaster, m20:blaster_bullet, m22:illusion, m23:landmaster, m25:landmaster_shell |  |
| 0x0A | pikachu (Pikachu) | 23 | 5 / 9 / 18 / 11 / 5 | m18:dengekidama/dengeki, m19:kaminari/cloud, m20:vortex |  |
| 0x0B | luigi (Luigi) | 22 | 4 / 1 / 23 / 13 / 8 | m18:fireball, m21:obakyumu | yes |
| 0x0C | captain (Captain_Falcon) | 17 | 11 / 5 / 4 / 8 / 5 | - | yes |
| 0x0D | ness (Ness) | 30 | 1 / 5 / 3 / 12 / 17 | m20:pkflash, m23:pkfire, m27:pkthunder, m29:pkstarstorm |  |
| 0x0E | peach (Peach) | 21 | 10 / 6 / 15 / 11 / 5 | m17:kinopio |  |
| 0x0F | koopa (Bowser) | 20 | 1 / 24 / 16 / 15 / 6 | m17:breath | yes |
| 0x10 | zelda (Zelda) | 27 | 9 / 4 / 6 / 14 / 3 | m18:dein, m20:dein_s, m21:phantom, m26:lightingbowarrow |  |
| 0x11 | sheik (Sheik) | 23 | 10 / 7 / 8 / 14 / 28 | m17:needlehave/needle, m22:lightingbowarrow |  |
| 0x12 | marth (Marth) | 17 | 7 / 5 / 3 / 9 / 15 | - | yes |
| 0x13 | gamewatch (Mr_Game_and_Watch) | 23 | 33 / 2 / 11 / 5 / 14 | m17:food, m20:octopus |  |
| 0x14 | ganon (Ganondorf) | 18 | 1 / 3 / 9 / 9 / 6 | m17:beast |  |
| 0x15 | falco (Falco) | 25 | 2 / 5 / 16 / 16 / 1 | m18:blaster, m19:blaster_bullet, m21:illusion, m22:landmaster, m24:landmaster_shell |  |
| 0x16 | wario (Wario) | 23 | 1 / 9 / 8 / 9 / 8 | m17:wariobike |  |
| 0x17 | metaknight (Meta_Knight) | 19 | 5 / 22 / 12 / 11 / 9 | m18:mantle | yes |
| 0x18 | pit (Pit) | 26 | 1 / 4 / 7 / 13 / 10 | m18:bowarrow |  |
| 0x19 | szerosuit (Zero_Suit_Samus) | 25 | 15 / 3 / 1 / 11 / 14 | m19:paralyzer_bullet, m20:whip, m22:cockpit, m23:gunship, m24:laser |  |
| 0x1A | pikmin (Pikmin_and_Olimar) | 28 | 32 / 2 / 3 / 24 / 1 | m17:pikmin, m25:dolfin |  |
| 0x1B | diddy (Diddy_Kong) | 31 | 47 / 9 / 5 / 20 / 5 | m18:explosion, m19:gun, m20:peanuts, m21:barreljet |  |
| 0x1C | dedede (King_Dedede) | 25 | 6 / 21 / 8 / 17 / 6 | m18:starmissile, m19:gordo, m22:star, m24:bomb |  |
| 0x1D | ike (Ike) | 18 | 14 / 9 / 19 / 5 / 15 | m17:sword |  |
| 0x1E | lucario (Lucario) | 25 | 1 / 6 / 5 / 16 / 8 | m18:auraball, m23:qigong |  |
| 0x1F | robot (ROB) | 24 | 17 / 7 / 19 / 17 / 7 | m18:beam, m21:hugebeam, m22:narrowbeam, m23:widebeam |  |
| 0x20 | toonlink (Toon_Link) | 28 | 12 / 5 / 2 / 10 / 1 | m18:boomerang, m19:bowarrow, m20:hookshotall/hookshot, m21:takt, m22:fairy |  |
| 0x21 | lizardon (Charizard) | 26 | 2 / 24 / 15 / 9 / 7 | m18:breath, m19:rockstone/rock, m20:explosion, m22:lizardonm, m23:daimonji | yes |
| 0x22 | sonic (Sonic) | 22 | 1 / 29 / 47 / 10 / 15 | m17:gimmickjump, m18:supersonic | yes |
| 0x23 | purin (Jigglypuff) | 18 | 4 / 26 / 5 / 1 / 2 | - |  |
| 0x24 | mariod (Dr_Mario) | 23 | 1 / 1 / 5 / 11 / 8 | m19:drcapsule, m21:hugecapsule |  |
| 0x25 | lucina (Lucina) | 17 | 7 / 5 / 3 / 9 / 15 | - |  |
| 0x26 | pitb (Dark_Pit) | 22 | 9 / 4 / 7 / 13 / 10 | m18:bowarrow |  |
| 0x27 | rosetta (Rosalina_and_Luma) | 32 | 1 / 19 / 3 / 16 / 18 | m18:rosettaticomissile, m26:starpiece |  |
| 0x28 | wiifit (Wii_Fit_Trainer) | 24 | 1 / 4 / 7 / 18 / 22 | m18:hulahoop, m19:sunbullet |  |
| 0x29 | littlemac (Little_Mac) | 17 | 4 / 24 / 12 / 9 / 24 | - |  |
| 0x2A | murabito (Villager) | 45 | 3 / 8 / 5 / 33 / 4 | m25:clayrocket, m29:balloon, m32:sprout, m34:sprinkling_water, m36:tree |  |
| 0x2B | palutena (Palutena) | 30 | 13 / 17 / 33 / 39 / 51 | m18:explosiveflame, m19:fireworks, m20:autoaimbullet, m22:autoreticle, m23:reflectionboard, m27:blackhole, m28:beam |  |
| 0x2C | reflet (Robin) | 24 | 25 / 12 / 3 / 14 / 12 | m17:thunder, m18:gigafire, m19:elwind, m20:chrom |  |
| 0x2D | duckhunt (Duck_Hunt) | 49 | 49 / 3 / 10 / 18 / 5 | m18:reticle, m19:can, m23:clay, m26:gunman, m43:kurofukuhat, m46:finalduck, m47:finalenemy, m48:finalbird |  |
| 0x2E | koopajr (Bowser_Jr) | 25 | 2 / 6 / 42 / 20 / 4 | m18:cannonball, m20:remainclown, m24:batten |  |
| 0x2F | shulk (Shulk) | 19 | 13 / 41 / 8 / 11 / 21 | - |  |
| 0x30 | gekkouga (Greninja) | 28 | 11 / 9 / 14 / 15 / 39 | m18:shuriken, m19:water | yes |
| 0x31 | pacman (PAC-MAN) | 65 | 0 (empty struct, 1 byte) / 6 / 33 / 12 / 4 | m49:esa, m55:trampoline, m57:firehydrant, m61:firehydrantwater |  |
| 0x32 | rockman (Mega_Man) | 40 | 17 / 5 / 1 / 10 / 10 | m17:rockbuster, m18:chargeshot, m20:hardknuckle, m21:airshooter, m28:crashbomb, m29:rushcoil, m31:leafshield, m33:blackhole, m36:rockmanx, m37:rockmandash, m38:rockmanexe, m39:shootingstarrockman |  |
| 0x33 | mewtwo (Mewtwo) | 27 | 3 / 6 / 2 / 16 / 5 | m17:shadowball, m21:bindball, m22:mewtwom, m23:search, m24:psychobreak |  |
| 0x34 | ryu (Ryu) | 21 | 48 / 12 / 33 / 28 / 26 | m17:hadoken, m20:shinkuhadoken | yes |
| 0x35 | lucas (Lucas) | 30 | 2 / 5 / 3 / 16 / 17 | m19:himohebi/himohebi, m20:pkfreeze, m23:pkfire, m27:pkthunder, m29:pkstarstorm |  |
| 0x36 | roy (Roy) | 17 | 6 / 9 / 3 / 10 / 15 | - |  |
| 0x37 | cloud (Cloud) | 21 | 15 / 11 / 11 / 19 / 13 | m18:wave |  |
| 0x38 | bayonetta (Bayonetta) | 28 | 66 / 22 / 37 / 13 / 21 | m24:bat |  |
| 0x39 | kamui (Corrin) | 20 | 43 / 14 / 32 / 17 / 19 | m17:ryusensya, m19:spearhand | yes |
| 0x3A | koopag (Giga_Bowser) | 19 | 3 / 20 / 16 / 15 / 6 | m17:breath |  |
| 0x3B | warioman (Wario-Man) | 23 | 4 / 9 / 8 / 9 / 8 | m17:wariobike |  |
| 0x3C | littlemacg (Giga_Mac) | 17 | 4 / 15 / 12 / 9 / 20 | - | yes |
| 0x3D | lucariom (Mega_Lucario) | 25 | 7 / 6 / 5 / 16 / 8 | m18:auraball, m23:qigong | yes |
| 0x3E | miienemyf (Fighting_Mii_Brawler) | 21 | 2 / 10 / 29 / 23 / 21 | - |  |
| 0x3F | miienemys (Fighting_Mii_Swordfighter) | 18 | 2 / 15 / 42 / 31 / 26 | - |  |
| 0x40 | miienemyg (Fighting_Mii_Gunner) | 23 | 9 / 13 / 18 / 36 / 23 | m18:rapidshot_bullet, m20:attackairf_bullet |  |

## 4. Param IDs and where they come from (code)

MSC and native code read params through the object's WorkModule: `get_float(id)` /
`get_int(id)` (vtable `+0x44` / `+0x84`, fighters' copy `0x02F1DBE4`). `id >> 24 & 0xF` is the
category, `id & 0xFFFFFF` the word index; the `0x10000000` bit marks an int read (same index
space as floats: a category's float and int arrays point at the same buffer, so word i is
`0x0C00000i` as a float and `0x1C00000i` as an int).

**Fighters** (`FighterWorkModule`, 0x15F4 bytes, vtable `0x1013AFFC`): categories 0 / 1 =
instance / status work, 2 = `fighter_param_common`, and 3-8 are **per-fighter copies** made
when the fighter is set up (`0x02F1BF88`, records at WM `+0x1540`, sizes `0x02F1C19C`):

| Category | IDs | Source | Copy at WM |
|---|---|---|---|
| 3 | `0x03000000`+ | the kind's `fighter_param.bin` entry (0x162 words) | `+0x20` |
| 4 | `0x04` / `0x14` | vl `+0x140` (m16) | `+0xB30` |
| 5 | `0x05` / `0x15` | m12 entry [instance int `0x10000048`] | `+0xD30` |
| 6 | `0x06` / `0x16` | m13 entry [`0x10000049`] | `+0xF30` |
| 7 | `0x07` / `0x17` | m14 entry [`0x1000004A`] | `+0x1130` |
| 8 | `0x08` / `0x18` | m15 entry [`0x1000004B`] | `+0x1330` |

- Each copy is 0x200 bytes: at most 128 words per special (Bayonetta's 66-word category 4 is the
  largest block).
- **Custom slots** (`0x02E12B4C`): the player's choice for each special (0-2); 3 or more
  becomes 0. Kinds `0x33`-`0x3C` (Mewtwo, Ryu, Lucas, Roy, Cloud, Bayonetta, Corrin, and the
  transformations) always get 0. **Entry 3 is never selected at set-up** (the community sheets
  don't list it; the CSVs now show it as Custom3). Some fighters' own code changes a slot later
  (e.g. Lucina / Roy read the slot ints in their special code; `set_int(0x1000004B)` at
  `0x027AECB0`). The community suspects Cloud uses entry 1 for Limit Break (not checked).
- **Kirby** (`0x02F1B8B0`): while he has a copy (instance int `0x100000A4` < 0x3A), category 5
  is replaced by the copied fighter's m12 **entry 0** (size from that fighter's table entry).
  So Kirby's MSC copy functions read the copied fighter's neutral-special IDs; the CSVs use
  them as evidence for those fighters. Kirby's own category 4 (`0x14000000`) is the cooldown
  of the copied Luma Shot.
- Stat boosts (equipment etc.) rescale categories 3-8 in place (`0x02F1BCEC` → `0x02F1B94C`,
  0x2C-byte records); group 12 lists special params with multipliers (see General.csv).
- Category F (`0x0F...`) is free: the repo's caves use it (`docs/position-variables.md`).

**Weapons (articles)**: a weapon's WorkModule (0x20 bytes) gets its params from the weapon
descriptor's `get_param(out, custom slot)` (descriptor `+0x18`; e.g. star missile
`0x02B03F3C`: Kirby vl `+0x164` (m18 data) + slot x 0x6C, size 0x6C). That block is the weapon's
**category 2**: `0x02000000+i` / `0x12000000+i` (Kirby's star missile MSC reads `0x0200000D`
and `0x12000013`). Descriptor `+0x24` can return a modifier list like group 12 (Final Cutter:
Kirby m22). The 194 accessors were found by their code pattern and tied to weapon kinds through
the weapon-kind switches (`cmplwi 0x184`) and the weapon name table `0x10419604`
(`getparam2.py`, section 10).

## 5. Who reads what (code)

Three ways in, all used for the evidence column:

1. **MSC**: `WorkModuleF(0, id)` / `WorkModule(0x6, id)` in the fighter's and its articles'
   scripts. Common code in every fighter script has per-kind branches (`global1` = fighter kind,
   e.g. `if (global1 == 0x16)` reads Wario's `0x06000007`); those reads count for that kind.
   Scripts also contain leftovers from the fighter they were made from (Kirby's has Mario's cape
   code), so a read only counts when its type and index fit the kind's block.
2. **Native WorkModule reads** with a constant ID (`lis/addi r4` + `get_float` / `get_int`):
   1149 sites; attributed to a kind when the function is reached from that kind's specializer
   vtable (and the status classes it installs) and the ID fits the kind's layout
   (`owners.py`, `native_attr2.py`, `cluster_attr.py`). The same ID format is used
   by other param systems (the staff-roll game, stages), so unattributed hits are ignored.
3. **Direct struct reads**: `0x02F1C2E4(WorkModule)` returns the vl struct of the object's kind
   (`[mgr + 0x111C + 4*kind]`); code then indexes a member by the slot and reads fields
   (`direct_reads.py`). Marth's, Lucina's and Roy's side / up / down special code reads its
   params this way, which is why their MSC barely touches them.

## 6. A new fighter

The layout is compiled in **per kind**, so a new fighter's vl file must have exactly the layout
of the kind (slot) it replaces: same members, same fields, same types' widths. What is free:

- every value;
- vector counts: motions (group 1, must match the motion count), hurtboxes, ECB bones,
  attach points, idle odds lists, fighter-specific lists. Special blocks (m12-m15) and weapon
  blocks need 4 entries (indexed by custom slot; slot 3 only if code sets it);
- the meaning of a special field, if the fighter's MSC is rewritten: categories 4-8 are plain
  word arrays to MSC. Fields the slot's **native** code reads (evidence "native ..." in the
  CSV) keep their native meaning; the others can be reused freely, up to the block's size
  (section 3 table). Kinds with the fewest native special reads are the easiest hosts.

The tool:

```
python3 tools/fighter_param_vl.py new OUT.bin --base marth --from <vanilla>/fighter_param_vl_marth.bin \
    --count g5=10 --count m0=700        # copy, resize vectors (copies the last entry)
python3 tools/fighter_param_vl.py new OUT.bin --template marth --from <vanilla marth file>   # same layout, all 0
python3 tools/fighter_param_vl.py set OUT.bin OUT.bin 0x05000000=45 "Counter trigger bubble size=10" --slot all
python3 tools/fighter_param_vl.py check OUT.bin --kind marth
```

(The vanilla file supplies the value types; the schema supplies the layout.)

## 7. Tool reference

```
python3 tools/fighter_param_vl.py dump FILE [--kind K] [--only m12] [--no-labels]
python3 tools/fighter_param_vl.py get FILE 0x05000003 [--slot 0|1|2|3|all]
python3 tools/fighter_param_vl.py get FILE starmissile:0x0200000D --slot all
python3 tools/fighter_param_vl.py set FILE OUT m16.1=40 g13[0].2=0.9 "Landing lag=20"
python3 tools/fighter_param_vl.py schema kirby
python3 tools/fighter_param_vl.py test <param/fighter dir>      # byte-exact round trip of every file
```

Paths: `m<i>` member, `[e]` vector entry, `.<f>` struct field, `.i<k>` item k of an entry with
nested vectors (`m17[0].i1[3]` = Kirby's 4th air-jump speed). Labels come from the CSV's
`Path` column (`[*]` = every entry). Kind from the file name or `--kind` (name or CSV name).
Round trip: all 65 vanilla files rebuild byte for byte.

## 8. The CSVs

Columns: the community's (Group, Name, Move, Variable ID, Default, Custom1, Custom2,
Description, Comment) plus **Custom3** (4th entry), **Type**, **Confidence**, **Evidence**,
**Path**. Rows follow the file: one row per field for 4-entry blocks (values per slot), one row
per value for lists (a community description given once per field is applied to every entry).
IDs are computed from the layout; where the sheet had another ID the Comment says so (e.g.
Mario's category 4 value is `0x04000000`, not `0x04000004`). Community rows that match no value
are kept at the end of their group.

Confidence: **high** = the code was read and does what the description says; **medium** = the
community description (game-tested, not checked in code, or consistent with where it is read)
or a code reading whose purpose is partly inferred; **low** = guess, an `[auto]` usage summary
from the reading code, or copied from a fighter with the same layout. Evidence lists the read
sites (MSC function, native address) and "no read in the vanilla MSC (native or unused)" for
special fields of fighters whose script was available.

Coverage. Before (the community sheets): 8633 rows, 4810 with a description (718 of them with
a "?"), IDs partly missing or off, no confidence or evidence, entry 3 missing. Now: 11372 rows
(every value from group 13 on, lists expanded; 259 community rows that match no value are kept
apart), 5773 with a description: 40 high, 5223 medium, 510 low (225 `[auto]` usage summaries,
274 copied from a same-layout fighter, 19 new hand-written ones; the rest the community's, now
graded). 953 rows have read sites as evidence; 135 community IDs were corrected. Kirby: 135 rows,
82 described (17 high); Marth: 39 / 32 (9 high); Captain Falcon: 33 / 22 (14 high).

## 9. Not known yet

- Groups 6 and 11 (General.csv): unknown; group 1 bytes 1-5 only partly checked.
- Fighter-specific non-weapon members: most are read by native code not traced here.
- Marth's counter fields 6-13, Captain Falcon's category 4 (Blue Falcon), many article fields:
  no read found (native code with IDs in registers other than r4, or tables).
- Entry 3 of the special blocks: what (if anything) selects it.
- Which fighters switch custom slots at runtime and why (Cloud's Limit Break?).

**MSC needed to finish the rest**: decompiled vanilla `script/msc/*.mscsb` (fighter and article
scripts) of every fighter not yet covered: bayonetta, cloud, dedede, diddy, donkey, duckhunt, falco, fox, gamewatch, ganon, ike, koopag, koopajr, link, littlemac, lucario, lucas, lucina, mariod, mewtwo, miienemyf, miienemyg, miienemys, miifighter, miigunner, miiswordsman, murabito, ness, pacman, palutena, peach, pikachu, pikmin, pit, pitb, purin, reflet, robot, rockman, rosetta, roy, samus, sheik, shulk, szerosuit, toonlink, wario, warioman, wiifit, yoshi, zelda. MSC used here: the fighter scripts of Kirby, Bowser, Sonic, Luigi, Marth, Captain Falcon, Mario, Greninja, Corrin, Ryu, Meta Knight, Charizard, Giga Mac and Mega Lucario, and the article scripts that came with the Kirby, Bowser, Sonic, Luigi, Mario, Captain Falcon and Charizard uploads. The articles' scripts matter as much as the
fighter's (weapon blocks are category 2 of the article's WorkModule).

## 10. Method

Analysis scripts (kept in the session scratchpad, `vl/`, not in the repo; the results they
produced are the files above): `emu_vl.py` (Unicorn run of the parser), `schema2.py` → `schemas.json`,
`export_schema.py` → `vl_schema.json`, `getparam2.py` (weapon accessors), `native_ids.py`,
`owners.py`, `native_attr2.py`, `cluster_attr.py`, `direct_reads.py` (native reads),
`msc/scan2.py` (MSC reads; `reads2.json`), `gen/canon.py` (alignment with the community sheets),
`gen/evidence.py`, `gen/annotations.py` (hand-written descriptions), `gen/gen_csv.py`.
Working notes: scratchpad `params/vl_notes.md`.

## Which copy in the user's param dump is vanilla (no clean dump available)

The user's `param - Copy/` has two sets of vl files: top level (dated 2026-02-10) and `fighter/`
(2026-10-20); 28 differ. Compared with the community sheets' Default column
(reference/fighter_param_vl/*.csv, made from vanilla), at every value both can be checked:
the top-level copy matches as well or better in all 27 comparable files (e.g. Mr. Game & Watch
95 vs 75, Bowser Jr. 85 vs 64, R.O.B. 67 vs 51, Mega Man 50 vs 43). The differing fighters
overlap the ones the user changed in fighter_param.bin (docs/params/fighter_param.md: there the top
level is vanilla and `fighter/` is the user's experiment). So: **top level ≈ vanilla, `fighter/`
= the user's edits**, for the vl files too. Neither matches the sheets fully (the sheets come from
various game versions).

Exception: the top-level `fighter_param_vl_bayonetta.bin` doesn't parse with this executable's
layout (one extra string in member 18, her shooting-bone list: "ShootingArmL_AtkOn" before
"ShootingLegR_AtkOn"), so it's likely from another game version; the `fighter/` one parses.
The layouts in vl_schema.json come from the game's parser and don't depend on values. The values
quoted in the CSVs' Default / Custom columns are the community's.
