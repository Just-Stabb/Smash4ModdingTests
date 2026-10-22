# Fighter files and per-fighter data

What makes a Smash 4 fighter outside the shared param tables: the files in its own folder
(`data/fighter/<name>/`), the per-fighter records in other data folders, and the per-fighter
tables in `cross_f.rpx`. The goal is a list good enough to build a new fighter. Found by static
analysis of `cross_f.rpx` (addresses are memory addresses, as in `docs/native-notes.md`) and of
Marth's, Mario's and Kirby's folders, the `param` dump and `sound/config`.

How sure each fact is:
- **(code)**: read in the executable's code (address given).
- **(files)**: seen in the data files (checked on the fighters named).
- **(inferred)**: worked out from the data, not confirmed in the code.

Related docs: `fighter_param_vl` in general (the other groups, the struct) is covered by the
vl write-up (`scratchpad/params/vl_notes.md` for now); `fighter_param.bin` (the stats) and the
UI / character-slot side (`ui_character_db`, adding a kind) are covered elsewhere in
`docs/params/`. This page links to them where they meet.

Tools written for this page (all in `tools/`, each with a docstring):

| Tool | For | Writes |
|---|---|---|
| `vl_shapes.py` | hurtboxes, ECB bones and ledge-grab boxes in `fighter_param_vl_<name>.bin`, with bone names from the model | yes, byte-exact (`--selftest`: all 67 vl files) |
| `mtable.py` | `motion.mtable` with motion names, plus the executable's motion → animation tables (`--rpx --kind`) | yes (`--build`), byte-exact |
| `ai_files.py` | `script/ai/`: `attack_data.bin` (dump / JSON / write), `script.bin` (routines and commands), `param.bin` (AIPD layout) | ATKD and script.bin byte-exact; AIPD read-only |
| `fighter_sound.py` | how the sound folder is bound: bank ids → `soundlabeltable` rows → sound IDs, `.sqb` voice sequences, `.vat` mouth animations, `commonsoundtable.csb` | read-only |

Tools that already existed: `nud.py`, `nut.py`, `vbn_bones.py`, `omo.py` (OMO + KCAP `.pac`),
`mta.py`, `xmb.py`, `acmd.py` (ACMD `.bin`), `msclang` / `mscdec` (MSC), `s4param.py` (flat
param files), `minecraft_music.py` (nus3bank / IDSP).

---

## 1. How the game finds a fighter's files (code)

Two tables in `.data`, indexed by fighter kind (Kirby = 8, Marth = 0x12, 65 kinds 0x00-0x40):

| Table | Getter | Contents |
|---|---|---|
| `0x102FF484` | `0x0275DB24(kind)` | folder name: `mario`, `marth`, `szerosuit`, ... |
| `0x102FF588` | `0x0275DB38(kind)` | sound / effect name: `Mario`, `Marth`, `SZerosuit`, `KoopaJr`, ... |

Every path is built from those names. The path builder `0x030BB464(out, buf, kind, type, costume)`:

| type | Path | Notes |
|---|---|---|
| 0 | `fighter/%s/model/body/c%02d/` | `l%02d/` (the low-poly models) instead when `0x02FFD69C()` > 4, i.e. more than 4 fighters (8-player Smash; **inferred**), except in some modes |
| 1 | `fighter/%s/motion/%s/` (`0x030BB18C`) | sub-folder `body`, `bodyentry`, `bodyresult`, `bodyroutemap`; Bayonetta (0x38) also `body2`, ... for some costumes |
| 2 | `fighter/%s/effect/%s/` | both `%s` = the folder name |
| 3 | `fighter/%s/script/msc/%s.mscsb` | |
| 4 | `fighter/%s/script/animcmd/body/` | `game.bin`, `effect.bin`, `sound.bin`, `expression.bin`, `motion.mtable` |
| 5 | `fighter/%s/sound/snd_se_%s.nus3bank` | `snd_se_%s_c%02d.nus3bank` for costume-specific banks |
| 6 | `fighter/%s/sound/snd_vc_%s.nus3bank` | `_c%02d` likewise |
| 8 | `fighter/%s/sound/snd_vc_%s_ouen.nus3bank` | crowd cheers; Mii fighters (kinds 0-2) share `fighter/mii/sound/snd_vc_Mii_ouen.nus3bank` |
| 9 | `fighter/%s/sound/soundseq_%s.sqb` | |
| 10 | `fighter/%s/sound/voiceanim_%s.vat` | |
| 11 | `fighter/%s/script/ai/` | |
| 14 | `fighter/%s/sound/snd_se_vc_Kirby_copy_%s.nus3bank` | Kirby's voice lines for this copy ability, loaded with the fighter |

A second builder (`0x030BBBF0`) gives `snd_se_%s_common(_c%02d).nus3bank`,
`fighter/donkey/sound/donkey_seq.cms` (DK only), `fighter/%s/effect/Fin%s/` (Final Smash
effects), `fighter/%s/camera/final/` (Final Smash cameras; only for kinds whose Final Smash
has a cutscene camera: exactly 0x0C Falcon, 0x2D Duck Hunt, 0x2F Shulk, 0x32 Mega Man, 0x38
Bayonetta, 0x39 Corrin, `0x030BBDE0`) and `model/body/c%02d/` again.

The fighter's sound loader (`0x030C0C34`) registers its resources under IDs `kind * 0x11 + 6..0xF`:
SE bank, voice bank, cheers, sequences, `fighter/common/sound/soundseq_Common.sqb`, voice
animations and (for kinds other than Kirby, up to 0x39) the Kirby-copy voice bank. For a costume
other than 0 it uses `snd_se_%s_c%02d` / `snd_vc_%s_c%02d` when that file exists (any fighter), with
the costume number mapped first for some kinds: Olimar (0x1A) and Bayonetta (0x38) costume >= 4
→ c01, Little Mac (0x29) >= 8 → c01, Wii Fit (0x28), Robin (0x2C), Cloud (0x37), Corrin (0x39)
odd costumes → c01; others use the costume number as is (Bowser Jr.'s Koopalings c01-c07).

Articles (projectiles, items a fighter owns; `reference/FighterArticles.xml`), builder at
`0x030BCB10`: `fighter/<owner>/model/<article>/c%02d/`, `fighter/<owner>/motion/<article>/`,
`fighter/<owner>/script/msc/<article>/<article>.mscsb`,
`fighter/<owner>/script/animcmd/weapon/<article>/` (its own `motion.mtable` and the four ACMD
files) and `physics/...`.

The model folder loader (generic, `0x03303000`-`0x03304300`) tries these names in every model
folder: `model.xmb`, `model.vbn`, `model.nhb`, `model.moi`, `model.mta`, `model.obt`,
`model.nut`, `metal.nut`, `metal.nud`, `model.nud`, `model.flp`, `model.hkt`, `model.jtb`,
`model.mir`, `model.exi`, `model.sb`, `shadow.nut`, `shadow.nud`, `model.ik`, `model.sbwl`,
`material_anime.mfp`, and the packs `material_anime(_eye|_eyelid|_face|_hand|_body|_item0|_item1).pac`
(and `..._lang.pac`, the per-language ones; table `0x10429108`). Missing files are skipped.

Kinds are hard-wired in many places (switches with 65 cases: the vl loader `0x02EA6BC4`, the
per-kind descriptor getter `0x02E4313C`, the specializer getter `0x02E669F0`, ...). A new
fighter is far easier as a **replacement of an existing kind's slot** than as a 66th kind; see
the new-slot write-up in `docs/params/` for adding one.

---

## 2. Inventory: the fighter folder

Marth's folder (`data/fighter/marth/`), which is typical. "New fighter" says whether a new fighter
in Marth's slot needs its own file or can keep the base fighter's.

### model/

| File | Format | What it is | Tool | New fighter |
|---|---|---|---|---|
| `body/c00`..`c07/` | | one folder per costume (8 here; the count is in `ui_character_db`) | | own |
| `body/l00`..`l07/` | | the same, low-poly, for 8-player Smash | | own (can be copies of `cXX`) |
| `model.nud` | NDP3 (BE) | meshes, bone weights, materials | `nud.py`, Smash Forge | own |
| `model.nut` | NTWU | textures | `nut.py` | own |
| `model.vbn` | ` NBV` (LE on Wii U fighters) | skeleton: names, parents, hashes (the animations' bone keys), bind pose | `vbn_bones.py`, `omo.py` | own |
| `model.jtb` | u16 count1, u16 count2, u16 tables | **joint table**: maps the bone IDs used by params / ACMD / MSC to `model.vbn` indices (section 3.5) | `vl_shapes.py` reads it | own (match the base's ID order) |
| `model.mta` | MTA4 | material animation (eyes etc.) | `mta.py` | own |
| `material_anime_eye/_eyelid/_face(_lang).pac` | KCAP of `.mta` | face, eyelid, eye animations per motion (`FitMarthBodyMainJ02Win1.mta`, mouth shapes `FitMarthBodyMainVoiceS0`) | `omo.py` pac reader | own |
| `metal.nud` | NDP3 | the model used while Metal (Metal Box) | `nud.py` | own (or a copy of model.nud) |
| `model.sb` | ` BWS` | swing bones (cape, hair physics), by bone hash | none | own if the skeleton has swing bones |
| `model.nhb` | ` BHN` | helper bones (twist / shoulder correctives, `HLP_*`) | none | own if it has `HLP_*` bones |
| `model.ik` | `CRIK` | IK chains (Marth: two leg chains, bones 3-6 and 7-10) | none | own (or copy if the leg bone indices match) |
| `model.flp` | `FLIP` | 12 bytes (`FLIP 01 01 00 00 'up' 00 00`), mirroring setting | none | copy |
| `model.moi` | BE, 0x26 entries | per-mesh info by hash (unknown use) | none | own (unknown if required) |
| `model.xmb` | XMB | `type=fighter`, shadow caster, lightset, draw passes | `xmb.py` | copy |

Other model sub-folders are articles (Mario: `model/pump/`, `model/mantle/`), each a full
model folder with its own `model.jtb`.

### motion/

| Path | What | New fighter |
|---|---|---|
| `body/main.pac` | KCAP pack of OMO animations for battle, named `Fit<Name>Body<Part><Code><Motion>.omo` (`FitMarthBodyMainA00Wait1.omo`) | own |
| `body/lhand.pac`, `rhand.pac` | hand-pose animations (parts 4 and 3) | own |
| `body/<name>pt1.pac`, `<name>sw1.pac` / `pt2` | extra parts (6, 7): Marth's `marthpt1` / `marthsw1` (sword), Kirby's `kirbypt1` / `kirbypt2` | own if the skeleton has such parts |
| `bodyentry/` | entrance (`EntryL`, `EntryR`) | own |
| `bodyresult/` | results screen (`Win1`-`3`, `Win1Wait`.., `Lose`); `face.pac` = part 5 | own |
| `bodyroutemap/` | `Wait1`-`3`, `AppealHi` (used outside battles, probably the route-map figures: **inferred**) | own |

Animations are found by a hash of their **file name** (section 4), so the names matter.

### script/

| File | Format | What it is | Tool | New fighter |
|---|---|---|---|---|
| `animcmd/body/game.bin` | ACMD | per-motion scripts: hitboxes, frame timing, intangibility, armor ... | `acmd.py`, Sm4shCommand | own |
| `animcmd/body/effect.bin` | ACMD | effects, sword traces | same | own |
| `animcmd/body/sound.bin` | ACMD | sounds and voices | same | own |
| `animcmd/body/expression.bin` | ACMD | rumble, facial expressions, ... | same | own |
| `animcmd/body/motion.mtable` | u32 BE per motion kind | hash of each motion's script name (section 4) | `mtable.py` | own (same count as the base) |
| `animcmd/weapon/<article>/` | the same five files | per-article scripts | same | own per article |
| `msc/<name>.mscsb` | MSC bytecode | the fighter's status scripts (all of its behaviour) | `msclang`, `mscdec`, `docs/MSC-C_Guide.md` | own (start from the base's) |
| `msc/<article>/<article>.mscsb` | MSC | article behaviour | same | own per article |
| `ai/attack_data.bin` | `ATKD` | where and when each attack hits, for the CPU | `ai_files.py` | own (else CPUs don't know the new moves) |
| `ai/param.bin` | `AIPD` v15 | CPU behaviour tuning | `ai_files.py` (layout) | copy the base's (missing → common) |
| `ai/param_nfp.bin` | `AIPD` v15 | the same for amiibo | `ai_files.py` (layout) | copy the base's |
| `ai/script.bin` | AI script | fighter-specific CPU routines (e.g. how to recover) | `ai_files.py` | copy the base's, or own |

### sound/

| File | Format | What it is | New fighter |
|---|---|---|---|
| `snd_se_<Name>.nus3bank` | NUS3 (LE), sections PROP BINF GRP DTON TONE JUNK PACK; IDSP audio | sound effects | own, keeping the base's BINF id and label count (section 6) |
| `snd_vc_<Name>.nus3bank` | same | voice clips | same |
| `snd_vc_<Name>_ouen.nus3bank` | same | crowd cheers | same |
| `snd_se_vc_Kirby_copy_<Name>.nus3bank` | same | Kirby's voice clips with this copy | same (or keep) |
| `soundseq_<Name>.sqb` | `SQB\0` (LE) | random voice picks ("one of these 4 grunts, or nothing") | own or copy |
| `voiceanim_<Name>.vat` | `VAT\0` (LE) | which mouth animation goes with each voice clip | own or copy |

### effect/

| Path | Format | What it is | New fighter |
|---|---|---|---|
| `effect/<name>/<name>.010d0000.efc` | `EFCF` v7 (BE): effect count, model count, 0x10-byte entries, then the effect model names | maps the ACMD effect index to an emitter set in the `.ptcl` | own |
| `effect/<name>/<name>.010d0000.ptcl` | `EFTF` (Nintendo particle file) | particle emitters, textures | own (or copy) |
| `effect/<name>/model/Eff*/` | model folders | meshes used by effects (Marth's counter flash, Dolphin Slash) | own |
| `effect/<name>/trail/*.nut` | NTWU | sword-trail textures (`Sword_Trace`) | own |
| `effect/Fin<Name>/` | the same layout | Final Smash effects | own |
| `camera/final/` | camera animations | Final Smash camera (only some kinds) | own if the slot's kind loads one |

### Data outside the folder, keyed by fighter

| Where | Entry | Notes |
|---|---|---|
| `param/fighter/fighter_param_vl_<name>.bin` | the whole file | shapes (section 3), per-motion values, special-move params; vl write-up |
| `param/fighter/fighter_param.bin` | entry with word 0 = kind | stats, shield size, camera box, item grab box, ...; fighter_param write-up |
| `param/ai/fighter_ai_fighter_param.bin` | 65 entries x 72 values, value 0 = kind | CPU tuning per kind |
| `param/ai/fighter_ai_nfp_learning_param.bin` | 65 x 41 | amiibo learning per kind |
| `param/fighter/ai/fighter_ai_<name>_param.bin` | | extra CPU params for Little Mac, Cloud, Rosalina, Bowser Jr., Villager, Robin, Greninja only (`0x101255BE`...) |
| `param/sound/audience_ouen_param.bin` | 70 x 5, value 0 = index | crowd cheer timing |
| `param/sound/narration_param.bin` | 98 x 3 (sound ID, two frame values) | announcer calls |
| `sound/config/soundlabeltable.bin` | one row per bank | makes the fighter's banks playable (section 6) |
| `sound/config/commonsoundtable.csb` | one entry per fighter | three common voice clips + the cheer bank |
| `sound/config/fightermodelbanktable.mtb` | 13 entries | costume-specific banks (`_c01`...) |
| `sound/se/snd_se_narration_characall_<Name>...` | | announcer name call |
| `ui/...` (portraits `chr_00`..`chr_13`, stock icons, names in `melee.msbt`), `param/ui/ui_character_db.bin` | | UI side: new-slot write-up |
| `fighter/kirby/model/<name>cap/`, `fighter/kirby/motion/<name>body/` | | Kirby's hat and copy-ability animations (section 8) |
| `cross_f.rpx` | descriptor, motion tables, specializer | section 4; new-slot write-up |

---

## 3. Shapes: hurtboxes, ground box, ledge grab, shield ...

Smash 4's hurtboxes are **not in the model files**: they are in `fighter_param_vl_<name>.bin`,
next to the ground-box bones and the ledge-grab boxes. All three are read once, when the fighter
is set up (`0x02E13048`), from the vl object `[[0x102FF448] + 0x111C + 4 * kind]`. Group numbers
below count from 1, as the community sheet and the vl write-up do (the file's first group is 1).
`tools/vl_shapes.py` prints and edits them, with bone names.

### 3.1 Hurtboxes: vl group 5 (code)

`[[0x102FF448] + 0x1734 + 4 * kind]` = the group's descriptor (`+8` count, `+0xC` data, 0x30-byte
entries). Set-up passes it to HitModule (accessor `+0x58`) vtable `+0x4C` (`0x02C42D7C` →
`0x02C415DC`), which makes one collision shape per entry from the pool given by the last value
(`0x02C108C4` / `0x02C118E4`) and copies the whole entry into the hurtbox slot (`0x02C44354`,
0x40-byte slots).

| Offset | Type | Field |
|---|---|---|
| 0x00 | f32 x3 | capsule start (x, y, z) in the bone's space |
| 0x0C | f32 x3 | capsule end (same as start: a sphere) |
| 0x18 | f32 | radius |
| 0x1C | u32 | bone ID (3.5) |
| 0x20 | u32 | part: 0 body / head, 1 arm, 3 leg, 2 other (Yoshi) **(inferred)** |
| 0x24 | u32 | height: 0 low, 1 mid, 2 high (head) **(inferred)**; picks the high / mid / low damage reaction |
| 0x28 | u32 | 0 (Pac-Man has a 3 on one) |
| 0x2C | u32 | collision pool, always 2 |

Marth: 8 hurtboxes (WaistN body, HeadN head, RArmJ / LArmJ arms, RLegJ / LLegJ / RKneeJ /
LKneeJ legs). Mario: 10 (upper arms too). Every fighter has 1 (Olimar) to 15 (Game & Watch).
Adding or removing entries is allowed (the vector count is free; the vl write-up checked the
parser). A second reader (`0x02E56C08`) puts the hurtbox list of another object's kind (looked
up by handle) into a HitModule through vtable `+0x6C`; its context was not traced.

### 3.2 Ground box (ECB): vl group 4 (code)

0x10-byte entries: u32 bone ID, f32 x, y, z (offset in the bone's space). The set-up passes
them to GroundModule (accessor `+0x2C`) via `0x02C3D02C` (`+0x8C` data, `+0x90` count; `+0x94` /
`+0x98` = 4.0 / 4.0, `+0xDE` = 1). Each frame `0x02C39C40` takes every point's position
(ModelModule vtable `+0xF4`, bone + offset), relative to the fighter's position, and keeps the
min / max X and Y: **the ground box is the bounding box of these points**, grown to at least
4 x 4 units (x the fighter's scale; `0x02C34990`). So it follows the animation. Marth's 6
points: HeadN (-0.5 x), RArmJ, LArmJ, RKneeJ, LKneeJ, HipN.

### 3.3 Ledge-grab boxes: vl group 7 (code)

0x10-byte entries, 4 floats. Set-up stores the group in GroundModule `+0xA8`; GroundModule's
"use box n" (`0x02C36A34`) scales entry n by the fighter's scale (PostureModule) and a second
factor, and writes it to the ground collision object (`+0x204`..`+0x218`; the back extent is
also multiplied by a common param, GroundModule `+0xA4` = `fighter_param_common` word at
`mgr + 0x20C`). Entry 0 is the normal box, entry 1 the one used while tumbling (the community
sheet's "usual" / "tumble"); some fighters have a third (tether reach). Marth: (0, 8, 16, 16)
and (0, 4, 9.6, 9.6); the sheet calls the values X, Y, X2, Y2 (the tool calls them x y w h; the
exact meaning of each is **inferred**).

### 3.4 Other per-fighter shapes

| Shape | Where | Status |
|---|---|---|
| Attach points ("virtual bones") | vl groups 9 and 10: (u32 bone, f32 x y z, f32 rot x y z). The vl manager keeps them at `mgr + 0x1838 + kind * 0x24` as {group 9, count, **10000**}, {group 10, count, **11000**}, {-, -, 12000} (`0x02EA8D50`), and the fighter object copies them (`0x02E540D4`) | code; that 10000+n / 11000+n are joint IDs for these points is **inferred**. Marth's group 9: BustN, HeadN x3, HipN x2 (head ones: likely stars / sleep effects, hat); group 10: one per hurtbox bone |
| Shield size, shield break size | `fighter_param.bin` (Shield Size, Shield Break Size words) | fighter_param write-up |
| Camera box | `fighter_param.bin`: the set-up passes entry `+0x1E8` (words 0x7A-0x7E) and `+0x1FC` (words 0x7F-0x82: camera bone, x / y offset, multiplier) to CameraModule (accessor `+0x30`) at `0x02E13718`, and word 0x89 (`+0x224`) after; the sheet names 0x76-0x79 "Camera Size Front / Back / Top / Bottom" and 0x7B-0x7E "Zoom Camera Size" | code; which words are the box: fighter_param write-up |
| Item grab box, magnifying-glass bubble, effect bones | `fighter_param.bin` (sheet columns 114-148, bone IDs) | fighter_param write-up |
| Grab (catch) boxes | ACMD `Grab` commands in `game.bin` (`Catch`, `CatchDash`, `CatchTurn`) | per move, like hitboxes |
| Body push ("jostle") box | not found per fighter (JostleModule `jostle_module_impl.cpp` exists) | unknown |

### 3.5 Bone IDs and the bones the game needs (code + files)

Params, ACMD and MSC name bones by **ID**, not by name. The ID goes through the model's
`model.jtb` (Smash Forge's rule, checked against Marth's and Mario's hurtboxes and ECB, which
land on the right bones): **ID 0 = `TransN`; ID n (1..999) = `model.vbn` index `jtb table 0[n - 1]`;
ID 1000 + n = table 1 entry n** (Marth's table 1: `Saya01N`, `TsukaN`, `SwordN`, `SwordHeadN`,
`FaceN`). Marth's table 0, so IDs 1-26:

`TransN RotN HipN LLegJ LKneeJ LFootJ LToeN RLegJ RKneeJ RFootJ RToeN WaistN BustN LShoulderN
LShoulderJ LArmJ LHandN NeckN HeadN RShoulderN RShoulderJ RArmJ RHandN LHaveN RHaveN ThrowN`

(ID 3 = HipN, 12 = WaistN, 19 = HeadN, 22 = RArmJ, 24 = LHaveN, 25 = RHaveN, 26 = ThrowN). The
vl, fighter_param, ACMD and MSC of the base fighter all use these IDs, so a new fighter must ship
a `model.jtb` that maps the same IDs to its own equivalent bones (it can have any number of
other bones; animations bind by bone-name hash, so its own animations must use its own
skeleton's names).

Names: the executable does not look fighter bones up by name in battle code. The only fighter
bone-name list (`TopN TransN RotN HipN LLegJ ... BustN EyeN1-3 LShoulderN ... RHandN`, 27 names at
`0x10124D10`; IDs 0-13 in the same order, with ID 0 = `TopN`) is copied by a debug / AI function
(`0x02DDC3C0`). **(inferred)**: ID 0 / 1 (`TransN`) is the root the fighter's position drives,
`RotN` carries the facing rotation, `LHaveN` / `RHaveN` hold items, `ThrowN` is where a grabbed
or thrown fighter is held (the fighter_param bone fields and ACMD name these IDs). What happens with a missing or
out-of-range ID was not traced (Forge falls back to bone 0).

---

## 4. Motions

### 4.1 Motion kinds (code + files)

A motion kind is a number per fighter. Kinds **0x000-0x210 (529) are common** to every fighter
(same names; Marth, Mario, Luigi, Kirby, Sonic compared); from **0x211 on they are the fighter's own**
(specials, Final Smash, ... Marth 0x211-0x297, 664 in all; Kirby 1222 with the copy
abilities). Three things must have exactly the fighter's motion count:

1. `script/animcmd/body/motion.mtable`: one u32 per kind, `zlib.crc32(name.lower())` of the
   motion's **script name** (0 = none). ACMD scripts in `game.bin` etc. are keyed by the same
   hash, so this is how a motion finds its game / effect / sound / expression scripts.
2. The executable's motion table for the kind (4.2): which **animation** each motion plays.
3. `fighter_param_vl` group 1: 6 bytes per motion (vl write-up; the first is 0 on looping
   motions).

`attack_data.bin` (AI) also stores 0x211 and the own-motion count (Marth 0x87 = 664 - 0x211).

### 4.2 The executable's motion tables (code)

Each kind has a static descriptor in `.data` returned by its fighter's getter (switch
`0x02E43144`, e.g. Marth `0x02F1F780` → `0x103AB664`, Kirby `0x103829BC`):
`{u32 kind, motion info*, ...}`. Motion info (Marth `0x103AEAA8`):

| Offset | Value (Marth) | Meaning |
|---|---|---|
| +0 | `0x103AEB1C` | main table: 8 bytes per motion = {animation hash, flags} |
| +4 | 0x298 (664) | motion count |
| +8 | `0x103AB5A4` | part list: {table, part id} pairs, a table = 4 bytes per motion (animation hash) |
| +0xC | 6 | part count |

Animation hash = `zlib.crc32(file name without .omo, 0xFFFFFFFF)` (case kept; the pack loader
`0x03326740` keys every `.omo` the same way, whichever `.pac` it is in). Part ids: 3 = `rhand`,
4 = `lhand`, 5 = `face` (`bodyresult/face.pac`), 6 = `<name>pt1`, 7 = `<name>sw1` (Marth) /
`kirbypt2` (Kirby); a part with no table plays nothing. Flags (main table, as seen): `0x6000000`
looping motions (Wait1, walks, SquatWait), `0x3000000` the L/R pairs (WalkBrakeR/L, WalkFallR/L),
`0x1` turns at the end (Turn, ThrowB), `0x2` / `0x4` mostly air / ground moves, `0x28` / `0x2A` =
no animation of its own (111 + 27 motions, the capture / thrown ones played with the grabber's
animation), `0x200` / `0x202` rare; the game ORs `0x80` in at run time. Meanings are
**inferred**, except "no own animation" (those slots have hash 0).

So the animation a motion plays is **fixed in the executable**: a new fighter in Marth's slot
must name its animations so their names hash to Marth's values, i.e. keep Marth's file names
(`FitMarthBodyMainA00Wait1.omo`, ...), or patch the tables with `tools/rpx_patch.py` (as
`tools/kirby_marth_sword.py` does). `python3 tools/mtable.py MTABLE --motions MOTION_DIR --rpx
cross_f.rpx --kind 0x12` lists every motion with its script name, animation per part and flags.

### 4.3 What every fighter needs

The common kinds use **288 distinct animations** (Marth's main table), by animation code
(the code letter is a category; the same name in every fighter, `Fit<Name>BodyMain<Code><Name>`):

| Code | Animations |
|---|---|
| A00-A06 | Wait1 Wait2 Wait3 WaitItem ItemHandPickUp ItemHandHave ItemHandGrip ItemHandSmash; WalkSlow WalkMiddle WalkFast WalkBrakeR WalkBrakeL Turn; Dash Run RunBrakeR RunBrakeL TurnRun TurnRunBrake; JumpSquat JumpF JumpB JumpAerialF JumpAerialB; Fall FallF FallB FallAerial FallAerialF FallAerialB FallSpecial FallSpecialF FallSpecialB LandingFallSpecial DamageFall WalkFallR WalkFallL RunFallR RunFallL; Squat SquatWait SquatWaitItem SquatRv LandingLight LandingHeavy; StepJump StepPose StepAirPose StepFall StepBack |
| B00-B02 | GuardOn Guard GuardOff; GuardDamage; EscapeN EscapeF EscapeB EscapeAir Rebound |
| C00-C05 | Attack11 Attack12 AttackDash; AttackS3S; AttackHi3 AttackLw3; AttackS4S AttackS4Charge; AttackHi4 AttackHi4Charge AttackLw4 AttackLw4Charge; AttackAirN/F/B/Hi/Lw, LandingAirN/F/B/Hi/Lw |
| E00-E03 | Catch CatchDash CatchTurn CatchWait CatchAttack CatchCut; ThrowF/B/Hi/Lw, ThrownF/B/Hi/Lw, ThrownDxF/B/Hi/Lw, ThrownGirlF/B/Hi/Lw; CapturePulledHi CaptureWaitHi CaptureDamageHi; CapturePulledLw CaptureWaitLw CaptureDamageLw CaptureCut CaptureJump |
| F00-F09 | DamageHi1-3 DamageN1-3 DamageLw1-3; DamageAir1-3 DamageFlyHi/N/Lw/Top/Roll; DamageElec; DownBoundU DownWaitU DownDamageU DownDamageU3 DownEatU DownStandU DownAttackU DownForwardU DownBackU DownSpotU (and the same with D); Passive PassiveStandF/B PassiveWall PassiveWallJump PassiveCeil; FuraFura FuraFuraStartU/D FuraFuraEnd; FuraSleepStart/Loop/End; Swallowed; CameraHit |
| G00-G03 | Pass Ottotto OttottoWait WallDamage StopWall StopCeil MissFoot; CliffCatch CliffWait; CliffClimbQuick CliffAttackQuick CliffEscapeQuick CliffJumpQuick1/2; SlipDown Slip SlipWait SlipStand SlipAttack SlipEscapeF/B |
| H00-H16 | items: LightGet LightWalkGet LightEat LightWalkEat; LightThrowF/B/Hi/Lw/Dash/Drop, LightThrowAirF/B/Hi/Lw; HeavyGet HeavyWalk HeavyThrowF/B/Hi/Lw; Swing1 Swing3 Swing4 Swing4Charge SwingDash, Swing4Bat; ItemHammerWait/Move/Air; ItemScrew ItemScrewFall; ItemDragoonGet/Ride; ItemBig ItemSmall; ItemLegsWait/SlowF/MiddleF/FastF/BrakeF/DashF/SlowB/MiddleB/FastB/BrakeB/DashB/JumpSquat/Landing; ItemShoot ItemShootAir; ItemScope(Air)Start/Rapid/Fire/End; ItemAssist; ItemGenesisStart/Fall/Fire/Loop/End/AirFire/AirLoop/AirEnd; ItemGrassPull; GekikaraWait |
| I00-I01 | SwimRise SwimUp SwimUpDamage Swim SwimF SwimEnd SwimTurn; SwimDrown SwimDrownOut |
| J00-J02 | EntryR EntryL (`bodyentry`); AppealHi AppealS AppealLw; Win1 Win1Wait Win2 Win2Wait Win3 Win3Wait Lose (`bodyresult`) |
| K00 | LadderWait LadderUp LadderDown LadderCatchR/L LadderCatchAirR/L LadderCatchEndR/L |

Plus the fighter's own (D codes): specials (`D00` neutral ... `D03` down, air versions,
`_c2` / `_c3` / `_c4` custom-move script variants sharing the animations) and Final Smash
(`D04`). Several motions share one animation (JumpFront and JumpFrontMini both play `JumpF`;
the item swings of every weapon play `Swing1`...). Only the main part is needed for the
humanoid set; hand / extra-part animations only if the skeleton has those parts.

Script names of the common kinds (what `motion.mtable` hashes) are in `tools/mtable.py`
(294 of the 494 used ones named, e.g. 0x019 `JumpFront`, 0x03E `StepPoseAir`, 0x133
`SwordSwing1`, 0x161 `Big`); the rest are shown with their animation.

---

## 5. AI (script/ai/) (code + files)

The loader (`0x02DE1DBC`) lists the fighter's `script/ai/` folder and picks files by name:

| File | Format | Notes |
|---|---|---|
| `param.bin` | `AIPD`, version 15 (checked at `0x02DFB4D8`) | 0x10 header, 0x158 bytes of per-action flags read by offset (e.g. `+0x108 + n`), 72 u32 section offsets at 0x168, the sections (27 of 0x171 bytes, one of 0x175, then 44 small ones). Missing or invalid → `fighter/common/script/ai/param.bin` |
| `param_nfp.bin` | `AIPD` v15 | the amiibo version; same fallback |
| `attack_data.bin` | `ATKD` | header {count, 0x211, own-motion count}, 0x18-byte entries {u16 motion kind, u16 0, u16 first / last active frame, f32 x min, x max, y min, y max} (`0x02DFC824` validates the magic and indexes the entries by motion kind, < 0x611). The CPU picks attacks from these boxes: without an entry it doesn't use the move |
| `script.bin` | AI script | header {0, routine count, 0, 0, offsets}; routine {u32 id, code offset 0x10, constants offset, flags}, commands {u8 op, u8 argc, u16 size, u32 args}, float constants. Routine ids (Marth 0x1130, 0x6039, 0x6047, 0x4010) override the common script's (`fighter/common/script/ai/script.bin`); passed to `0x02719350` |
| `fighter_param_vl.bin` | | a file of this name is also picked up here; when it is present, kinds 0x27, 0x29, 0x2A, 0x2C, 0x2E, 0x30, 0x37 also load their shared `param/fighter/ai/fighter_ai_<name>_param.bin` (refcounted, `0x02DE2718`), other kinds keep the file (`+0x130`). Not in Marth's, Mario's, Kirby's, Luigi's or Sonic's folder; its role is unclear |

Plus per-kind entries in `param/ai/fighter_ai_fighter_param.bin` (65 x 72) and
`fighter_ai_nfp_learning_param.bin` (65 x 41), and the 7 kinds' `fighter_ai_<name>_param.bin`.

For CPUs to play a new fighter: copy the base fighter's `param.bin`, `param_nfp.bin`,
`script.bin` (its routines suit the base's specials; replace them if the specials differ) and
write `attack_data.bin` for the new moves (`ai_files.py --json` / `--atkd`; the boxes can be
read off the hitboxes, e.g. with Sm4shCommand's hitbox viewer).

---

## 6. Sound (code + files)

- **Sound IDs.** `sound/config/soundlabeltable.bin` (`STB\0`, 3252 rows of {bank id, label
  count, offset, 0}, then each row's tone indices) gives each bank (by the **BINF id inside the
  `.nus3bank`**) a row; a sound's ID = `row << 16 | label`. ACMD uses these IDs directly: Marth's
  `snd_se_Marth` = BINF 2020 = row 22 → `Sound_Effect(0x16xxxx)`; `snd_vc_Marth` = 6016 = row 73 →
  `0x49xxxx`; cheers 6094 = row 2251; Kirby-copy voices 2091 = row 116. So a replacement bank must
  keep the base's BINF id and have at least as many labels / tones as its row (or the row must
  be edited, as `tools/minecraft_sound.py` does for a stage bank).
- **`soundseq_<Name>.sqb`**: header {u16 4, u16 **set id**, u32 count, u32 count x 4}, offsets
  (-1 = none), sequences of weighted choices (sound ID or -1 = silence, weight %). ACMD plays
  sequence n as `0x8000 | set id << 16 | n` (Marth's set 0x28: `Low_Voice_Clip(0x80280000)`,
  `PLAY_FLY_VOICE(0x80280004)`; Mario's set 0). Keep the base's set id.
- **`voiceanim_<Name>.vat`**: u32 2, u32 n, u32 0, then per voice label the hash of the mouth
  animation (`FitMarthBodyMainVoiceS0/S1/S2/L0` in `material_anime_face.pac`), -1 = none.
- **`commonsoundtable.csb`**: 62 entries in voice-bank order (bank ids 6001 Mario, ...,
  6016 Marth = entry 15): three voice clips (label, row) and the cheer bank's row (**inferred**:
  used for common situations such as KO screams).
- **`fightermodelbanktable.mtb`**: 13 entries {base bank id, ..., alternative bank ids}, for
  fighters whose costumes have their own voices (Bowser Jr. / Koopalings: 7 alternatives).
- Also: `soundprioritytable_fighter.spt`, `soundvolumefighternumtable.fnv` (volume by number of
  fighters), `narration_param.bin` / `snd_se_narration_characall_*` (announcer), audience cheer
  params. A new fighter in a slot keeps these.

`tools/fighter_sound.py SOUND_DIR soundlabeltable.bin --model MODEL_DIR` prints all of this for
a fighter folder.

---

## 7. Effects (files + code)

- The effect folder is loaded by path (types 2 and `Fin%s`); inside, `<name>.010d0000.efc` +
  `.ptcl` + `model/` + `trail/`.
- ACMD effect IDs (Marth's `effect.bin`): `0x1000000 | n` = common effects (dust, jump rings;
  used in every fighter's scripts), **`0x3KK0000 | n` = kind KK's own effects** (Marth `0x312xxxx`:
  Dolphin Slash, Counter, entry), `0x4KK0000 | n` = kind KK's Final Smash effects (`0x412xxxx`,
  only in the Final scripts), with n an index in the `.efc`. The kind is part of the ID, so a
  replacement keeps working in the slot (its scripts must use the slot's kind). `Sword_Trace` /
  `Sword_Glow` use the trail textures. (Bank meaning **inferred** from where they are used.)
- `param/effect/effect_param.bin` (168 bytes) has no per-fighter entries.

---

## 8. Articles and Kirby's copy ability

- **Articles** (`reference/FighterArticles.xml`: per fighter, weapon / item kinds and counts;
  Marth has none): each needs its model folder, motion folder, MSC, ACMD folder (with its own
  `motion.mtable`), vl param block (the vl write-up: weapons read their params from the owner's
  vl file) and an RPX weapon kind (weapon name table `0x10419604`). A new fighter is simplest
  with the base's article set.
- **Kirby's copy** of the fighter: Kirby's hat model `fighter/kirby/model/<name>cap/c00`
  (hat names table at `0x10159368`-`0x1015980C`: `marthcap`, `marthsword`, ...; held models
  `0x1041A8A0` + kind x 4), Kirby's animations `fighter/kirby/motion/<name>body/`, Kirby's motion
  table and scripts for the copy (motions above `0x30A` in Kirby's 1222), the copy's neutral-special
  params in Kirby's vl, and `snd_se_vc_Kirby_copy_<Name>.nus3bank` in the fighter's own sound
  folder (`docs/native-notes.md` "Copy abilities"). In a slot replacement all of this stays the
  base fighter's copy unless replaced.

---

## 9. Checklist: a new fighter in an existing slot (base = the slot's fighter)

Files in `data/fighter/<base>/`:
- [ ] `model/body/c00`..`cNN` (+ `l00`..`lNN`): `model.nud`, `model.nut`, `model.vbn`,
      **`model.jtb` mapping the base's bone IDs to the new bones** (3.5), `metal.nud`, `model.xmb`
      (copy), `model.mta` + `material_anime_*.pac` (eyes / face, incl. mouth shapes for
      `voiceanim`), `model.sb` / `.nhb` / `.ik` if the skeleton uses them.
- [ ] `motion/body/main.pac` with the 288 common animations (4.3) and the specials, **named
      with the base's names** (`Fit<Base>BodyMain...`), or the RPX motion tables patched; hand /
      part packs if the parts exist; `bodyentry`, `bodyresult` (incl. `face.pac`), `bodyroutemap`.
- [ ] `script/animcmd/body/`: `motion.mtable` (the base's, unless script names change; same
      length) + `game.bin`, `effect.bin`, `sound.bin`, `expression.bin`.
- [ ] `script/msc/<base>.mscsb` (start from the base's).
- [ ] `script/ai/`: base's `param.bin`, `param_nfp.bin`, `script.bin`; new `attack_data.bin`.
- [ ] `sound/`: banks with the base's BINF ids (and enough labels for their STB rows),
      `soundseq` with the base's set id, `voiceanim`.
- [ ] `effect/<base>/` and `effect/Fin<Base>/` (`.efc` indices as the scripts use them),
      `camera/final/` if the kind has one.

Data elsewhere:
- [ ] `param/fighter/fighter_param_vl_<base>.bin`: hurtboxes (group 5), ECB bones (4),
      ledge boxes (7), attach points (9, 10) with the new bone IDs (`vl_shapes.py`), per-motion
      values (group 1) and special params (vl write-up).
- [ ] `param/fighter/fighter_param.bin` entry (stats, shield, camera box, item box, bone IDs).
- [ ] `param/ai/fighter_ai_fighter_param.bin` entry (CPU tuning) if needed.
- [ ] UI: portraits, stock icon, name strings (new-slot write-up).
- [ ] Optional: Kirby's hat / copy files, announcer call, cheers.

A 66th kind needs all of the above plus every per-kind table in the executable (names `0x102FF484`
/ `0x102FF588`, vl names `0x10353DB4`, descriptor and motion tables, specializer, the 65-case
switches): see the new-slot write-up.

---

## 10. Unknown / needs files we don't have

- The meaning of hurtbox values part / height (inferred from bones), vl groups 9/10 as joint
  IDs 10000+ / 11000+ (no use found in Marth's ACMD or fighter_param), the ledge box values'
  exact meaning (x / y / w / h names from the community sheet), most motion-table flags.
- AIPD sections and AI script opcodes are laid out but not named (the AI code is around
  `0x02DD0000`-`0x02E00000`, not traced op by op).
- `model.moi`, `model.flp`, `model.sb`, `model.nhb`, `model.ik` formats only identified
  (magic, purpose), no editors; `.ptcl` (EFTF) not decoded.
- `camera/final/` contents: Marth's folder copy has none; needs a fighter with a Final Smash
  camera (Falcon, Shulk, ...).
- Unchecked against more fighters: everything here was compared on Marth, Mario, Kirby (and
  Luigi / Sonic scripts); the `l%02d` condition's player-count reading (`0x02FFD69C` > 4) is
  **inferred**.
- 206 common motion script names are unnamed (their hashes and animations are listed by
  `mtable.py`); most are capture / thrown motions with no animation of their own.
- Whether the game needs any fighter bone *by name* outside debug code: none found; not proven.
